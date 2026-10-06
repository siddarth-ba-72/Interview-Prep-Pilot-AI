package com.preppilot.topicservice.service;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.preppilot.topicservice.config.UsageLimitProperties;
import com.preppilot.topicservice.config.UsageLimitProperties.Tier;
import com.preppilot.topicservice.dto.UsageDtos.ActionUsage;
import com.preppilot.topicservice.dto.UsageDtos.UsageResponse;
import com.preppilot.topicservice.exception.ApiException;
import com.preppilot.topicservice.exception.UsageLimitExceededException;
import com.preppilot.topicservice.model.UsageAction;
import com.preppilot.topicservice.repository.TopicRepository;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.mongodb.core.MongoTemplate;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assumptions.assumeTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Runs the real update pipelines against MongoDB. Skipped unless TEST_MONGODB_URI is set, e.g.
 * <pre>
 * docker run -d --rm --name preppilot-test-mongo -p 27018:27017 mongo:7.0
 * TEST_MONGODB_URI=mongodb://localhost:27018 ./gradlew :topic-service:test
 * </pre>
 */
class UsageLimitServiceIntegrationTest {

    private static final String MONGODB_URI = System.getenv("TEST_MONGODB_URI");
    private static final Tier STUDENT = new Tier(2, 30, 2, 1);
    private static final Tier STANDARD = new Tier(null, 50, 3, 2);
    private static final Instant MONDAY_9AM = Instant.parse("2026-10-05T09:00:00Z");

    private static MongoClient client;

    private MongoTemplate mongoTemplate;
    private TopicRepository topicRepository;
    private MutableClock clock;
    private UsageLimitService service;

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
        mongoTemplate = new MongoTemplate(client, "usage_limit_test");
        mongoTemplate.dropCollection("usage_windows");
        topicRepository = mock(TopicRepository.class);
        clock = new MutableClock(MONDAY_9AM);
        service = new UsageLimitService(mongoTemplate, topicRepository,
                new UsageLimitProperties(Duration.ofHours(24), STUDENT, STANDARD), clock);
    }

    @Test
    void usingUpTheLimitLocksTheActionUntilAFullWindowAfterTheLastUse() {
        service.consume("u1", "STUDENT", UsageAction.TEST);
        clock.set(at("2026-10-05T18:00:00Z"));
        service.consume("u1", "STUDENT", UsageAction.TEST);

        clock.set(at("2026-10-05T20:00:00Z"));
        UsageLimitExceededException ex = assertThrows(UsageLimitExceededException.class,
                () -> service.consume("u1", "STUDENT", UsageAction.TEST));
        assertEquals(at("2026-10-06T18:00:00Z"), ex.getRetryAt());

        // The 9:00 use has left the window, but the lock holds until 24h after the last use
        clock.set(at("2026-10-06T09:30:00Z"));
        assertThrows(UsageLimitExceededException.class, () -> service.consume("u1", "STUDENT", UsageAction.TEST));

        // Then the whole limit is back
        clock.set(at("2026-10-06T18:00:00Z"));
        service.consume("u1", "STUDENT", UsageAction.TEST);
        service.consume("u1", "STUDENT", UsageAction.TEST);
        assertThrows(UsageLimitExceededException.class, () -> service.consume("u1", "STUDENT", UsageAction.TEST));
    }

    @Test
    void usesBelowTheLimitSlideOutOfTheWindow() {
        service.consume("u1", null, UsageAction.TEST);
        service.consume("u1", null, UsageAction.TEST);
        assertEquals(1, service.getUsage("u1", null).tests().remaining());

        clock.set(MONDAY_9AM.plus(Duration.ofHours(24)).plusSeconds(1));
        ActionUsage tests = service.getUsage("u1", null).tests();
        assertEquals(0, tests.used());
        assertEquals(3, tests.remaining());
        assertNull(tests.availableAt());
    }

    @Test
    void refundingTheUseThatSetTheLockLiftsIt() {
        String usageId = service.consume("u1", "STUDENT", UsageAction.MOCK_INTERVIEW);
        assertThrows(UsageLimitExceededException.class,
                () -> service.consume("u1", "STUDENT", UsageAction.MOCK_INTERVIEW));

        service.refund("u1", UsageAction.MOCK_INTERVIEW, usageId);

        assertEquals(1, service.getUsage("u1", "STUDENT").mockInterviews().remaining());
        assertDoesNotThrow(() -> service.consume("u1", "STUDENT", UsageAction.MOCK_INTERVIEW));
    }

    @Test
    void concurrentRequestsCannotBothTakeTheLastSlot() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(10);
        try {
            List<Callable<Boolean>> attempts = new ArrayList<>();
            for (int i = 0; i < 10; i++) {
                attempts.add(() -> {
                    try {
                        service.consume("u1", "STUDENT", UsageAction.MOCK_INTERVIEW);
                        return true;
                    } catch (UsageLimitExceededException e) {
                        return false;
                    }
                });
            }
            int succeeded = 0;
            for (Future<Boolean> result : pool.invokeAll(attempts)) {
                if (result.get()) {
                    succeeded++;
                }
            }
            assertEquals(1, succeeded);
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    void limitsAreSeparatePerUserAndPerAction() {
        service.consume("u1", "STUDENT", UsageAction.MOCK_INTERVIEW);

        assertDoesNotThrow(() -> service.consume("u2", "STUDENT", UsageAction.MOCK_INTERVIEW));
        assertDoesNotThrow(() -> service.consume("u1", "STUDENT", UsageAction.TEST));
        assertDoesNotThrow(() -> service.consume("u1", "STUDENT", UsageAction.LEARN_MESSAGE));
    }

    @Test
    void usageReportsTheTierLimitsAndWhenALockLifts() {
        when(topicRepository.countByUserId("u1")).thenReturn(1L);
        service.consume("u1", "STUDENT", UsageAction.LEARN_MESSAGE);
        service.consume("u1", "STUDENT", UsageAction.MOCK_INTERVIEW);

        UsageResponse usage = service.getUsage("u1", "STUDENT");

        assertEquals("STUDENT", usage.tier());
        assertEquals(24, usage.windowHours());
        assertEquals(1, usage.topics().used());
        assertEquals(2, usage.topics().limit());
        assertEquals(new ActionUsage(1, 30, 29, null), usage.learnMessages());
        assertEquals(new ActionUsage(0, 2, 2, null), usage.tests());
        assertEquals(new ActionUsage(1, 1, 0, MONDAY_9AM.plus(Duration.ofHours(24))), usage.mockInterviews());

        UsageResponse standard = service.getUsage("u2", "YEARS_3_5");
        assertEquals("STANDARD", standard.tier());
        assertNull(standard.topics().limit());
        assertEquals(50, standard.learnMessages().limit());
        assertEquals(2, standard.mockInterviews().limit());
    }

    @Test
    void switchingToALowerTierBlocksUntilEnoughUsesLeaveTheWindow() {
        // 31 Learn messages, one a minute: under the standard limit of 50, so no lock is set
        for (int i = 0; i <= 30; i++) {
            clock.set(MONDAY_9AM.plus(Duration.ofMinutes(i)));
            service.consume("u1", "YEARS_0_3", UsageAction.LEARN_MESSAGE);
        }

        // As a student (limit 30) they are over; a slot opens when the 9:01 message leaves the window
        UsageLimitExceededException ex = assertThrows(UsageLimitExceededException.class,
                () -> service.consume("u1", "STUDENT", UsageAction.LEARN_MESSAGE));
        Instant retryAt = MONDAY_9AM.plus(Duration.ofMinutes(1)).plus(Duration.ofHours(24));
        assertEquals(retryAt, ex.getRetryAt());

        clock.set(retryAt.minusSeconds(1));
        assertThrows(UsageLimitExceededException.class, () -> service.consume("u1", "STUDENT", UsageAction.LEARN_MESSAGE));
        clock.set(retryAt);
        assertDoesNotThrow(() -> service.consume("u1", "STUDENT", UsageAction.LEARN_MESSAGE));
    }

    @Test
    void onlyStudentsHaveATopicLimit() {
        when(topicRepository.countByUserId("u1")).thenReturn(2L);

        ApiException ex = assertThrows(ApiException.class, () -> service.checkCanCreateTopic("u1", "STUDENT"));
        assertEquals("TOPIC_LIMIT_REACHED", ex.getCode());
        assertDoesNotThrow(() -> service.checkCanCreateTopic("u1", "YEARS_5_8"));
        assertDoesNotThrow(() -> service.checkCanCreateTopic("u1", null));
    }

    private static Instant at(String iso) {
        return Instant.parse(iso);
    }

    private static class MutableClock extends Clock {
        private volatile Instant now;

        MutableClock(Instant now) {
            this.now = now;
        }

        void set(Instant now) {
            this.now = now;
        }

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return now;
        }
    }
}
