package com.preppilot.topicservice.service;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.preppilot.topicservice.dto.AdminDtos.ActivitySummary;
import com.preppilot.topicservice.dto.AdminDtos.DeletedTopicsActivity;
import com.preppilot.topicservice.dto.AdminDtos.SessionCounts;
import com.preppilot.topicservice.dto.AdminDtos.TopicActivity;
import com.preppilot.topicservice.dto.AdminDtos.UserActivity;
import com.preppilot.topicservice.dto.AdminDtos.UserActivityDetail;
import com.preppilot.topicservice.exception.ApiException;
import com.preppilot.topicservice.repository.TopicRepository;
import org.bson.Document;
import org.bson.types.ObjectId;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.repository.support.MongoRepositoryFactory;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/**
 * Runs the admin activity counts against MongoDB. Skipped unless TEST_MONGODB_URI is set, e.g.
 * <pre>
 * docker run -d --rm --name preppilot-test-mongo -p 27018:27017 mongo:7.0
 * TEST_MONGODB_URI=mongodb://localhost:27018 ./gradlew :topic-service:test
 * </pre>
 */
class AdminActivityServiceIntegrationTest {

    private static final String MONGODB_URI = System.getenv("TEST_MONGODB_URI");
    private static final Instant NOW = Instant.parse("2026-10-08T12:00:00Z");

    private static MongoClient client;

    private MongoTemplate mongoTemplate;
    private AdminActivityService service;

    @BeforeAll
    static void connect() {
        assumeTrue(MONGODB_URI != null && !MONGODB_URI.isBlank(), "TEST_MONGODB_URI is not set");
        client = MongoClients.create(MONGODB_URI);
    }

    @AfterAll
    static void disconnect() {
        if (client != null) {
            client.close();
        }
    }

    @BeforeEach
    void setUp() {
        mongoTemplate = new MongoTemplate(client, "admin_activity_test");
        for (String collection : List.of("topics", "test_sessions", "mock_interview_sessions")) {
            mongoTemplate.dropCollection(collection);
        }
        TopicRepository topicRepository = new MongoRepositoryFactory(mongoTemplate).getRepository(TopicRepository.class);
        service = new AdminActivityService(mongoTemplate, topicRepository, Clock.fixed(NOW, ZoneOffset.UTC));
    }

    @Test
    void countsActiveAndCompletedSessionsPerTopic() {
        String java = insertTopic("ann", "Java", "2026-10-01T09:00:00Z");
        String sql = insertTopic("ann", "SQL", "2026-10-02T09:00:00Z");
        insertTest("ann", java, "COMPLETED");
        insertTest("ann", java, "COMPLETED");
        insertTest("ann", java, "IN_PROGRESS");
        insertInterview("ann", sql, "COMPLETED", null);
        insertInterview("ann", sql, "IN_PROGRESS", NOW.plusSeconds(600));

        UserActivityDetail detail = service.userActivity("ann");

        assertEquals(List.of(
                new TopicActivity("SQL", SessionCounts.NONE, new SessionCounts(1, 1)),
                new TopicActivity("Java", new SessionCounts(1, 2), SessionCounts.NONE)), detail.topics());
        assertEquals(new SessionCounts(1, 2), detail.tests());
        assertEquals(new SessionCounts(1, 1), detail.interviews());
        assertNull(detail.deletedTopics());
    }

    @Test
    void anInterviewPastItsDeadlineIsNoLongerActive() {
        String java = insertTopic("ann", "Java", "2026-10-01T09:00:00Z");
        insertInterview("ann", java, "IN_PROGRESS", NOW.minusSeconds(1));
        insertInterview("ann", java, "IN_PROGRESS", null);

        assertEquals(new SessionCounts(1, 1), service.userActivity("ann").interviews());
    }

    @Test
    void sessionsOfDeletedTopicsStillCount() {
        String java = insertTopic("ann", "Java", "2026-10-01T09:00:00Z");
        String deleted = new ObjectId().toHexString();
        insertTest("ann", java, "COMPLETED");
        insertTest("ann", deleted, "COMPLETED");
        insertInterview("ann", deleted, "COMPLETED", null);

        UserActivityDetail detail = service.userActivity("ann");

        assertEquals(new DeletedTopicsActivity(new SessionCounts(0, 1), new SessionCounts(0, 1)), detail.deletedTopics());
        assertEquals(new SessionCounts(0, 2), detail.tests());
    }

    @Test
    void countsPerUserInTheOrderAsked() {
        String annJava = insertTopic("ann", "Java", "2026-10-01T09:00:00Z");
        insertTopic("ann", "SQL", "2026-10-02T09:00:00Z");
        String bobGo = insertTopic("bob", "Go", "2026-10-03T09:00:00Z");
        insertTest("ann", annJava, "COMPLETED");
        insertTest("bob", bobGo, "IN_PROGRESS");
        insertInterview("bob", bobGo, "COMPLETED", null);

        List<UserActivity> activity = service.usersActivity(List.of("bob", "nobody", "ann", "bob"));

        assertEquals(List.of(
                new UserActivity("bob", 1, new SessionCounts(1, 0), new SessionCounts(0, 1)),
                new UserActivity("nobody", 0, SessionCounts.NONE, SessionCounts.NONE),
                new UserActivity("ann", 2, new SessionCounts(0, 1), SessionCounts.NONE)), activity);
    }

    @Test
    void refusesTooManyUserIdsAtOnce() {
        List<String> ids = new ArrayList<>();
        for (int i = 0; i <= AdminActivityService.MAX_USER_IDS; i++) {
            ids.add("user-" + i);
        }
        assertThrows(ApiException.class, () -> service.usersActivity(ids));
        assertEquals(List.of(), service.usersActivity(Collections.emptyList()));
    }

    @Test
    void summarisesEveryone() {
        String annJava = insertTopic("ann", "Java", "2026-10-01T09:00:00Z");
        String bobGo = insertTopic("bob", "Go", "2026-10-03T09:00:00Z");
        insertTest("ann", annJava, "COMPLETED");
        insertTest("bob", bobGo, "IN_PROGRESS");
        insertInterview("ann", annJava, "IN_PROGRESS", NOW.plusSeconds(60));
        insertInterview("bob", bobGo, "IN_PROGRESS", NOW.minusSeconds(60));

        ActivitySummary summary = service.summary();

        assertEquals(new ActivitySummary(2, new SessionCounts(1, 1), new SessionCounts(1, 1)), summary);
    }

    @Test
    void anEmptyDatabaseHasNoActivity() {
        assertEquals(new ActivitySummary(0, SessionCounts.NONE, SessionCounts.NONE), service.summary());
    }

    private String insertTopic(String userId, String name, String createdAt) {
        ObjectId id = new ObjectId();
        mongoTemplate.getCollection("topics").insertOne(new Document("_id", id)
                .append("userId", userId)
                .append("name", name)
                .append("createdAt", Date.from(Instant.parse(createdAt))));
        return id.toHexString();
    }

    private void insertTest(String userId, String topicId, String status) {
        mongoTemplate.getCollection("test_sessions").insertOne(new Document("userId", userId)
                .append("topicId", topicId)
                .append("status", status));
    }

    private void insertInterview(String userId, String topicId, String status, Instant deadlineAt) {
        Document session = new Document("userId", userId)
                .append("topicId", topicId)
                .append("status", status);
        if (deadlineAt != null) {
            session.append("deadlineAt", Date.from(deadlineAt));
        }
        mongoTemplate.getCollection("mock_interview_sessions").insertOne(session);
    }
}
