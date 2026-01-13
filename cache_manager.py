"""
Cache Manager Module
Intelligent caching system for price data, fundamentals, and calculations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import hashlib
from typing import Optional, Dict, Any
import pickle

class CacheManager:
    """Manages caching of data with TTL and invalidation"""
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize Cache Manager
        
        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = cache_dir
        self.memory_cache = {}
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
    def _generate_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from parameters
        
        Args:
            prefix: Cache key prefix
            params: Parameters to hash
        
        Returns:
            Cache key string
        """
        # Sort params for consistent hashing
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}_{param_hash}"
    
    def _get_cache_path(self, key: str) -> str:
        """Get file path for cache key"""
        return os.path.join(self.cache_dir, f"{key}.pkl")
    
    def _is_cache_valid(self, cache_data: Dict, ttl: int) -> bool:
        """
        Check if cache is still valid based on TTL
        
        Args:
            cache_data: Cached data with metadata
            ttl: Time to live in seconds
        
        Returns:
            True if cache is valid
        """
        if 'timestamp' not in cache_data:
            return False
        
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        age_seconds = (datetime.now() - cache_time).total_seconds()
        
        return age_seconds < ttl
    
    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        """
        Get data from cache
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
        
        Returns:
            Cached data or None if not found/expired
        """
        # Check memory cache first
        if key in self.memory_cache:
            cache_data = self.memory_cache[key]
            if self._is_cache_valid(cache_data, ttl):
                return cache_data['data']
            else:
                del self.memory_cache[key]
        
        # Check file cache
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    cache_data = pickle.load(f)
                
                if self._is_cache_valid(cache_data, ttl):
                    # Load into memory cache
                    self.memory_cache[key] = cache_data
                    return cache_data['data']
                else:
                    # Cache expired, delete file
                    os.remove(cache_path)
            except Exception as e:
                print(f"Error reading cache {key}: {e}")
        
        return None
    
    def set(self, key: str, data: Any) -> bool:
        """
        Store data in cache
        
        Args:
            key: Cache key
            data: Data to cache
        
        Returns:
            True if successful
        """
        cache_data = {
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in memory cache
        self.memory_cache[key] = cache_data
        
        # Store in file cache
        try:
            cache_path = self._get_cache_path(key)
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            return True
        except Exception as e:
            print(f"Error writing cache {key}: {e}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate specific cache entry
        
        Args:
            key: Cache key to invalidate
        
        Returns:
            True if invalidated
        """
        # Remove from memory
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        # Remove file
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                return True
            except Exception as e:
                print(f"Error invalidating cache {key}: {e}")
        
        return False
    
    def clear_all(self) -> bool:
        """Clear all cache"""
        try:
            # Clear memory cache
            self.memory_cache.clear()
            
            # Clear file cache
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    os.remove(os.path.join(self.cache_dir, filename))
            
            return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        file_count = 0
        total_size = 0
        
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    file_count += 1
                    file_path = os.path.join(self.cache_dir, filename)
                    total_size += os.path.getsize(file_path)
        
        return {
            'memory_entries': len(self.memory_cache),
            'file_entries': file_count,
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': self.cache_dir
        }
    
    # Specialized cache methods for common operations
    
    def get_price_data(self, symbols: list, lookback: int) -> Optional[Dict]:
        """Get cached price data"""
        key = self._generate_key('prices', {
            'symbols': sorted(symbols),
            'lookback': lookback
        })
        return self.get(key, ttl=3600)  # 1 hour TTL
    
    def set_price_data(self, symbols: list, lookback: int, data: Dict) -> bool:
        """Cache price data"""
        key = self._generate_key('prices', {
            'symbols': sorted(symbols),
            'lookback': lookback
        })
        return self.set(key, data)
    
    def get_fundamentals(self, symbols: list) -> Optional[pd.DataFrame]:
        """Get cached fundamentals"""
        key = self._generate_key('fundamentals', {
            'symbols': sorted(symbols)
        })
        return self.get(key, ttl=86400)  # 24 hour TTL
    
    def set_fundamentals(self, symbols: list, data: pd.DataFrame) -> bool:
        """Cache fundamentals"""
        key = self._generate_key('fundamentals', {
            'symbols': sorted(symbols)
        })
        return self.set(key, data)
    
    def get_rs_results(self, symbols: list, config: Dict) -> Optional[pd.DataFrame]:
        """Get cached RS calculations"""
        key = self._generate_key('rs_results', {
            'symbols': sorted(symbols),
            'config': config
        })
        return self.get(key, ttl=3600)  # 1 hour TTL
    
    def set_rs_results(self, symbols: list, config: Dict, data: pd.DataFrame) -> bool:
        """Cache RS results"""
        key = self._generate_key('rs_results', {
            'symbols': sorted(symbols),
            'config': config
        })
        return self.set(key, data)
    
    def get_screening_results(self, params: Dict) -> Optional[pd.DataFrame]:
        """Get cached screening results"""
        key = self._generate_key('screening', params)
        return self.get(key, ttl=1800)  # 30 minute TTL
    
    def set_screening_results(self, params: Dict, data: pd.DataFrame) -> bool:
        """Cache screening results"""
        key = self._generate_key('screening', params)
        return self.set(key, data)


# Global cache instance
_cache_instance = None

def get_cache() -> CacheManager:
    """Get global cache instance (singleton pattern)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
