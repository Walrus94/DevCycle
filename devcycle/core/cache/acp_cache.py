"""
ACP-specific Redis caching service for DevCycle.

This module extends the base RedisCache to provide ACP-specific caching functionality
for agent state, workflow state, and performance optimization.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..logging import get_logger
from .redis_cache import RedisCache

logger = get_logger(__name__)


class ACPCache:
    """ACP-specific Redis caching service for performance optimization."""

    def __init__(self, redis_cache: RedisCache):
        """
        Initialize ACP cache service.

        Args:
            redis_cache: Base Redis cache instance
        """
        self.redis = redis_cache
        self.key_prefix = "acp:"

        # Cache TTL Configuration
        self.AGENT_STATUS_TTL = 300  # 5 minutes
        self.AGENT_METADATA_TTL = 3600  # 1 hour
        self.WORKFLOW_STATE_TTL = 1800  # 30 minutes
        self.CAPABILITY_MAPPING_TTL = 600  # 10 minutes
        self.SYSTEM_METRICS_TTL = 60  # 1 minute

    def _get_key(self, key: str) -> str:
        """Get the full Redis key with ACP prefix."""
        return f"{self.key_prefix}{key}"

    # Agent State Management
    async def cache_agent_status(self, agent_id: str, status: Dict[str, Any]) -> bool:
        """
        Cache agent status for fast discovery.

        Args:
            agent_id: Agent identifier
            status: Agent status data

        Returns:
            True if successful, False otherwise
        """
        key = f"agents:status:{agent_id}"
        return self.redis.set(key, status, ttl=self.AGENT_STATUS_TTL)

    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached agent status.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent status data or None if not found
        """
        key = f"agents:status:{agent_id}"
        return self.redis.get(key)

    async def update_agent_heartbeat(self, agent_id: str) -> bool:
        """
        Update agent heartbeat timestamp.

        Args:
            agent_id: Agent identifier

        Returns:
            True if successful, False otherwise
        """
        key = f"agents:heartbeat:{agent_id}"
        timestamp = datetime.now(timezone.utc).isoformat()
        return self.redis.set(key, timestamp, ttl=self.AGENT_STATUS_TTL)

    async def get_agent_heartbeat(self, agent_id: str) -> Optional[str]:
        """
        Get agent heartbeat timestamp.

        Args:
            agent_id: Agent identifier

        Returns:
            Heartbeat timestamp or None if not found
        """
        key = f"agents:heartbeat:{agent_id}"
        return self.redis.get(key)

    # Capability Discovery
    async def cache_capability_mapping(
        self, capability: str, agent_ids: List[str]
    ) -> bool:
        """
        Cache capability to agent mapping.

        Args:
            capability: Capability name
            agent_ids: List of agent IDs with this capability

        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"capabilities:{capability}"
            # Use Redis Set for capability mapping
            pipe = self.redis.redis_client.pipeline()
            pipe.delete(key)  # Clear existing mapping
            if agent_ids:
                pipe.sadd(key, *agent_ids)
            pipe.expire(key, self.CAPABILITY_MAPPING_TTL)
            results = pipe.execute()
            return bool(results[-1])  # Check if expire was successful
        except Exception as e:
            logger.error(f"Error caching capability mapping for {capability}: {e}")
            return False

    async def discover_agents_by_capability(self, capability: str) -> List[str]:
        """
        Fast capability-based agent discovery.

        Args:
            capability: Capability name

        Returns:
            List of agent IDs with the capability
        """
        try:
            key = f"capabilities:{capability}"
            agent_ids = self.redis.redis_client.smembers(key)
            return list(agent_ids) if agent_ids else []
        except Exception as e:
            logger.error(f"Error discovering agents for capability {capability}: {e}")
            return []

    async def invalidate_capability_cache(self, capability: str) -> bool:
        """
        Invalidate capability cache.

        Args:
            capability: Capability name

        Returns:
            True if successful, False otherwise
        """
        key = f"capabilities:{capability}"
        return self.redis.delete(key)

    # Workflow State Management
    async def cache_workflow_state(
        self, workflow_id: str, state: Dict[str, Any]
    ) -> bool:
        """
        Cache workflow state for real-time tracking.

        Args:
            workflow_id: Workflow identifier
            state: Workflow state data

        Returns:
            True if successful, False otherwise
        """
        key = f"workflows:active:{workflow_id}"
        return self.redis.set(key, state, ttl=self.WORKFLOW_STATE_TTL)

    async def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached workflow state.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Workflow state data or None if not found
        """
        key = f"workflows:active:{workflow_id}"
        return self.redis.get(key)

    async def update_workflow_step(
        self, workflow_id: str, step_id: str, result: Dict[str, Any]
    ) -> bool:
        """
        Update workflow step result.

        Args:
            workflow_id: Workflow identifier
            step_id: Step identifier
            result: Step result data

        Returns:
            True if successful, False otherwise
        """
        key = f"workflows:steps:{workflow_id}:{step_id}"
        return self.redis.set(key, result, ttl=self.WORKFLOW_STATE_TTL)

    async def get_workflow_step(
        self, workflow_id: str, step_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get workflow step result.

        Args:
            workflow_id: Workflow identifier
            step_id: Step identifier

        Returns:
            Step result data or None if not found
        """
        key = f"workflows:steps:{workflow_id}:{step_id}"
        return self.redis.get(key)

    # Performance Caching
    async def cache_agent_metadata(
        self, agent_id: str, metadata: Dict[str, Any]
    ) -> bool:
        """
        Cache agent metadata for performance.

        Args:
            agent_id: Agent identifier
            metadata: Agent metadata

        Returns:
            True if successful, False otherwise
        """
        key = f"cache:agents:{agent_id}"
        return self.redis.set(key, metadata, ttl=self.AGENT_METADATA_TTL)

    async def get_agent_metadata(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached agent metadata.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent metadata or None if not found
        """
        key = f"cache:agents:{agent_id}"
        return self.redis.get(key)

    async def cache_workflow_template(
        self, template_id: str, template: Dict[str, Any]
    ) -> bool:
        """
        Cache workflow template.

        Args:
            template_id: Template identifier
            template: Template definition

        Returns:
            True if successful, False otherwise
        """
        key = f"cache:templates:{template_id}"
        return self.redis.set(key, template, ttl=self.AGENT_METADATA_TTL)

    async def get_workflow_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached workflow template.

        Args:
            template_id: Template identifier

        Returns:
            Template definition or None if not found
        """
        key = f"cache:templates:{template_id}"
        return self.redis.get(key)

    # Batch Operations
    async def batch_update_agent_status(
        self, agent_updates: List[Dict[str, Any]]
    ) -> bool:
        """
        Batch update multiple agent statuses.

        Args:
            agent_updates: List of agent update data

        Returns:
            True if successful, False otherwise
        """
        try:
            pipe = self.redis.redis_client.pipeline()

            for update in agent_updates:
                agent_id = update.get("agent_id")
                status = update.get("status", {})
                if agent_id:
                    key = f"agents:status:{agent_id}"
                    pipe.hset(key, mapping=status)
                    pipe.expire(key, self.AGENT_STATUS_TTL)

            results = pipe.execute()
            return all(results)
        except Exception as e:
            logger.error(f"Error in batch update agent status: {e}")
            return False

    async def batch_cache_capabilities(
        self, capability_mappings: Dict[str, List[str]]
    ) -> bool:
        """
        Batch cache capability mappings.

        Args:
            capability_mappings: Dictionary of capability to agent IDs

        Returns:
            True if successful, False otherwise
        """
        try:
            pipe = self.redis.redis_client.pipeline()

            for capability, agent_ids in capability_mappings.items():
                key = f"capabilities:{capability}"
                pipe.delete(key)  # Clear existing
                if agent_ids:
                    pipe.sadd(key, *agent_ids)
                pipe.expire(key, self.CAPABILITY_MAPPING_TTL)

            results = pipe.execute()
            return all(results)
        except Exception as e:
            logger.error(f"Error in batch cache capabilities: {e}")
            return False

    # Cache Statistics
    async def get_cache_hit_ratio(self) -> float:
        """
        Calculate cache hit ratio.

        Returns:
            Cache hit ratio (0.0 to 1.0)
        """
        try:
            info = self.redis.redis_client.info("stats")
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total = hits + misses
            return hits / total if total > 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating cache hit ratio: {e}")
            return 0.0

    async def get_agent_status_distribution(self) -> Dict[str, int]:
        """
        Get distribution of agent statuses.

        Returns:
            Dictionary with status counts
        """
        try:
            pattern = self._get_key("agents:status:*")
            keys = self.redis.redis_client.keys(pattern)

            status_counts = {"online": 0, "offline": 0, "busy": 0}
            for key in keys:
                status_data = self.redis.redis_client.hget(key, "status")
                if status_data:
                    status_counts[status_data] += 1

            return status_counts
        except Exception as e:
            logger.error(f"Error getting agent status distribution: {e}")
            return {"online": 0, "offline": 0, "busy": 0}

    async def get_workflow_metrics(self) -> Dict[str, Any]:
        """
        Get workflow performance metrics.

        Returns:
            Dictionary with workflow metrics
        """
        try:
            active_workflows = self.redis.redis_client.keys(
                self._get_key("workflows:active:*")
            )

            return {
                "active_workflows": len(active_workflows),
                "cache_hit_ratio": await self.get_cache_hit_ratio(),
                "agent_status_distribution": await self.get_agent_status_distribution(),
            }
        except Exception as e:
            logger.error(f"Error getting workflow metrics: {e}")
            return {
                "active_workflows": 0,
                "cache_hit_ratio": 0.0,
                "agent_status_distribution": {"online": 0, "offline": 0, "busy": 0},
            }

    # Cache Management
    async def clear_agent_cache(self, agent_id: str) -> bool:
        """
        Clear all cache entries for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            patterns = [
                f"agents:status:{agent_id}",
                f"agents:heartbeat:{agent_id}",
                f"cache:agents:{agent_id}",
            ]

            keys_to_delete = []
            for pattern in patterns:
                full_pattern = self._get_key(pattern)
                keys = self.redis.redis_client.keys(full_pattern)
                keys_to_delete.extend(keys)

            if keys_to_delete:
                result = self.redis.redis_client.delete(*keys_to_delete)
                return bool(result)
            return True
        except Exception as e:
            logger.error(f"Error clearing agent cache for {agent_id}: {e}")
            return False

    async def clear_workflow_cache(self, workflow_id: str) -> bool:
        """
        Clear all cache entries for a specific workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            patterns = [
                f"workflows:active:{workflow_id}",
                f"workflows:steps:{workflow_id}:*",
            ]

            keys_to_delete = []
            for pattern in patterns:
                full_pattern = self._get_key(pattern)
                keys = self.redis.redis_client.keys(full_pattern)
                keys_to_delete.extend(keys)

            if keys_to_delete:
                result = self.redis.redis_client.delete(*keys_to_delete)
                return bool(result)
            return True
        except Exception as e:
            logger.error(f"Error clearing workflow cache for {workflow_id}: {e}")
            return False

    async def clear_all_acp_cache(self) -> int:
        """
        Clear all ACP cache entries.

        Returns:
            Number of keys deleted
        """
        pattern = self._get_key("*")
        return self.redis.clear_pattern(pattern.replace(self.redis.key_prefix, ""))
