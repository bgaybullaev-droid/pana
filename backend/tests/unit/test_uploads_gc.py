"""PR-H — Orphan-uploads GC unit tests.

The async helper is tested by pointing `_UPLOAD_DIR` at a tempdir,
creating a mix of referenced / unreferenced / new files, and asserting
the cleanup summary.

DB access is stubbed via monkeypatching `_collect_referenced_keys` so
we don't need a live Postgres.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.workers.tasks import uploads_gc

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────
# _url_to_key
# ─────────────────────────────────────────────────────────────────────


class TestUrlToKey:
    def test_absolute_https_url(self):
        assert (
            uploads_gc._url_to_key(
                "https://ucharmarket.uz/uploads/listings/abc/photo.jpg"
            )
            == "listings/abc/photo.jpg"
        )

    def test_absolute_http_localhost(self):
        assert (
            uploads_gc._url_to_key(
                "http://localhost:8001/uploads/listings/abc/photo.jpg"
            )
            == "listings/abc/photo.jpg"
        )

    def test_relative_url(self):
        assert (
            uploads_gc._url_to_key("/uploads/listings/abc/photo.jpg")
            == "listings/abc/photo.jpg"
        )

    def test_none_returns_none(self):
        assert uploads_gc._url_to_key(None) is None

    def test_empty_string_returns_none(self):
        assert uploads_gc._url_to_key("") is None

    def test_non_upload_url_returns_none(self):
        # CDN / crawler source URLs have no /uploads/ segment.
        assert uploads_gc._url_to_key("https://cdn.olx.uz/images/abc123.jpg") is None


# ─────────────────────────────────────────────────────────────────────
# _walk_upload_tree
# ─────────────────────────────────────────────────────────────────────


class TestWalkTree:
    def test_enumerates_two_level_files(self, tmp_path: Path):
        (tmp_path / "listings" / "userA").mkdir(parents=True)
        (tmp_path / "listings" / "userB").mkdir(parents=True)
        (tmp_path / "listings" / "userA" / "one.jpg").write_bytes(b"x")
        (tmp_path / "listings" / "userA" / "two.jpg").write_bytes(b"x")
        (tmp_path / "listings" / "userB" / "three.jpg").write_bytes(b"x")

        results = list(uploads_gc._walk_upload_tree(tmp_path))
        keys = {r[1] for r in results}
        assert keys == {
            "listings/userA/one.jpg",
            "listings/userA/two.jpg",
            "listings/userB/three.jpg",
        }

    def test_missing_root_yields_nothing(self, tmp_path: Path):
        # `listings/` does not exist — generator finishes cleanly.
        assert list(uploads_gc._walk_upload_tree(tmp_path)) == []

    def test_ignores_stray_files_at_wrong_depth(self, tmp_path: Path):
        (tmp_path / "listings").mkdir()
        (tmp_path / "listings" / "stray.jpg").write_bytes(b"x")  # wrong depth
        (tmp_path / "listings" / "userA").mkdir()
        (tmp_path / "listings" / "userA" / "ok.jpg").write_bytes(b"x")

        keys = {r[1] for r in uploads_gc._walk_upload_tree(tmp_path)}
        # Stray file at root level is NOT yielded — not in the expected layout.
        assert keys == {"listings/userA/ok.jpg"}

    def test_returns_mtime_near_now(self, tmp_path: Path):
        (tmp_path / "listings" / "u").mkdir(parents=True)
        (tmp_path / "listings" / "u" / "fresh.jpg").write_bytes(b"x")
        results = list(uploads_gc._walk_upload_tree(tmp_path))
        assert len(results) == 1
        mtime = results[0][2]
        assert isinstance(mtime, datetime)
        delta = abs((datetime.utcnow() - mtime).total_seconds())
        assert delta < 10  # freshly created — within 10s


# ─────────────────────────────────────────────────────────────────────
# _cleanup_orphan_uploads
# ─────────────────────────────────────────────────────────────────────


def _age_file_by_hours(path: Path, hours: float) -> None:
    """Backdate a file's mtime by `hours` hours."""
    then = time.time() - hours * 3600
    os.utime(path, (then, then))


class TestCleanupHelper:
    @pytest.fixture
    def mock_db(self, monkeypatch):
        """Stub `_collect_referenced_keys` + `_get_session` so the helper
        doesn't need a live DB. The test controls which keys appear
        referenced by setting the `referenced` list on the fixture."""
        state = {"referenced": set()}

        async def fake_collect(_db):
            return state["referenced"]

        # Replace the internal collector.
        monkeypatch.setattr(uploads_gc, "_collect_referenced_keys", fake_collect)

        # Replace the session CM with a no-op so nothing tries to open
        # a real DB connection.
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_session():
            yield None

        monkeypatch.setattr(uploads_gc, "_get_session", fake_session)
        return state

    def _redirect_upload_dir(self, monkeypatch, new_dir: Path) -> None:
        monkeypatch.setattr(uploads_gc, "_UPLOAD_DIR", new_dir)

    def test_deletes_old_unreferenced_file(self, tmp_path, monkeypatch, mock_db):
        self._redirect_upload_dir(monkeypatch, tmp_path)
        (tmp_path / "listings" / "u").mkdir(parents=True)
        f = tmp_path / "listings" / "u" / "old.jpg"
        f.write_bytes(b"x")
        _age_file_by_hours(f, 48)

        result = asyncio.run(
            uploads_gc._cleanup_orphan_uploads(min_age_hours=24, dry_run=False)
        )
        assert result["deleted_count"] == 1
        assert result["referenced_count"] == 0
        assert result["too_new_count"] == 0
        assert not f.exists()

    def test_keeps_referenced_file_even_when_old(self, tmp_path, monkeypatch, mock_db):
        self._redirect_upload_dir(monkeypatch, tmp_path)
        (tmp_path / "listings" / "u").mkdir(parents=True)
        f = tmp_path / "listings" / "u" / "kept.jpg"
        f.write_bytes(b"x")
        _age_file_by_hours(f, 48)
        mock_db["referenced"] = {"listings/u/kept.jpg"}

        result = asyncio.run(
            uploads_gc._cleanup_orphan_uploads(min_age_hours=24, dry_run=False)
        )
        assert result["referenced_count"] == 1
        assert result["deleted_count"] == 0
        assert f.exists()

    def test_skips_fresh_unreferenced_file(self, tmp_path, monkeypatch, mock_db):
        self._redirect_upload_dir(monkeypatch, tmp_path)
        (tmp_path / "listings" / "u").mkdir(parents=True)
        f = tmp_path / "listings" / "u" / "fresh.jpg"
        f.write_bytes(b"x")
        # mtime ~ now. No backdating.

        result = asyncio.run(
            uploads_gc._cleanup_orphan_uploads(min_age_hours=24, dry_run=False)
        )
        assert result["too_new_count"] == 1
        assert result["deleted_count"] == 0
        assert f.exists()

    def test_dry_run_does_not_delete(self, tmp_path, monkeypatch, mock_db):
        self._redirect_upload_dir(monkeypatch, tmp_path)
        (tmp_path / "listings" / "u").mkdir(parents=True)
        f = tmp_path / "listings" / "u" / "old.jpg"
        f.write_bytes(b"x")
        _age_file_by_hours(f, 48)

        result = asyncio.run(
            uploads_gc._cleanup_orphan_uploads(min_age_hours=24, dry_run=True)
        )
        # deleted_count reflects what WOULD be deleted.
        assert result["deleted_count"] == 1
        assert result["dry_run"] is True
        # File is still on disk.
        assert f.exists()

    def test_mixed_bucket_counts(self, tmp_path, monkeypatch, mock_db):
        self._redirect_upload_dir(monkeypatch, tmp_path)
        (tmp_path / "listings" / "u").mkdir(parents=True)

        # Old + unreferenced → delete
        f1 = tmp_path / "listings" / "u" / "orphan.jpg"
        f1.write_bytes(b"x")
        _age_file_by_hours(f1, 48)

        # Old + referenced → keep
        f2 = tmp_path / "listings" / "u" / "loved.jpg"
        f2.write_bytes(b"x")
        _age_file_by_hours(f2, 48)

        # Fresh + unreferenced → skip (race guard)
        f3 = tmp_path / "listings" / "u" / "fresh.jpg"
        f3.write_bytes(b"x")

        mock_db["referenced"] = {"listings/u/loved.jpg"}

        result = asyncio.run(
            uploads_gc._cleanup_orphan_uploads(min_age_hours=24, dry_run=False)
        )
        assert result["scanned_count"] == 3
        assert result["referenced_count"] == 1
        assert result["too_new_count"] == 1
        assert result["deleted_count"] == 1
        assert not f1.exists()
        assert f2.exists()
        assert f3.exists()

    def test_empty_upload_dir(self, tmp_path, monkeypatch, mock_db):
        self._redirect_upload_dir(monkeypatch, tmp_path)
        result = asyncio.run(
            uploads_gc._cleanup_orphan_uploads(min_age_hours=24, dry_run=False)
        )
        assert result == {
            "scanned_count": 0,
            "referenced_count": 0,
            "too_new_count": 0,
            "deleted_count": 0,
            "errors": 0,
            "cutoff": result["cutoff"],  # any ISO timestamp
            "dry_run": False,
        }
