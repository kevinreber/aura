# Caching Implementation Guide

## Overview

This guide describes the comprehensive caching system implemented in the Daily MCP Server to reduce API rate limiting and improve performance. The caching layer uses Redis as the primary cache with an in-memory fallback for development and error scenarios.

## Architecture

### Cache Service

- **Primary**: Redis with async support
- **Fallback**: In-memory cache with TTL
- **Location**: `mcp_server/utils/cache.py`

### Key Features

- ✅ **Automatic fallback** from Redis to in-memory cache
- ✅ **TTL-based expiration** for data freshness
- ✅ **Smart cache invalidation** for write operations
- ✅ **Tool-specific TTL values** based on data volatility
- ✅ **Cache statistics** for monitoring
- ✅ **JSON serialization** for complex objects

## Cache TTL Strategy

| Data Type               | TTL        | Reason                                 |
| ----------------------- | ---------- | -------------------------------------- |
| **Weather Geocoding**   | 7 days     | Coordinates don't change               |
| **Weather Forecast**    | 30 minutes | Weather updates frequently             |
| **Financial Stocks**    | 5 minutes  | Market volatility during trading hours |
| **Financial Crypto**    | 2 minutes  | Higher volatility than stocks          |
| **Mobility Directions** | 15 minutes | Traffic conditions change              |
| **Calendar Events**     | 10 minutes | Events don't change frequently         |

## Implementation by Tool

### Financial Tool (`tools/financial.py`)

**Problem**: Alpha Vantage API has strict rate limits (5 calls/minute for free tier)

**Solution**:

- Cache individual stock symbols separately
- Batch crypto requests but cache individually
- Use shorter TTL for crypto due to higher volatility

```python
# Before: 5 stock symbols = 5 API calls every time
# After: 5 stock symbols = 0-5 API calls depending on cache hits
```

### Weather Tool (`tools/weather.py`)

**Problem**: 2 API calls per request (geocoding + weather)

**Solution**:

- Cache geocoding results with long TTL (coordinates don't change)
- Cache weather forecasts with moderate TTL
- Separate cache keys for different locations and dates

```python
# Before: Every weather request = 2 API calls
# After: Repeated location requests = 0-1 API calls
```

### Mobility Tool (`tools/mobility.py`)

**Problem**: Google Maps API rate limits for direction requests

**Solution**:

- Cache direction results by origin + destination + mode
- Moderate TTL to account for traffic changes
- Smart cache key generation

```python
# Before: Same route requested = full API call each time
# After: Same route = cached result for 15 minutes
```

### Calendar Tool (`tools/calendar.py`)

**Problem**: Multiple Google Calendar API calls for events

**Solution**:

- Cache events by date and date ranges
- Smart cache invalidation when events are created/updated/deleted
- Efficient bulk range queries

```python
# Before: List events for same date = API call each time
# After: Recent dates served from cache
```

## Cache Key Strategy

Cache keys are generated using a consistent pattern:

```python
cache_key = generate_cache_key(prefix, *args, **kwargs)
# Example: "weather_geocoding:san_francisco_ca"
# Example: "financial_stocks:MSFT"
# Example: "calendar_events:2024-12-18"
```

## Configuration

Add to your `.env` file:

```env
# Redis URL (optional - will use in-memory if not provided)
REDIS_URL=redis://localhost:6379

# Default cache TTL in seconds (optional - defaults to 300)
CACHE_TTL=300
```

## Monitoring

### Cache Statistics Endpoint

```http
GET /cache/stats
```

Returns:

```json
{
  "cache_stats": {
    "redis_connected": true,
    "memory_cache_size": 42,
    "redis_size": 156
  },
  "status": "success"
}
```

### Logging

Cache operations are logged at debug level:

```
2024-12-18 10:30:00 | DEBUG | cache | Cache hit (Redis): weather_geocoding:london_uk
2024-12-18 10:30:15 | DEBUG | cache | Cache set (Redis): financial_stocks:MSFT (TTL: 300s)
2024-12-18 10:30:30 | DEBUG | cache | Cached 3 calendar events for 2024-12-18
```

## Cache Invalidation

### Automatic Invalidation

- **Calendar events**: Automatically invalidated when events are created, updated, or deleted
- **TTL expiration**: All cached data expires based on TTL values
- **Error scenarios**: Failed API calls don't update cache

### Manual Cache Management

For development/testing:

```python
from mcp_server.utils.cache import get_cache_service

# Clear all cache
cache = await get_cache_service()
await cache.clear()

# Delete specific key
await cache.delete("weather_forecast:37.7749_-122.4194:2024-12-18")
```

## Performance Impact

### Before Caching

- **Financial Tool**: 5 stock symbols = 5 API calls + delay
- **Weather Tool**: 2 API calls per request
- **Calendar Tool**: 1+ API calls per date query
- **Mobility Tool**: 1 API call per route request

### After Caching

- **Financial Tool**: 5 stock symbols = 0-5 API calls (depending on cache)
- **Weather Tool**: 0-2 API calls (geocoding often cached)
- **Calendar Tool**: 0-1 API calls (recent dates cached)
- **Mobility Tool**: 0-1 API calls (common routes cached)

**Estimated API Call Reduction**: 60-90% for typical usage patterns

## Error Handling

The cache system is designed to fail gracefully:

1. **Redis unavailable**: Falls back to in-memory cache
2. **Cache read error**: Proceeds with API call
3. **Cache write error**: Logs warning but continues
4. **JSON serialization error**: Skips caching for that item

## Best Practices

### For Developers

1. **Use appropriate TTL**: Match TTL to data volatility
2. **Cache at the right level**: Cache expensive operations, not cheap ones
3. **Handle cache misses gracefully**: Always have fallback to API
4. **Monitor cache hit rates**: Use `/cache/stats` endpoint

### For Operations

1. **Monitor Redis memory usage**: Set appropriate memory limits
2. **Monitor cache hit rates**: Low hit rates may indicate TTL issues
3. **Set up Redis persistence**: For production deployments
4. **Monitor API rate limits**: Track remaining quota

## Deployment Considerations

### Development

- Uses in-memory cache by default
- No Redis dependency required
- Cache stats show `redis_connected: false`

### Production

- Deploy Redis instance
- Set `REDIS_URL` environment variable
- Monitor Redis metrics
- Consider Redis clustering for high availability

## Security Considerations

- **No sensitive data caching**: API keys and personal data are not cached
- **Redis access**: Secure Redis with authentication in production
- **Cache isolation**: Each environment should have separate Redis instances

## Troubleshooting

### Common Issues

1. **High memory usage**: Reduce TTL values or implement cache size limits
2. **Stale data**: Check TTL values and cache invalidation logic
3. **Cache misses**: Verify cache key generation is consistent
4. **Redis connection errors**: Check Redis availability and network

### Debug Commands

```bash
# Check Redis connectivity
redis-cli ping

# Monitor cache operations
redis-cli monitor

# Check memory usage
redis-cli info memory

# View cache keys
redis-cli keys "*"
```

## Future Enhancements

Potential improvements:

- **Cache compression**: For large response objects
- **Distributed caching**: For multi-instance deployments
- **Cache warming**: Pre-populate common requests
- **Metrics integration**: Prometheus/Grafana monitoring
- **Advanced invalidation**: Tag-based cache invalidation
