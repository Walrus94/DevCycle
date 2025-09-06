"""
Cache warming service.

This module provides intelligent cache warming strategies to preload
frequently accessed data and improve cache hit ratios.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ...cache.acp_cache import ACPCache
from ...logging import get_logger

logger = get_logger(__name__)


class WarmingStrategy(Enum):
    """Cache warming strategies."""

    ON_STARTUP = "on_startup"
    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"
    PREDICTIVE = "predictive"


@dataclass
class WarmingRule:
    """Cache warming rule definition."""

    name: str
    key_pattern: str
    data_loader: Callable[[str], Any]
    priority: int
    ttl: Optional[float] = None
    enabled: bool = True
    last_warmed: Optional[datetime] = None
    warm_count: int = 0


@dataclass
class WarmingStatistics:
    """Cache warming statistics."""

    total_rules: int
    enabled_rules: int
    total_warmed: int
    successful_warms: int
    failed_warms: int
    last_warming_cycle: Optional[datetime]
    average_warm_time_ms: float


class CacheWarmer:
    """Intelligent cache warming service."""

    def __init__(self, acp_cache: ACPCache):
        """
        Initialize cache warmer.

        Args:
            acp_cache: ACP cache instance to warm
        """
        self.acp_cache = acp_cache
        self.redis = acp_cache.redis  # Access Redis client directly
        self.warming_rules: Dict[str, WarmingRule] = {}
        self.warming_strategies: Set[WarmingStrategy] = {WarmingStrategy.ON_STARTUP}

        # Warming state
        self.warming_enabled = True
        self.last_warming_cycle = None
        self.warming_statistics = WarmingStatistics(
            total_rules=0,
            enabled_rules=0,
            total_warmed=0,
            successful_warms=0,
            failed_warms=0,
            last_warming_cycle=None,
            average_warm_time_ms=0.0,
        )

        # Background task
        self._warming_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the cache warming system."""
        if self._running:
            return

        self._running = True

        # Run initial warming if enabled
        if WarmingStrategy.ON_STARTUP in self.warming_strategies:
            await self._warm_on_startup()

        # Start scheduled warming if enabled
        if WarmingStrategy.SCHEDULED in self.warming_strategies:
            self._warming_task = asyncio.create_task(self._scheduled_warming_loop())

        logger.info("Cache warmer started")

    async def stop(self) -> None:
        """Stop the cache warming system."""
        if not self._running:
            return

        self._running = False
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache warmer stopped")

    async def _warm_on_startup(self) -> None:
        """Warm cache on startup."""
        logger.info("Starting cache warming on startup")
        await self._execute_warming_cycle()

    async def _scheduled_warming_loop(self) -> None:
        """Background scheduled warming loop."""
        while self._running:
            try:
                # Run warming every hour
                await asyncio.sleep(3600)
                if self.warming_enabled:
                    await self._execute_warming_cycle()
            except Exception as e:
                logger.error(f"Error in scheduled warming loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _execute_warming_cycle(self) -> None:
        """Execute a complete warming cycle."""
        if not self.warming_enabled:
            return

        logger.info("Starting cache warming cycle")
        start_time = datetime.now(timezone.utc)

        # Get enabled rules sorted by priority
        enabled_rules = [rule for rule in self.warming_rules.values() if rule.enabled]
        enabled_rules.sort(key=lambda x: x.priority, reverse=True)

        successful_warms = 0
        failed_warms = 0

        for rule in enabled_rules:
            try:
                await self._warm_rule(rule)
                successful_warms += 1
            except Exception as e:
                logger.error(f"Failed to warm rule {rule.name}: {e}")
                failed_warms += 1

        # Update statistics
        end_time = datetime.now(timezone.utc)
        warm_time_ms = (end_time - start_time).total_seconds() * 1000

        self.warming_statistics.total_warmed += len(enabled_rules)
        self.warming_statistics.successful_warms += successful_warms
        self.warming_statistics.failed_warms += failed_warms
        self.warming_statistics.last_warming_cycle = end_time

        if len(enabled_rules) > 0:
            self.warming_statistics.average_warm_time_ms = (
                self.warming_statistics.average_warm_time_ms + warm_time_ms
            ) / 2

        logger.info(
            f"Cache warming cycle completed: {successful_warms} successful, "
            f"{failed_warms} failed"
        )

    async def _warm_rule(
        self, rule: WarmingRule, key_pattern: Optional[str] = None
    ) -> None:
        """Warm a specific rule."""
        start_time = datetime.now(timezone.utc)

        try:
            # Use provided key_pattern or fall back to rule's key_pattern
            pattern = key_pattern or rule.key_pattern

            # Load data using the rule's data loader
            data = await rule.data_loader(pattern)

            if data is not None:
                # Store in cache with specified TTL
                self.redis.set(
                    pattern, json.dumps(data), ttl=int(rule.ttl) if rule.ttl else None
                )

                # Update rule statistics
                rule.last_warmed = start_time
                rule.warm_count += 1

                logger.debug(f"Warmed cache for rule {rule.name}: {pattern}")
            else:
                logger.warning(f"No data returned for warming rule {rule.name}")

        except Exception as e:
            logger.error(f"Error warming rule {rule.name}: {e}")
            raise

    def add_warming_rule(self, rule: WarmingRule) -> None:
        """Add a cache warming rule."""
        self.warming_rules[rule.name] = rule
        self.warming_statistics.total_rules = len(self.warming_rules)
        self.warming_statistics.enabled_rules = len(
            [r for r in self.warming_rules.values() if r.enabled]
        )
        logger.info(f"Added warming rule: {rule.name}")

    def remove_warming_rule(self, rule_name: str) -> None:
        """Remove a cache warming rule."""
        if rule_name in self.warming_rules:
            del self.warming_rules[rule_name]
            self.warming_statistics.total_rules = len(self.warming_rules)
            self.warming_statistics.enabled_rules = len(
                [r for r in self.warming_rules.values() if r.enabled]
            )
            logger.info(f"Removed warming rule: {rule_name}")

    def enable_warming_rule(self, rule_name: str) -> None:
        """Enable a warming rule."""
        if rule_name in self.warming_rules:
            self.warming_rules[rule_name].enabled = True
            self.warming_statistics.enabled_rules = len(
                [r for r in self.warming_rules.values() if r.enabled]
            )
            logger.info(f"Enabled warming rule: {rule_name}")

    def disable_warming_rule(self, rule_name: str) -> None:
        """Disable a warming rule."""
        if rule_name in self.warming_rules:
            self.warming_rules[rule_name].enabled = False
            self.warming_statistics.enabled_rules = len(
                [r for r in self.warming_rules.values() if r.enabled]
            )
            logger.info(f"Disabled warming rule: {rule_name}")

    async def warm_on_demand(self, key_patterns: List[str]) -> None:
        """Warm cache on demand for specific key patterns."""
        if not self.warming_enabled:
            return

        logger.info(
            f"Starting on-demand cache warming for {len(key_patterns)} patterns"
        )

        for pattern in key_patterns:
            # Find matching rules
            matching_rules = [
                rule
                for rule in self.warming_rules.values()
                if rule.enabled and self._pattern_matches(pattern, rule.key_pattern)
            ]

            for rule in matching_rules:
                try:
                    await self._warm_rule(rule, pattern)
                except Exception as e:
                    logger.error(f"Failed to warm rule {rule.name} on demand: {e}")

    def _pattern_matches(self, key: str, pattern: str) -> bool:
        """Check if a key matches a pattern."""
        # Simple pattern matching - can be enhanced with regex
        if "*" in pattern:
            prefix, suffix = pattern.split("*", 1)
            return key.startswith(prefix) and key.endswith(suffix)
        return key == pattern

    def add_warming_strategy(self, strategy: WarmingStrategy) -> None:
        """Add a warming strategy."""
        self.warming_strategies.add(strategy)
        logger.info(f"Added warming strategy: {strategy.value}")

    def remove_warming_strategy(self, strategy: WarmingStrategy) -> None:
        """Remove a warming strategy."""
        self.warming_strategies.discard(strategy)
        logger.info(f"Removed warming strategy: {strategy.value}")

    def enable_warming(self) -> None:
        """Enable cache warming."""
        self.warming_enabled = True
        logger.info("Cache warming enabled")

    def disable_warming(self) -> None:
        """Disable cache warming."""
        self.warming_enabled = False
        logger.info("Cache warming disabled")

    def get_warming_statistics(self) -> Dict[str, Any]:
        """Get cache warming statistics."""
        return {
            "warming_enabled": self.warming_enabled,
            "strategies": [strategy.value for strategy in self.warming_strategies],
            "total_rules": self.warming_statistics.total_rules,
            "enabled_rules": self.warming_statistics.enabled_rules,
            "total_warmed": self.warming_statistics.total_warmed,
            "successful_warms": self.warming_statistics.successful_warms,
            "failed_warms": self.warming_statistics.failed_warms,
            "last_warming_cycle": (
                self.warming_statistics.last_warming_cycle.isoformat()
                if self.warming_statistics.last_warming_cycle
                else None
            ),
            "average_warm_time_ms": self.warming_statistics.average_warm_time_ms,
            "rules": {
                name: {
                    "key_pattern": rule.key_pattern,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "last_warmed": (
                        rule.last_warmed.isoformat() if rule.last_warmed else None
                    ),
                    "warm_count": rule.warm_count,
                }
                for name, rule in self.warming_rules.items()
            },
        }

    async def reset_statistics(self) -> None:
        """Reset warming statistics."""
        self.warming_statistics = WarmingStatistics(
            total_rules=len(self.warming_rules),
            enabled_rules=len([r for r in self.warming_rules.values() if r.enabled]),
            total_warmed=0,
            successful_warms=0,
            failed_warms=0,
            last_warming_cycle=None,
            average_warm_time_ms=0.0,
        )

        for rule in self.warming_rules.values():
            rule.last_warmed = None
            rule.warm_count = 0

        logger.info("Cache warming statistics reset")
