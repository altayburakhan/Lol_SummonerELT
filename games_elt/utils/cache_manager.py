from typing import Dict, Any, Optional
import time
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_dir: str = ".cache", ttl: int = 3600):
        """
        Initialize the cache manager
        
        Args:
            cache_dir (str): Directory to store cache files
            ttl (int): Time to live in seconds for cached items
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_file(self, key: str) -> Path:
        """Get the cache file path for a key"""
        return self.cache_dir / f"{key}.json"
        
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a value from cache
        
        Args:
            key (str): Cache key
            
        Returns:
            Optional[Dict[str, Any]]: Cached value if found and not expired
        """
        # Check memory cache first
        if key in self.memory_cache:
            data = self.memory_cache[key]
            if time.time() - data["timestamp"] <= self.ttl:
                return data["value"]
            else:
                del self.memory_cache[key]
                
        # Check file cache
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            try:
                with cache_file.open("r") as f:
                    data = json.load(f)
                    
                if time.time() - data["timestamp"] <= self.ttl:
                    # Update memory cache
                    self.memory_cache[key] = data
                    return data["value"]
                else:
                    # Remove expired cache file
                    cache_file.unlink()
            except Exception as e:
                logger.error(f"Error reading cache file {cache_file}: {str(e)}")
                
        return None
        
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Set a value in cache
        
        Args:
            key (str): Cache key
            value (Dict[str, Any]): Value to cache
        """
        data = {
            "timestamp": time.time(),
            "value": value
        }
        
        # Update memory cache
        self.memory_cache[key] = data
        
        # Update file cache
        cache_file = self._get_cache_file(key)
        try:
            with cache_file.open("w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error writing cache file {cache_file}: {str(e)}")
            
    def clear(self, key: str = None) -> None:
        """
        Clear cache entries
        
        Args:
            key (str, optional): Specific key to clear. If None, clears all cache
        """
        if key is None:
            # Clear all cache
            self.memory_cache.clear()
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"Error deleting cache file {cache_file}: {str(e)}")
        else:
            # Clear specific key
            if key in self.memory_cache:
                del self.memory_cache[key]
                
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"Error deleting cache file {cache_file}: {str(e)}")
                    
    def cleanup_expired(self) -> None:
        """Remove all expired cache entries"""
        current_time = time.time()
        
        # Clean memory cache
        expired_keys = [
            key for key, data in self.memory_cache.items()
            if current_time - data["timestamp"] > self.ttl
        ]
        for key in expired_keys:
            del self.memory_cache[key]
            
        # Clean file cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with cache_file.open("r") as f:
                    data = json.load(f)
                    
                if current_time - data["timestamp"] > self.ttl:
                    cache_file.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up cache file {cache_file}: {str(e)}") 