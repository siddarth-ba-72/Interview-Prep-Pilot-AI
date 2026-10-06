package com.preppilot.topicservice.dto;

import java.time.Instant;

public class UsageDtos {

    /** {@code tier} is STUDENT or STANDARD. */
    public record UsageResponse(
        String tier,
        long windowHours,
        TopicUsage topics,
        ActionUsage learnMessages,
        ActionUsage tests,
        ActionUsage mockInterviews
    ) {}

    /** {@code limit} is null when the user's tier has no topic limit. */
    public record TopicUsage(long used, Integer limit) {}

    /**
     * {@code used} counts uses inside the current window. {@code availableAt} is set only while
     * the user is locked out ({@code remaining} is then 0) and says when the lock lifts.
     */
    public record ActionUsage(int used, int limit, int remaining, Instant availableAt) {}
}
