"""
Decorators for caching API responses and function results.
Provides various caching strategies with proper error handling.
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Typing for function results
T = TypeVar('T')


class CacheKeyGenerator:
    """
    Helper class to generate cache keys for function calls.
    Ensures keys are compatible with backend cache systems like Memcached.
    """

    @staticmethod
    def generate_key(func: Callable, args: tuple, kwargs: Dict[str, Any]) -> str:
        """
        Generate a cache key based on function name and arguments.
        Creates a deterministic and safe key that can be used with cache backends.

        Args:
            func: The function being cached
            args: Positional arguments to the function
            kwargs: Keyword arguments to the function

        Returns:
            str: Cache key string
        """
        # Create base key from function module and name
        base_key = f"{func.__module__}.{func.__qualname__}"

        # If no arguments, return base key
        if not args and not kwargs:
            return base_key

        # Convert arguments to a dictionary for consistent processing
        arg_dict = {}

        # If first argument is self or cls, skip it for the cache key
        if args and hasattr(args[0], '__class__'):
            method_args = args[1:]
        else:
            method_args = args

        # Add positional arguments with numeric keys
        for i, arg in enumerate(method_args):
            arg_dict[f'arg_{i}'] = str(arg)

        # Add keyword arguments, sorting to ensure consistent order
        for key, value in sorted(kwargs.items()):
            arg_dict[key] = str(value)

        # Convert arguments to JSON and hash to create a compact key
        args_json = json.dumps(arg_dict, sort_keys=True)
        args_hash = hashlib.md5(args_json.encode()).hexdigest()

        # Combine base key with argument hash
        return f"{base_key}:{args_hash}"


def cached_api_call(
    cache_timeout: int = 3600,
    key_prefix: str = "",
    skip_cache_on_error: bool = False
) -> Callable:
    """
    Decorator for caching API call results with advanced features.

    Caches function results for the specified time period.
    Handles errors gracefully and provides logging.

    Args:
        cache_timeout: Time in seconds to cache the result (default: 1 hour)
        key_prefix: Optional prefix for cache keys
        skip_cache_on_error: If True, errors will not be cached

    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            # Generate a unique cache key for this function call
            cache_key = CacheKeyGenerator.generate_key(func, args, kwargs)
            if key_prefix:
                cache_key = f"{key_prefix}:{cache_key}"

            # Try to get result from cache
            sentinel = object()
            cached_result = cache.get(cache_key, sentinel)

            if cached_result is not sentinel:
                logger.debug(f"Cache hit for {func.__name__}")
                return cast(T, cached_result)

            try:
                # Call the original function
                result = func(*args, **kwargs)

                # Cache the result if it's not None
                if result is not None:
                    cache.set(cache_key, result, cache_timeout)
                    logger.debug(f"Cached result for {func.__name__} with key {cache_key}")

                return result

            except Exception as e:
                # Log the error
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)

                # If we should cache errors, set None in cache
                if not skip_cache_on_error:
                    cache.set(cache_key, None, cache_timeout)

                # Return None for error case
                return None

        return wrapper
    return decorator


def clear_cache_for(func: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Clear cache for a specific function call with given arguments.
    Useful for manually invalidating cache entries.

    Args:
        func: The function whose cache should be cleared
        args: Positional arguments used in the original call
        kwargs: Keyword arguments used in the original call
    """
    cache_key = CacheKeyGenerator.generate_key(func, args, kwargs)
    cache.delete(cache_key)
    logger.debug(f"Cache cleared for {func.__name__} with key {cache_key}")
