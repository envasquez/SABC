# Cache management utilities
import hashlib
import logging
from typing import Any, Optional

from django.conf import settings
from django.core.cache import cache, caches
from django.core.cache.utils import make_key

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Centralized cache management for SABC application.
    Provides cache invalidation, key generation, and performance monitoring.
    """

    # Cache timeouts (in seconds)
    TIMEOUTS = {
        "tournament_list": 300,  # 5 minutes
        "tournament_detail": 900,  # 15 minutes
        "aoy_results": 600,  # 10 minutes
        "roster": 1800,  # 30 minutes
        "calendar": 3600,  # 1 hour
        "statistics": 1800,  # 30 minutes
    }

    @classmethod
    def get_cache_key(cls, category: str, *args, **kwargs) -> str:
        """Generate consistent cache keys."""
        key_parts = [category]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

        key_string = "_".join(key_parts)

        # Hash long keys to avoid Redis key length limits
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{category}_{key_hash}"

        return key_string

    @classmethod
    def get(cls, category: str, *args, **kwargs) -> Optional[Any]:
        """Get value from cache with logging."""
        cache_key = cls.get_cache_key(category, *args, **kwargs)
        try:
            value = cache.get(cache_key)
            if value is not None:
                logger.debug(f"Cache hit: {cache_key}")
            else:
                logger.debug(f"Cache miss: {cache_key}")
            return value
        except Exception as e:
            logger.warning(f"Cache get error for {cache_key}: {e}")
            return None

    @classmethod
    def set(
        cls, category: str, value: Any, timeout: Optional[int] = None, *args, **kwargs
    ):
        """Set value in cache with automatic timeout."""
        cache_key = cls.get_cache_key(category, *args, **kwargs)
        if timeout is None:
            timeout = cls.TIMEOUTS.get(category, 300)

        try:
            cache.set(cache_key, value, timeout)
            logger.debug(f"Cache set: {cache_key} (timeout: {timeout}s)")
        except Exception as e:
            logger.warning(f"Cache set error for {cache_key}: {e}")

    @classmethod
    def delete(cls, category: str, *args, **kwargs):
        """Delete specific cache key."""
        cache_key = cls.get_cache_key(category, *args, **kwargs)
        try:
            cache.delete(cache_key)
            logger.debug(f"Cache deleted: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache delete error for {cache_key}: {e}")

    @classmethod
    def invalidate_tournament(cls, tournament_id: int):
        """Invalidate all tournament-related caches."""
        patterns = [
            ("tournament_detail", tournament_id),
            ("tournament_list",),
            ("aoy_results",),
            ("statistics",),
        ]

        for pattern in patterns:
            try:
                cls.delete(*pattern)
            except Exception as e:
                logger.warning(f"Error invalidating cache pattern {pattern}: {e}")

    @classmethod
    def invalidate_year(cls, year: int):
        """Invalidate all year-based caches."""
        patterns = [
            ("tournament_list", year),
            ("aoy_results", year),
            ("roster", year),
            ("calendar", year),
        ]

        for pattern in patterns:
            try:
                cls.delete(*pattern)
            except Exception as e:
                logger.warning(f"Error invalidating year cache pattern {pattern}: {e}")

    @classmethod
    def clear_all(cls):
        """Clear all application caches."""
        try:
            cache.clear()
            logger.info("All caches cleared")
        except Exception as e:
            logger.error(f"Error clearing all caches: {e}")


def cache_result(category: str, timeout: Optional[int] = None):
    """Decorator for caching function results."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = CacheManager.get_cache_key(
                category, func.__name__, *args, **kwargs
            )

            # Try to get from cache first
            cached_result = CacheManager.get(category, func.__name__, *args, **kwargs)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            CacheManager.set(category, result, timeout, func.__name__, *args, **kwargs)
            return result

        return wrapper

    return decorator


# Cache warming utilities
def warm_cache():
    """Warm up commonly accessed cache entries."""
    logger.info("Starting cache warming...")

    try:
        # Import here to avoid circular imports
        from datetime import date

        from tournaments.views_optimized import get_aoy_results_optimized

        current_year = date.today().year

        # Warm AOY results for current year
        get_aoy_results_optimized(current_year)
        logger.info(f"Warmed AOY results cache for {current_year}")

    except Exception as e:
        logger.error(f"Error warming cache: {e}")
