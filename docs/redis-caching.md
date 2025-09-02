# Redis Caching in DevCycle

This document describes the Redis caching implementation in DevCycle, which provides distributed caching capabilities for improved performance and scalability.

## Overview

DevCycle now includes Redis-based caching that can be used throughout the application to:

- **Improve Performance**: Reduce database queries and expensive computations
- **Enable Distributed Caching**: Share cache across multiple application instances
- **Provide Automatic Expiration**: TTL-based cache invalidation
- **Support Rich Data Types**: JSON serialization for complex objects

## Architecture

The Redis caching system consists of:

1. **RedisCache Service** (`devcycle/core/cache/redis_cache.py`)
   - Core caching functionality
   - JSON serialization/deserialization
   - TTL support
   - Error handling and health checks

2. **Enhanced Agent Availability Service** (`devcycle/core/services/agent_availability_service_redis.py`)
   - Redis-backed agent availability caching
   - Improved performance for agent lookups
   - Distributed cache sharing

## Configuration

Redis configuration is managed through the existing `RedisConfig` in `devcycle/core/config/settings.py`:

```python
class RedisConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
```

Environment variables:
- `REDIS_HOST`: Redis server host
- `REDIS_PORT`: Redis server port
- `REDIS_PASSWORD`: Redis password (optional)
- `REDIS_DB`: Redis database number
- `REDIS_MAX_CONNECTIONS`: Maximum connections
- `REDIS_SOCKET_TIMEOUT`: Socket timeout
- `REDIS_SOCKET_CONNECT_TIMEOUT`: Connection timeout
- `REDIS_RETRY_ON_TIMEOUT`: Retry on timeout

## Usage

### Basic Caching

```python
from devcycle.core.cache.redis_cache import get_cache

# Get cache instance
cache = get_cache("my_app:")

# Set a value with TTL
cache.set("user:123", {"name": "John", "email": "john@example.com"}, ttl=300)

# Get a value
user_data = cache.get("user:123")

# Check if key exists
exists = cache.exists("user:123")

# Delete a key
cache.delete("user:123")

# Clear all keys with pattern
cache.clear_pattern("user:*")
```

### Agent Availability Caching

```python
from devcycle.core.services.agent_availability_service_redis import RedisAgentAvailabilityService

# Initialize service with Redis caching
service = RedisAgentAvailabilityService(agent_repository)

# Check agent availability (uses cache)
available = await service.is_agent_available("agent1")

# Get agent capabilities (uses cache)
capabilities = await service.get_agent_capabilities("agent1")

# Clear cache for specific agent
service.clear_cache("agent1")

# Get cache statistics
stats = service.get_cache_stats()
```

## Cache Keys

The system uses structured cache keys with prefixes:

### Agent Availability Service
- `devcycle:agent:availability:{agent_id}` - Agent availability status
- `devcycle:agent:capabilities:{agent_id}` - Agent capabilities
- `devcycle:agent:load:{agent_id}` - Agent load information
- `devcycle:agent:agents_by_capability:{capability}` - Agents by capability

### Session Management
- `jwt_blacklist:{token_hash}` - Blacklisted JWT tokens
- `user_sessions:{user_id}` - User session tracking
- `session_info:{session_id}` - Session metadata

## Performance Benefits

### Before Redis Caching
- Agent availability checks required database queries
- In-memory cache limited to single instance
- No cache sharing between application instances

### After Redis Caching
- **Reduced Database Load**: Cache hits avoid database queries
- **Distributed Caching**: Multiple instances share cache
- **Improved Response Times**: Sub-millisecond cache access
- **Better Scalability**: Horizontal scaling with shared cache

### Example Performance Improvement
```
Without Cache: 100ms (database query)
With Cache:    1ms (Redis lookup)
Improvement:   99% faster response time
```

## Monitoring and Health Checks

### Cache Statistics
```python
stats = cache.get_stats()
# Returns:
# {
#     "total_keys": 150,
#     "redis_connected": True,
#     "redis_version": "7.0.0",
#     "used_memory": "2.5M",
#     "connected_clients": 3
# }
```

### Health Checks
```python
healthy = cache.health_check()
# Returns: True if Redis is accessible, False otherwise
```

## Error Handling

The Redis cache service includes comprehensive error handling:

- **Connection Failures**: Graceful degradation with fallback
- **Serialization Errors**: JSON encoding/decoding error handling
- **Timeout Handling**: Configurable timeouts and retries
- **Logging**: Detailed error logging for debugging

## Testing

The Redis caching system includes comprehensive tests:

```bash
# Run Redis cache tests
poetry run pytest tests/unit/test_redis_cache.py -v

# Run agent availability service tests
poetry run pytest tests/unit/test_agent_availability_service_redis.py -v
```

## Demo

Run the Redis caching demo to see the system in action:

```bash
poetry run python examples/redis_caching_demo.py
```

The demo shows:
- Basic caching operations
- Agent availability caching
- Performance comparisons
- Cache hit ratios

## Migration from In-Memory Cache

To migrate from the existing in-memory cache to Redis:

1. **Replace Service**: Use `RedisAgentAvailabilityService` instead of `AgentAvailabilityService`
2. **Update Dependencies**: Ensure Redis is available in your environment
3. **Configure Redis**: Set appropriate Redis configuration
4. **Test**: Run tests to ensure functionality works correctly

## Best Practices

1. **Use Appropriate TTLs**: Set reasonable expiration times for different data types
2. **Key Naming**: Use consistent, hierarchical key naming conventions
3. **Error Handling**: Always handle cache failures gracefully
4. **Monitoring**: Monitor cache hit ratios and performance metrics
5. **Memory Management**: Be mindful of Redis memory usage

## Future Enhancements

Potential future improvements:

- **Cache Warming**: Pre-populate cache with frequently accessed data
- **Cache Invalidation**: Event-driven cache invalidation
- **Compression**: Compress large cache values
- **Metrics**: Detailed performance and usage metrics
- **Clustering**: Redis cluster support for high availability
