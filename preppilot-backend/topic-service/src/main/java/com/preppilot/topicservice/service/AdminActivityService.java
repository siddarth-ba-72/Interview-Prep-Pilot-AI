package com.preppilot.topicservice.service;

import com.preppilot.topicservice.dto.AdminDtos.ActivitySummary;
import com.preppilot.topicservice.dto.AdminDtos.DeletedTopicsActivity;
import com.preppilot.topicservice.dto.AdminDtos.SessionCounts;
import com.preppilot.topicservice.dto.AdminDtos.TopicActivity;
import com.preppilot.topicservice.dto.AdminDtos.UserActivity;
import com.preppilot.topicservice.dto.AdminDtos.UserActivityDetail;
import com.preppilot.topicservice.exception.ApiException;
import com.preppilot.topicservice.exception.ErrorCode;
import com.preppilot.topicservice.model.Topic;
import com.preppilot.topicservice.repository.TopicRepository;
import org.bson.Document;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Activity counts for the admin dashboard: how many topics, tests and mock interviews each
 * user has. Admins see topic names and counts only, never scores, answers, reports or chats.
 */
@Service
public class AdminActivityService {

    static final int MAX_USER_IDS = 100;
    private static final String TOPICS = "topics";
    private static final String TEST_SESSIONS = "test_sessions";
    private static final String INTERVIEW_SESSIONS = "mock_interview_sessions";

    private final MongoTemplate mongoTemplate;
    private final TopicRepository topicRepository;
    private final Clock clock;

    @Autowired
    public AdminActivityService(MongoTemplate mongoTemplate, TopicRepository topicRepository) {
        this(mongoTemplate, topicRepository, Clock.systemUTC());
    }

    AdminActivityService(MongoTemplate mongoTemplate, TopicRepository topicRepository, Clock clock) {
        this.mongoTemplate = mongoTemplate;
        this.topicRepository = topicRepository;
        this.clock = clock;
    }

    public ActivitySummary summary() {
        Document everything = new Document();
        return new ActivitySummary(
                topicRepository.count(),
                total(countSessions(TEST_SESSIONS, everything, null)),
                total(countSessions(INTERVIEW_SESSIONS, everything, null)));
    }

    /** One entry per id, in the order given; users with no activity get zeros. */
    public List<UserActivity> usersActivity(List<String> userIds) {
        List<String> ids = userIds.stream().filter(id -> id != null && !id.isBlank()).distinct().toList();
        if (ids.size() > MAX_USER_IDS) {
            throw new ApiException(ErrorCode.USER_INVALID_INPUT, "At most " + MAX_USER_IDS + " user ids at a time");
        }
        if (ids.isEmpty()) {
            return List.of();
        }

        Document ofTheseUsers = new Document("userId", new Document("$in", ids));
        Map<String, Long> topics = countTopicsByUser(ofTheseUsers);
        Map<String, SessionCounts> tests = countSessions(TEST_SESSIONS, ofTheseUsers, "userId");
        Map<String, SessionCounts> interviews = countSessions(INTERVIEW_SESSIONS, ofTheseUsers, "userId");
        return ids.stream()
                .map(id -> new UserActivity(id, topics.getOrDefault(id, 0L),
                        tests.getOrDefault(id, SessionCounts.NONE), interviews.getOrDefault(id, SessionCounts.NONE)))
                .toList();
    }

    /**
     * The user's topics, newest first, with session counts per topic. Deleting a topic keeps its
     * tests and interviews, so those are reported together under {@code deletedTopics}.
     */
    public UserActivityDetail userActivity(String userId) {
        Document ofThisUser = new Document("userId", userId);
        Map<String, SessionCounts> testsByTopic = countSessions(TEST_SESSIONS, ofThisUser, "topicId");
        Map<String, SessionCounts> interviewsByTopic = countSessions(INTERVIEW_SESSIONS, ofThisUser, "topicId");

        List<Topic> topics = topicRepository.findByUserIdOrderByCreatedAtDesc(userId);
        List<TopicActivity> topicActivity = topics.stream()
                .map(topic -> new TopicActivity(topic.getName(),
                        testsByTopic.getOrDefault(topic.getId(), SessionCounts.NONE),
                        interviewsByTopic.getOrDefault(topic.getId(), SessionCounts.NONE)))
                .toList();

        Set<String> topicIds = topics.stream().map(Topic::getId).collect(Collectors.toSet());
        SessionCounts deletedTests = totalExcept(testsByTopic, topicIds);
        SessionCounts deletedInterviews = totalExcept(interviewsByTopic, topicIds);
        DeletedTopicsActivity deletedTopics = deletedTests.equals(SessionCounts.NONE) && deletedInterviews.equals(SessionCounts.NONE)
                ? null
                : new DeletedTopicsActivity(deletedTests, deletedInterviews);

        return new UserActivityDetail(userId, topicActivity, deletedTopics,
                total(testsByTopic), total(interviewsByTopic));
    }

    private Map<String, Long> countTopicsByUser(Document match) {
        List<Document> pipeline = List.of(
                new Document("$match", match),
                new Document("$group", new Document("_id", "$userId").append("count", new Document("$sum", 1))));
        Map<String, Long> counts = new HashMap<>();
        for (Document row : mongoTemplate.getCollection(TOPICS).aggregate(pipeline)) {
            counts.put(row.getString("_id"), ((Number) row.get("count")).longValue());
        }
        return counts;
    }

    /** Active and completed sessions per value of {@code groupField}, or one group if it is null. */
    private Map<String, SessionCounts> countSessions(String collection, Document match, String groupField) {
        Document isActive = new Document("$cond", List.of(activeCondition(collection), 1, 0));
        List<Document> pipeline = List.of(
                new Document("$match", match),
                new Document("$group", new Document("_id", groupField != null ? "$" + groupField : null)
                        .append("total", new Document("$sum", 1))
                        .append("active", new Document("$sum", isActive))));

        Map<String, SessionCounts> counts = new HashMap<>();
        for (Document row : mongoTemplate.getCollection(collection).aggregate(pipeline)) {
            long total = ((Number) row.get("total")).longValue();
            long active = ((Number) row.get("active")).longValue();
            counts.put(row.getString("_id"), new SessionCounts(active, total - active));
        }
        return counts;
    }

    /**
     * Sessions are IN_PROGRESS or COMPLETED. An interview past its deadline stays IN_PROGRESS
     * until the user comes back and it is closed as TIME_EXPIRED, so it is no longer active.
     */
    private Document activeCondition(String collection) {
        Document inProgress = new Document("$eq", List.of("$status", "IN_PROGRESS"));
        if (!INTERVIEW_SESSIONS.equals(collection)) {
            return inProgress;
        }
        // Arrays.asList: List.of rejects the null elements these expressions need
        Document noDeadline = new Document("$eq", Arrays.asList(new Document("$ifNull", Arrays.asList("$deadlineAt", null)), null));
        Document beforeDeadline = new Document("$gt", List.of("$deadlineAt", Date.from(clock.instant())));
        return new Document("$and", List.of(inProgress, new Document("$or", List.of(noDeadline, beforeDeadline))));
    }

    private static SessionCounts total(Map<String, SessionCounts> counts) {
        return counts.values().stream().reduce(SessionCounts.NONE, SessionCounts::plus);
    }

    private static SessionCounts totalExcept(Map<String, SessionCounts> countsByTopic, Set<String> topicIds) {
        return countsByTopic.entrySet().stream()
                .filter(entry -> !topicIds.contains(entry.getKey()))
                .map(Map.Entry::getValue)
                .reduce(SessionCounts.NONE, SessionCounts::plus);
    }
}
