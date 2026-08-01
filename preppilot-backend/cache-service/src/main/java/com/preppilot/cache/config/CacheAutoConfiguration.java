package com.preppilot.cache.config;

import com.github.benmanes.caffeine.cache.Caffeine;
import com.preppilot.cache.service.GenericCacheService;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.caffeine.CaffeineCache;
import org.springframework.cache.support.SimpleCacheManager;
import org.springframework.context.annotation.Bean;

import java.util.List;

@AutoConfiguration
@EnableCaching
@EnableConfigurationProperties(CacheProperties.class)
@ConditionalOnClass(Caffeine.class)
public class CacheAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public CacheManager cacheManager(CacheProperties properties) {
        SimpleCacheManager manager = new SimpleCacheManager();
        List<CaffeineCache> caches = properties.getRegions().entrySet().stream()
                .map(entry -> buildCache(entry.getKey(), entry.getValue()))
                .toList();
        manager.setCaches(caches);
        return manager;
    }

    @Bean
    @ConditionalOnMissingBean
    public GenericCacheService genericCacheService(CacheManager cacheManager) {
        return new GenericCacheService(cacheManager);
    }

    private CaffeineCache buildCache(String name, CacheProperties.RegionConfig config) {
        Caffeine<Object, Object> builder = Caffeine.newBuilder()
                .maximumSize(config.getMaximumSize())
                .expireAfterWrite(config.getExpireAfterWrite());

        if (config.isRecordStats()) {
            builder.recordStats();
        }

        return new CaffeineCache(name, builder.build());
    }
}