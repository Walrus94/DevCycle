"""
Redis Caching Demo for DevCycle.

This example demonstrates how to use Redis caching in the DevCycle system
for improved performance and distributed caching capabilities.
"""

import asyncio
import time
from typing import Any, Dict

from devcycle.core.cache.redis_cache import get_cache
from devcycle.core.logging import get_logger

logger = get_logger(__name__)


async def demo_basic_caching() -> None:
    """Demonstrate basic Redis caching functionality."""
    print("🚀 Redis Caching Demo - Basic Operations")
    print("=" * 50)

    # Get cache instance
    cache = get_cache("demo:")

    # Test basic operations
    print("1. Setting cache values...")
    cache.set("user:123", {"name": "John Doe", "email": "john@example.com"}, ttl=60)
    cache.set("config:app", {"version": "1.0.0", "debug": True}, ttl=300)
    cache.set("temp:data", "temporary data", ttl=10)

    print("✅ Cache values set")

    # Test getting values
    print("\n2. Getting cache values...")
    user_data = cache.get("user:123")
    config_data = cache.get("config:app")
    temp_data = cache.get("temp:data")

    print(f"User data: {user_data}")
    print(f"Config data: {config_data}")
    print(f"Temp data: {temp_data}")

    # Test existence check
    print("\n3. Checking cache existence...")
    exists = cache.exists("user:123")
    print(f"User 123 exists: {exists}")

    # Test TTL
    print("\n4. Checking TTL...")
    ttl = cache.get_ttl("user:123")
    print(f"User 123 TTL: {ttl} seconds")

    # Test cache stats
    print("\n5. Cache statistics...")
    stats = cache.get_stats()
    print(f"Total keys: {stats['total_keys']}")
    print(f"Redis connected: {stats['redis_connected']}")

    # Test health check
    print("\n6. Health check...")
    healthy = cache.health_check()
    print(f"Cache healthy: {healthy}")


async def demo_agent_caching() -> None:
    """Demonstrate agent availability caching."""
    print("\n\n🤖 Agent Availability Caching Demo")
    print("=" * 50)

    # Simulate agent data
    agent_data = {
        "availability:agent1": {
            "available": True,
            "status": "online",
            "capabilities": ["nlp", "code_generation"],
            "last_check": time.time(),
        },
        "capabilities:agent1": {
            "capabilities": ["nlp", "code_generation", "data_analysis"],
            "last_check": time.time(),
        },
        "load:agent1": {
            "load_info": {
                "agent_id": "agent1",
                "status": "online",
                "current_tasks": 2,
                "max_concurrent_tasks": 5,
                "available_slots": 3,
                "response_time_ms": 150,
            },
            "last_check": time.time(),
        },
    }

    cache = get_cache("agent:")

    # Set agent cache data
    print("1. Setting agent cache data...")
    for key, data in agent_data.items():
        cache.set(key, data, ttl=30)

    print("✅ Agent cache data set")

    # Simulate cache hits
    print("\n2. Simulating cache hits...")
    availability = cache.get("availability:agent1")
    capabilities = cache.get("capabilities:agent1")
    load_info = cache.get("load:agent1")

    if availability:
        print(f"Agent 1 available: {availability['available']}")
    if capabilities:
        print(f"Agent 1 capabilities: {capabilities['capabilities']}")
    if load_info and "load_info" in load_info:
        print(f"Agent 1 available slots: {load_info['load_info']['available_slots']}")

    # Test cache pattern clearing
    print("\n3. Clearing agent cache...")
    cleared = cache.clear_pattern("availability:*")
    print(f"Cleared {cleared} availability entries")


async def demo_performance_comparison() -> None:
    """Demonstrate performance benefits of caching."""
    print("\n\n⚡ Performance Comparison Demo")
    print("=" * 50)

    cache = get_cache("perf:")

    # Simulate expensive operation
    def expensive_operation(key: str) -> Dict[str, Any]:
        """Simulate an expensive operation (e.g., database query)."""
        time.sleep(0.1)  # Simulate 100ms operation
        return {
            "key": key,
            "result": f"Expensive computation for {key}",
            "timestamp": time.time(),
        }

    # Test without cache
    print("1. Testing without cache...")
    start_time = time.time()
    for i in range(5):
        result = expensive_operation(f"operation_{i}")
    no_cache_time = time.time() - start_time
    print(f"Without cache: {no_cache_time:.2f} seconds")

    # Test with cache
    print("\n2. Testing with cache...")
    start_time = time.time()
    for i in range(5):
        cache_key = f"operation_{i}"
        cached_result = cache.get(cache_key)

        if cached_result is None:
            # Cache miss - perform expensive operation
            result = expensive_operation(f"operation_{i}")
            cache.set(cache_key, result, ttl=60)
        else:
            # Cache hit - use cached result
            result = cached_result

    with_cache_time = time.time() - start_time
    print(f"With cache: {with_cache_time:.2f} seconds")

    # Calculate improvement
    improvement = ((no_cache_time - with_cache_time) / no_cache_time) * 100
    print(f"\nPerformance improvement: {improvement:.1f}%")

    # Test cache hit ratio
    print("\n3. Testing cache hit ratio...")
    cache_hits = 0
    total_requests = 10

    for i in range(total_requests):
        cache_key = f"operation_{i % 5}"  # Cycle through 5 operations
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            cache_hits += 1

    hit_ratio = (cache_hits / total_requests) * 100
    print(f"Cache hit ratio: {hit_ratio:.1f}% ({cache_hits}/{total_requests})")


async def main() -> None:
    """Run all demos."""
    try:
        await demo_basic_caching()
        await demo_agent_caching()
        await demo_performance_comparison()

        print("\n\n🎉 Redis Caching Demo Complete!")
        print("=" * 50)
        print("Key benefits of Redis caching:")
        print("✅ Improved performance through reduced database queries")
        print("✅ Distributed caching across multiple application instances")
        print("✅ Automatic expiration with TTL support")
        print("✅ Rich data types and operations")
        print("✅ High availability and persistence")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("Make sure Redis is running and accessible.")


if __name__ == "__main__":
    asyncio.run(main())
