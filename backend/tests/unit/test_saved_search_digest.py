"""FU7 — saved-search push debounce / digest unit tests.

Covers the pure pieces of the debounce-and-digest path added to
``app.workers.tasks.notifications`` (the async flush itself, which loads
from the DB and dispatches Celery, lives in the integration suite):

    - ``_dedupe_saved_search_entries`` — the 1-vs-N decision input
      (dedupe by listing_id, preserve order, keep first search_name,
      skip malformed entries).
    - ``_enqueue_debounced_saved_search_push`` — first hit schedules a
      flush, subsequent hits within the window do not; Redis outage
      fails open (returns False so the caller sends immediately).
    - ``push_saved_search_digest`` renders with ``count`` across all
      three bot locales.
    - ``build_notifications_link`` emits the bare ``notifications``
      startapp token.
    - ``_saved_search_rich_push`` renders the single-match rich card.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.workers.tasks import notifications as N

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# Fake Redis (enough surface for the debounce helpers)
# --------------------------------------------------------------------------


class _FakePipeline:
    def __init__(self, client: "_FakeRedis"):
        self._client = client
        self._ops: list = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def rpush(self, key, value):
        self._ops.append(("rpush", key, value))

    def expire(self, key, ttl):
        self._ops.append(("expire", key, ttl))

    def lrange(self, key, start, end):
        self._ops.append(("lrange", key, start, end))

    def delete(self, key):
        self._ops.append(("delete", key))

    def execute(self):
        results = []
        for op in self._ops:
            if op[0] == "rpush":
                self._client.lists.setdefault(op[1], []).append(op[2])
                results.append(len(self._client.lists[op[1]]))
            elif op[0] == "lrange":
                results.append(list(self._client.lists.get(op[1], [])))
            elif op[0] == "delete":
                self._client.lists.pop(op[1], None)
                self._client.kv.pop(op[1], None)
                results.append(1)
            else:
                results.append(True)
        self._ops = []
        return results


class _FakeRedis:
    def __init__(self):
        self.lists: dict[str, list] = {}
        self.kv: dict[str, str] = {}

    def pipeline(self):
        return _FakePipeline(self)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.kv:
            return None
        self.kv[key] = value
        return True

    def close(self):
        pass


# --------------------------------------------------------------------------
# _dedupe_saved_search_entries
# --------------------------------------------------------------------------


class TestDedupe:
    def _entry(self, lid, name):
        return json.dumps({"l": lid, "s": name})

    def test_single_entry(self):
        out = N._dedupe_saved_search_entries([self._entry("a", "Поиск 1")])
        assert out == [("a", "Поиск 1")]

    def test_dedupe_keeps_first_name_and_order(self):
        raw = [
            self._entry("a", "Первый"),
            self._entry("b", "Второй"),
            self._entry("a", "Дубль"),  # same listing → dropped, first name kept
        ]
        out = N._dedupe_saved_search_entries(raw)
        assert out == [("a", "Первый"), ("b", "Второй")]

    def test_malformed_entries_skipped(self):
        raw = ["not-json", json.dumps({"no_listing": 1}), self._entry("z", "ok")]
        out = N._dedupe_saved_search_entries(raw)
        assert out == [("z", "ok")]

    def test_empty(self):
        assert N._dedupe_saved_search_entries([]) == []

    def test_missing_name_defaults_to_blank(self):
        out = N._dedupe_saved_search_entries([json.dumps({"l": "a"})])
        assert out == [("a", "")]


# --------------------------------------------------------------------------
# _enqueue_debounced_saved_search_push
# --------------------------------------------------------------------------


class TestEnqueueDebounce:
    def test_first_hit_schedules_second_does_not(self, monkeypatch):
        fake = _FakeRedis()
        monkeypatch.setattr(N, "_get_sync_redis", lambda: fake)
        calls: list = []
        monkeypatch.setattr(
            N.flush_pending_saved_search_pushes,
            "apply_async",
            lambda *a, **k: calls.append((a, k)),
        )

        assert N._enqueue_debounced_saved_search_push("u1", "L1", "Поиск") is True
        assert N._enqueue_debounced_saved_search_push("u1", "L2", "Поиск") is True

        # Only the first hit schedules a flush.
        assert len(calls) == 1
        assert calls[0][1]["countdown"] == N._SAVED_SEARCH_BATCH_WINDOW_SEC
        assert calls[0][1]["args"] == ["u1"]
        # Both listings landed in the pending list.
        pending = fake.lists[N._SS_PENDING_KEY.format(user_id="u1")]
        assert [json.loads(e)["l"] for e in pending] == ["L1", "L2"]

    def test_separate_users_each_schedule(self, monkeypatch):
        fake = _FakeRedis()
        monkeypatch.setattr(N, "_get_sync_redis", lambda: fake)
        calls: list = []
        monkeypatch.setattr(
            N.flush_pending_saved_search_pushes,
            "apply_async",
            lambda *a, **k: calls.append(k),
        )
        N._enqueue_debounced_saved_search_push("u1", "L1", "x")
        N._enqueue_debounced_saved_search_push("u2", "L1", "x")
        assert len(calls) == 2

    def test_redis_failure_returns_false(self, monkeypatch):
        def boom():
            raise RuntimeError("redis down")

        monkeypatch.setattr(N, "_get_sync_redis", boom)
        assert N._enqueue_debounced_saved_search_push("u1", "L1", "x") is False


# --------------------------------------------------------------------------
# Digest template + deep link
# --------------------------------------------------------------------------


class TestDigestTemplate:
    def test_renders_count_all_locales(self):
        from app.bot.i18n import t

        for lang in ("ru", "uz", "uz_cyrl"):
            text = t(lang, "push_saved_search_digest", count=5)
            assert "5" in text
            assert text != "[push_saved_search_digest]"  # key exists

    def test_notifications_link_token(self):
        from app.services.deeplink import build_notifications_link

        url = build_notifications_link()
        assert url.endswith("?startapp=notifications")


# --------------------------------------------------------------------------
# _saved_search_rich_push (single-match render)
# --------------------------------------------------------------------------


class TestRichPush:
    def _fake_listing(self):
        return SimpleNamespace(
            id="abc123",
            rooms=2,
            currency=SimpleNamespace(value="USD"),
            property_type=SimpleNamespace(value="apartment"),
            type=SimpleNamespace(value="sale"),
            district="Юнусабад",
            price=60000,
            seller_id=None,
        )

    def test_body_includes_search_name_and_marker(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.listing_push.build_listing_action_kb_spec",
            lambda *a, **k: [[{"text": "x", "callback_data": "y"}]],
        )
        body, kb_spec = N._saved_search_rich_push(
            self._fake_listing(), None, "ru", "Квартиры до $65k"
        )
        assert "🔍" in body
        assert "Квартиры до $65k" in body
        assert kb_spec == [[{"text": "x", "callback_data": "y"}]]

    def test_kb_failure_degrades_to_none(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("kb build failed")

        monkeypatch.setattr(
            "app.services.listing_push.build_listing_action_kb_spec", boom
        )
        body, kb_spec = N._saved_search_rich_push(
            self._fake_listing(), None, "uz", "Test"
        )
        assert kb_spec is None
        assert "Test" in body
