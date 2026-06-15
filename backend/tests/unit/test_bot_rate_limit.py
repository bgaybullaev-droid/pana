"""Block D (FU3) — unit tests for the bot per-user rate limiter.

Pure in-memory: a tiny ``FakeRedis`` stands in for Redis and the config
loader is monkeypatched so no DB is touched. Covers the fixed-window
counter, scope isolation, the on/off toggle, fail-open on Redis errors,
the admin-editable message lookup and config (de)serialization.
"""

import pytest

from app.bot import rate_limit
from app.bot.rate_limit import RateLimitConfig

pytestmark = pytest.mark.unit


class FakeRedis:
    """Minimal async Redis stub for the limiter (INCR/EXPIRE/GET/SET)."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.expires: dict[str, int] = {}
        self.fail = False

    async def incr(self, key: str) -> int:
        if self.fail:
            raise RuntimeError("redis down")
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, window: int) -> bool:
        if self.fail:
            raise RuntimeError("redis down")
        self.expires[key] = window
        return True

    def reset_window(self, scope: str, user_id: int) -> None:
        """Simulate TTL expiry of a user's window bucket."""
        self.store.pop(f"bot:rl:{scope}:{user_id}", None)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()

    async def _get_redis():
        return fake

    monkeypatch.setattr(rate_limit, "get_redis", _get_redis)
    return fake


def _patch_config(monkeypatch, config: RateLimitConfig) -> None:
    async def _load() -> RateLimitConfig:
        return config

    monkeypatch.setattr(rate_limit, "_load_config", _load)


class TestRateLimiterHit:
    async def test_allows_up_to_limit_then_blocks(self, monkeypatch, fake_redis):
        _patch_config(
            monkeypatch, RateLimitConfig(search_limit=3, search_window_sec=60)
        )
        results = [await rate_limit.hit("search", 1) for _ in range(4)]
        assert results == [True, True, True, False]

    async def test_window_reset_allows_again(self, monkeypatch, fake_redis):
        _patch_config(monkeypatch, RateLimitConfig(search_limit=2))
        assert await rate_limit.hit("search", 7) is True
        assert await rate_limit.hit("search", 7) is True
        assert await rate_limit.hit("search", 7) is False
        fake_redis.reset_window("search", 7)  # TTL elapsed
        assert await rate_limit.hit("search", 7) is True

    async def test_expire_armed_with_window_on_first_hit(self, monkeypatch, fake_redis):
        _patch_config(
            monkeypatch, RateLimitConfig(search_limit=5, search_window_sec=42)
        )
        await rate_limit.hit("search", 3)
        await rate_limit.hit("search", 3)
        assert fake_redis.expires["bot:rl:search:3"] == 42

    async def test_scopes_are_independent(self, monkeypatch, fake_redis):
        _patch_config(
            monkeypatch, RateLimitConfig(search_limit=1, inline_limit=1)
        )
        assert await rate_limit.hit("search", 9) is True
        assert await rate_limit.hit("search", 9) is False
        # The inline scope keeps its own counter.
        assert await rate_limit.hit("inline", 9) is True
        assert await rate_limit.hit("inline", 9) is False

    async def test_disabled_scope_always_allows(self, monkeypatch, fake_redis):
        _patch_config(
            monkeypatch, RateLimitConfig(search_enabled=False, search_limit=1)
        )
        for _ in range(5):
            assert await rate_limit.hit("search", 2) is True

    async def test_fail_open_on_redis_error(self, monkeypatch, fake_redis):
        _patch_config(monkeypatch, RateLimitConfig(search_limit=1))
        fake_redis.fail = True
        assert await rate_limit.hit("search", 4) is True
        assert await rate_limit.hit("search", 4) is True


class TestLimitMessage:
    async def test_custom_message_per_locale(self, monkeypatch):
        cfg = RateLimitConfig(
            limit_message_ru="ru-msg",
            limit_message_uz="uz-msg",
            limit_message_uz_cyrl="cyrl-msg",
        )
        _patch_config(monkeypatch, cfg)
        assert await rate_limit.limit_message("ru") == "ru-msg"
        assert await rate_limit.limit_message("uz") == "uz-msg"
        assert await rate_limit.limit_message("uz_cyrl") == "cyrl-msg"
        # Unknown locale falls back to Russian.
        assert await rate_limit.limit_message("en") == "ru-msg"

    async def test_defaults_are_non_empty(self, monkeypatch):
        _patch_config(monkeypatch, RateLimitConfig())
        for lang in ("ru", "uz", "uz_cyrl"):
            assert (await rate_limit.limit_message(lang)).strip()


class TestConfigSerialization:
    def test_round_trip(self):
        cfg = RateLimitConfig(search_limit=42, limit_message_ru="x")
        assert RateLimitConfig.from_json(cfg.to_json()) == cfg

    def test_from_json_ignores_unknown_keys(self):
        cfg = RateLimitConfig.from_json('{"search_limit": 5, "bogus": 1}')
        assert cfg.search_limit == 5
