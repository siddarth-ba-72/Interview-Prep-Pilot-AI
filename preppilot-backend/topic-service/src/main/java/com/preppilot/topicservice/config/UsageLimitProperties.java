package com.preppilot.topicservice.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;

/** Binds {@code usage-limits.*} from application.yml. */
@ConfigurationProperties(prefix = "usage-limits")
public record UsageLimitProperties(Duration window, Tier student, Tier standard) {

    /** {@code maxTopics} is null when the tier has no topic limit. */
    public record Tier(Integer maxTopics, int learnMessages, int tests, int mockInterviews) {}
}
