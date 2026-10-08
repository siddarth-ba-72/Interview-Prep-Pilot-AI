package com.preppilot.userservice.service;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.preppilot.userservice.dto.FeedbackDtos.AdminFeedback;
import com.preppilot.userservice.dto.FeedbackDtos.AdminFeedbackPage;
import com.preppilot.userservice.model.AuthProvider;
import com.preppilot.userservice.model.User;
import com.preppilot.userservice.repository.FeedbackRepository;
import org.bson.Document;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.repository.support.MongoRepositoryFactory;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Instant;
import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assumptions.assumeTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Runs the feedback queries against MongoDB. Skipped unless TEST_MONGODB_URI is set, e.g.
 * <pre>
 * docker run -d --rm --name preppilot-test-mongo -p 27018:27017 mongo:7.0
 * TEST_MONGODB_URI=mongodb://localhost:27018 ./gradlew :user-service:test
 * </pre>
 */
class FeedbackServiceIntegrationTest {

    private static final String MONGODB_URI = System.getenv("TEST_MONGODB_URI");

    private static MongoClient client;

    private MongoTemplate mongoTemplate;
    private UserService userService;
    private FeedbackService service;

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
        mongoTemplate = new MongoTemplate(client, "feedback_test");
        mongoTemplate.dropCollection("feedback");
        FeedbackRepository repository = new MongoRepositoryFactory(mongoTemplate).getRepository(FeedbackRepository.class);
        userService = mock(UserService.class);
        service = new FeedbackService(repository, userService);
    }

    @Test
    void savesEachMessageWithTheSendersNameAndEmail() {
        when(userService.getUser("u1")).thenReturn(user("u1", "ann@example.com", "Ann Lee"));

        service.submit("u1", "  The timer is too short  ");
        service.submit("u1", "Second thought: dark mode is great");

        List<Document> saved = mongoTemplate.getCollection("feedback").find().into(new java.util.ArrayList<>());
        assertEquals(2, saved.size());
        assertEquals("u1", saved.get(0).getString("userId"));
        assertEquals("ann@example.com", saved.get(0).getString("email"));
        assertEquals("Ann Lee", saved.get(0).getString("displayName"));
        assertEquals("The timer is too short", saved.get(0).getString("message"));
    }

    @Test
    void listsNewestFeedbackFirstOnePageAtATime() {
        insertFeedback("u1", "first", "2026-10-01T09:00:00Z");
        insertFeedback("u2", "second", "2026-10-02T09:00:00Z");
        insertFeedback("u1", "third", "2026-10-03T09:00:00Z");

        AdminFeedbackPage first = service.list(0, 2);
        AdminFeedbackPage second = service.list(1, 2);

        assertEquals(List.of("third", "second"), messages(first));
        assertEquals(List.of("first"), messages(second));
        assertEquals(3, first.total());
        assertEquals("u1@example.com", first.feedback().get(0).email());
        assertEquals("Name u1", first.feedback().get(0).displayName());
    }

    @Test
    void pageSizeIsCapped() {
        assertEquals(FeedbackService.MAX_PAGE_SIZE, service.list(0, 10_000).size());
        assertEquals(1, service.list(-5, 0).size());
    }

    private void insertFeedback(String userId, String message, String createdAt) {
        mongoTemplate.getCollection("feedback").insertOne(new Document("userId", userId)
                .append("email", userId + "@example.com")
                .append("displayName", "Name " + userId)
                .append("message", message)
                .append("createdAt", Date.from(Instant.parse(createdAt))));
    }

    private static User user(String id, String email, String displayName) {
        User user = new User(email, "hash", AuthProvider.LOCAL, null, displayName);
        ReflectionTestUtils.setField(user, "id", id);
        return user;
    }

    private static List<String> messages(AdminFeedbackPage page) {
        return page.feedback().stream().map(AdminFeedback::message).toList();
    }
}
