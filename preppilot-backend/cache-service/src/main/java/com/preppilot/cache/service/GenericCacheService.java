package com.preppilot.cache.service;

import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;

import java.util.function.Function;

public class GenericCacheService {

    private final CacheManager cacheManager;

    public GenericCacheService(CacheManager cacheManager) {
        this.cacheManager = cacheManager;
    }

    public <V> V get(String region, Object key, Class<V> type) {
        Cache.ValueWrapper wrapper = requireCache(region).get(key);
        return wrapper != null ? type.cast(wrapper.get()) : null;
    }

    /**
     * Reads from cache; on miss, loads via the supplied function and populates the cache.
     */
    public <V> V getOrLoad(String region, Object key, Class<V> type, Function<Object, V> loader) {
        V cached = get(region, key, type);
        if (cached != null) {
            return cached;
        }
        V loaded = loader.apply(key);
        if (loaded != null) {
            put(region, key, loaded);
        }
        return loaded;
    }

    public void put(String region, Object key, Object value) {
        requireCache(region).put(key, value);
    }

    public void evict(String region, Object key) {
        requireCache(region).evict(key);
    }

    public void evictAll(String region) {
        requireCache(region).clear();
    }

    private Cache requireCache(String region) {
        Cache cache = cacheManager.getCache(region);
        if (cache == null) {
            throw new IllegalArgumentException(
                    "No cache region configured: '" + region + "'. Check app.caching.regions in application.yml"
            );
        }
        return cache;
    }
}