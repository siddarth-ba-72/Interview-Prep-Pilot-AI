package com.preppilot.cache.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

@ConfigurationProperties(prefix = "app.caching")
public class CacheProperties {

    /**
     * Each entry is one cache "region" — e.g. users, topics, sessions.
     * Configured per consuming service in that service's application.yml.
     */
    private Map<String, RegionConfig> regions = new LinkedHashMap<>();

    public Map<String, RegionConfig> getRegions() {
        return regions;
    }

    public void setRegions(Map<String, RegionConfig> regions) {
        this.regions = regions;
    }

    public static class RegionConfig {
        private long maximumSize = 10_000;
        private Duration expireAfterWrite = Duration.ofMinutes(30);
        private boolean recordStats = true;

        public long getMaximumSize() {
            return maximumSize;
        }

        public void setMaximumSize(long maximumSize) {
            this.maximumSize = maximumSize;
        }

        public Duration getExpireAfterWrite() {
            return expireAfterWrite;
        }

        public void setExpireAfterWrite(Duration expireAfterWrite) {
            this.expireAfterWrite = expireAfterWrite;
        }

        public boolean isRecordStats() {
            return recordStats;
        }

        public void setRecordStats(boolean recordStats) {
            this.recordStats = recordStats;
        }
    }
}