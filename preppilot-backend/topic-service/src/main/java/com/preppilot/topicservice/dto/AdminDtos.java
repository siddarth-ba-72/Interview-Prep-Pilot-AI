package com.preppilot.topicservice.dto;

import java.util.List;

/**
 * Read-only views for the admin dashboard. They carry topic names and session counts only:
 * no scores, answers, reports or chat messages.
 */
public class AdminDtos {

    /**
     * {@code active}: tests and interviews still in progress. {@code completed}: everything
     * else, including interviews whose time ran out before the user came back to finish them.
     */
    public record SessionCounts(long active, long completed) {
        public static final SessionCounts NONE = new SessionCounts(0, 0);

        public SessionCounts plus(SessionCounts other) {
            return new SessionCounts(active + other.active, completed + other.completed);
        }
    }

    public record ActivitySummary(long topics, SessionCounts tests, SessionCounts interviews) {}

    public record UserActivity(String userId, long topics, SessionCounts tests, SessionCounts interviews) {}

    public record TopicActivity(String name, SessionCounts tests, SessionCounts interviews) {}

    /** Sessions of topics the user has since deleted (deleting a topic keeps its sessions). */
    public record DeletedTopicsActivity(SessionCounts tests, SessionCounts interviews) {}

    /** {@code deletedTopics} is null when none of the user's sessions belong to a deleted topic.
     * {@code tests} and {@code interviews} are totals over all sessions, deleted topics included. */
    public record UserActivityDetail(
        String userId,
        List<TopicActivity> topics,
        DeletedTopicsActivity deletedTopics,
        SessionCounts tests,
        SessionCounts interviews
    ) {}
}
