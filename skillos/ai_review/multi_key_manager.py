"""
ai_review/multi_key_manager.py

Multi-Key Manager for AI Providers
====================================

Supports multiple API keys per provider with:
  - Round-robin rotation across keys
  - Per-key circuit breaking (failed key is skipped, retried after cooldown)
  - Per-key rate-limit detection (429 → mark key as rate-limited, skip it)
  - Automatic key re-activation after cooldown period
  - Zero-config: works with 1 key, scales to N keys seamlessly

CONFIGURATION (.env):
  # Single key per provider (original):
  ANTHROPIC_API_KEY=sk-ant-abc123
  GROQ_API_KEY=gsk_abc123
  GEMINI_API_KEY=AIza_abc123
  OPENAI_API_KEY=sk-abc123

  # Multiple keys per provider (comma-separated):
  ANTHROPIC_API_KEY=sk-ant-key1,sk-ant-key2,sk-ant-key3
  GROQ_API_KEY=gsk_key1,gsk_key2
  GEMINI_API_KEY=AIza_key1,AIza_key2
  OPENAI_API_KEY=sk-key1,sk-key2,sk-key3

  # Optional: cooldown after key failure (seconds, default 60)
  AI_KEY_COOLDOWN_SECONDS=60

  # Optional: max consecutive failures before key is suspended
  AI_KEY_MAX_FAILURES=3

USAGE:
  from skillos.ai_review.multi_key_manager import key_manager

  key = key_manager.get_key("anthropic")   # returns next healthy key or None
  key_manager.mark_success("anthropic", key)
  key_manager.mark_failure("anthropic", key, rate_limited=False)
  key_manager.mark_rate_limited("anthropic", key)

  # Status endpoint
  status = key_manager.get_status()
"""

from __future__ import annotations
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

# ── Configuration ─────────────────────────────────────────────────────────────
_COOLDOWN_S   = int(os.environ.get("AI_KEY_COOLDOWN_SECONDS", "60"))
_RATE_COOLDOWN = int(os.environ.get("AI_RATE_LIMIT_COOLDOWN_SECONDS", "120"))
_MAX_FAILS    = int(os.environ.get("AI_KEY_MAX_FAILURES", "3"))


def _load_keys(env_var: str) -> list[str]:
    """Parse comma-separated keys from environment variable. Filters empty strings."""
    raw = os.environ.get(env_var, "")
    return [k.strip() for k in raw.split(",") if k.strip()]


@dataclass
class KeyState:
    """Health state for a single API key."""
    key:          str
    failures:     int   = 0
    last_fail_at: float = 0.0
    rate_limited: bool  = False
    rate_limit_at: float = 0.0
    total_uses:   int   = 0
    total_errors: int   = 0

    def is_healthy(self) -> bool:
        """Returns True if this key can be used right now."""
        now = time.time()

        # Rate-limited: longer cooldown
        if self.rate_limited:
            if now - self.rate_limit_at > _RATE_COOLDOWN:
                self.rate_limited = False
                self.failures = 0
            else:
                return False

        # Too many consecutive failures: cooldown
        if self.failures >= _MAX_FAILS:
            if now - self.last_fail_at > _COOLDOWN_S:
                self.failures = 0  # reset after cooldown
            else:
                return False

        return True

    def masked(self) -> str:
        """Return masked key for logging (show first 8 + last 4 chars)."""
        if len(self.key) <= 12:
            return "***"
        return f"{self.key[:8]}...{self.key[-4:]}"


class ProviderKeyPool:
    """
    Thread-safe round-robin key pool for one provider.
    Maintains a rotating cursor so requests spread evenly across keys.
    """

    def __init__(self, provider: str, keys: list[str]):
        self.provider = provider
        self._states: list[KeyState] = [KeyState(key=k) for k in keys]
        self._cursor: int = 0
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._states)

    def get_key(self) -> Optional[str]:
        """
        Return the next healthy key using round-robin rotation.
        Returns None if no healthy keys are available.
        """
        with self._lock:
            n = len(self._states)
            if n == 0:
                return None
            # Try every key starting from cursor
            for i in range(n):
                idx = (self._cursor + i) % n
                state = self._states[idx]
                if state.is_healthy():
                    self._cursor = (idx + 1) % n  # advance cursor past used key
                    state.total_uses += 1
                    return state.key
            return None

    def mark_success(self, key: str) -> None:
        with self._lock:
            for s in self._states:
                if s.key == key:
                    s.failures = 0
                    s.rate_limited = False
                    return

    def mark_failure(self, key: str) -> None:
        with self._lock:
            for s in self._states:
                if s.key == key:
                    s.failures += 1
                    s.last_fail_at = time.time()
                    s.total_errors += 1
                    return

    def mark_rate_limited(self, key: str) -> None:
        with self._lock:
            for s in self._states:
                if s.key == key:
                    s.rate_limited = True
                    s.rate_limit_at = time.time()
                    s.total_errors += 1
                    return

    def get_status(self) -> dict:
        with self._lock:
            return {
                "provider": self.provider,
                "total_keys": len(self._states),
                "healthy_keys": sum(1 for s in self._states if s.is_healthy()),
                "keys": [
                    {
                        "key_masked":     s.masked(),
                        "healthy":        s.is_healthy(),
                        "failures":       s.failures,
                        "rate_limited":   s.rate_limited,
                        "total_uses":     s.total_uses,
                        "total_errors":   s.total_errors,
                    }
                    for s in self._states
                ],
            }


class MultiKeyManager:
    """
    Central manager for all AI provider keys.
    Handles 1..N keys per provider transparently.
    """

    _PROVIDERS = {
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini":    "GEMINI_API_KEY",
        "groq":      "GROQ_API_KEY",
        "openai":    "OPENAI_API_KEY",
    }

    def __init__(self):
        self._pools: dict[str, ProviderKeyPool] = {}
        self._reload()

    def _reload(self) -> None:
        """Load/reload all provider keys from environment variables."""
        for provider, env_var in self._PROVIDERS.items():
            keys = _load_keys(env_var)
            self._pools[provider] = ProviderKeyPool(provider, keys)

    def get_key(self, provider: str) -> Optional[str]:
        """
        Get the next healthy API key for a provider.
        Returns None if:
          - Provider has no keys configured
          - All keys are currently suspended (failing / rate-limited)
        """
        pool = self._pools.get(provider)
        if pool is None:
            return None
        return pool.get_key()

    def mark_success(self, provider: str, key: str) -> None:
        """Record a successful API call for a key."""
        pool = self._pools.get(provider)
        if pool:
            pool.mark_success(key)

    def mark_failure(self, provider: str, key: str, rate_limited: bool = False) -> None:
        """Record a failed API call. Set rate_limited=True for HTTP 429 responses."""
        pool = self._pools.get(provider)
        if pool:
            if rate_limited:
                pool.mark_rate_limited(key)
            else:
                pool.mark_failure(key)

    def is_configured(self, provider: str) -> bool:
        """Returns True if the provider has at least one key configured."""
        pool = self._pools.get(provider)
        return pool is not None and len(pool) > 0

    def has_healthy_key(self, provider: str) -> bool:
        """Returns True if the provider has at least one healthy key available."""
        return self.get_key(provider) is not None

    def get_status(self) -> dict:
        """Full health status for all providers — used by /admin/ai-status."""
        return {
            provider: pool.get_status()
            for provider, pool in self._pools.items()
        }

    def get_provider_summary(self) -> dict:
        """
        Compact per-provider summary for /admin/ai-status:
        {provider: {configured, healthy, key_count, healthy_key_count}}
        """
        summary = {}
        for provider, pool in self._pools.items():
            status = pool.get_status()
            summary[provider] = {
                "configured":        status["total_keys"] > 0,
                "healthy":           status["healthy_keys"] > 0,
                "key_count":         status["total_keys"],
                "healthy_key_count": status["healthy_keys"],
            }
        return summary


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this from anywhere:
#   from skillos.ai_review.multi_key_manager import key_manager
key_manager = MultiKeyManager()
