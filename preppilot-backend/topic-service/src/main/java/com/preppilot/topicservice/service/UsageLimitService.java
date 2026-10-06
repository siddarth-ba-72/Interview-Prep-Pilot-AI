package com.preppilot.topicservice.service;

import com.mongodb.client.MongoCollection;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.FindOneAndUpdateOptions;
import com.mongodb.client.model.ReturnDocument;
import com.preppilot.topicservice.config.UsageLimitProperties;
import com.preppilot.topicservice.config.UsageLimitProperties.Tier;
import com.preppilot.topicservice.dto.UsageDtos.ActionUsage;
import com.preppilot.topicservice.dto.UsageDtos.TopicUsage;
import com.preppilot.topicservice.dto.UsageDtos.UsageResponse;
import com.preppilot.topicservice.exception.ApiException;
import com.preppilot.topicservice.exception.ErrorCode;
import com.preppilot.topicservice.exception.UsageLimitExceededException;
import com.preppilot.topicservice.model.UsageAction;
import com.preppilot.topicservice.model.UsageWindow;
import com.preppilot.topicservice.repository.TopicRepository;
import com.preppilot.topicservice.util.StructuredLogger;
import org.bson.Document;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Per-user limits on AI-backed actions, so one user cannot use up the shared AI budget.
 *
 * Each action is counted over a sliding window (24h by default). The use that reaches the
 * limit locks the action until one full window after that use, so a user who has used up
 * their limit waits a full window from their last use rather than getting slots back one
 * at a time as old uses expire.
 *
 * State lives in the {@code usage_windows} collection, one document per user and action.
 * Every check-and-record is a single atomic update, so two requests racing for the last
 * slot cannot both get it.
 */
@Service
public class UsageLimitService {

    private static final StructuredLogger log = new StructuredLogger(UsageLimitService.class);
    static final String STUDENT_LEVEL = "STUDENT";
    private static final String COLLECTION = "usage_windows";
    private static final Date NEVER = new Date(0);

    private final MongoTemplate mongoTemplate;
    private final TopicRepository topicRepository;
    private final UsageLimitProperties properties;
    private final Clock clock;

    @Autowired
    public UsageLimitService(MongoTemplate mongoTemplate, TopicRepository topicRepository,
                             UsageLimitProperties properties) {
        this(mongoTemplate, topicRepository, properties, Clock.systemUTC());
    }

    UsageLimitService(MongoTemplate mongoTemplate, TopicRepository topicRepository,
                      UsageLimitProperties properties, Clock clock) {
        this.mongoTemplate = mongoTemplate;
        this.topicRepository = topicRepository;
        this.properties = properties;
        this.clock = clock;
    }

    /** {@code experienceLevel} is the user's onboarding answer from the X-User-Experience header. */
    public Tier tierFor(String experienceLevel) {
        return STUDENT_LEVEL.equals(experienceLevel) ? properties.student() : properties.standard();
    }

    public void checkCanCreateTopic(String userId, String experienceLevel) {
        Integer maxTopics = tierFor(experienceLevel).maxTopics();
        if (maxTopics != null && topicRepository.countByUserId(userId) >= maxTopics) {
            throw new ApiException(ErrorCode.TOPIC_LIMIT_REACHED,
                    "You can have up to " + maxTopics + " topics. Delete a topic to add a new one.");
        }
    }

    /**
     * Records one use of {@code action}, or throws {@link UsageLimitExceededException} if the
     * user may not use it right now. Returns the use's id for {@link #refund}.
     */
    public String consume(String userId, String experienceLevel, UsageAction action) {
        int limit = action.limitIn(tierFor(experienceLevel));
        Instant now = clock.instant();
        String eventId = UUID.randomUUID().toString();

        Document updated = collection().findOneAndUpdate(
                Filters.eq("_id", windowId(userId, action)),
                consumePipeline(userId, action, eventId, limit, now),
                new FindOneAndUpdateOptions().upsert(true).returnDocument(ReturnDocument.AFTER));
        UsageWindow window = mongoTemplate.getConverter().read(UsageWindow.class, updated);

        boolean recorded = window.getEvents().stream().anyMatch(e -> eventId.equals(e.eventId()));
        if (!recorded) {
            throw new UsageLimitExceededException(
                    "You've reached your limit of " + action.describe(limit)
                            + " per " + window().toHours() + " hours.",
                    retryAt(window, limit, now));
        }
        return eventId;
    }

    /**
     * Gives back a use whose AI work failed, so users are not charged for our errors. If that
     * use had locked the action, the lock goes with it. Never throws: a failed refund must not
     * hide the error that caused it.
     */
    public void refund(String userId, UsageAction action, String eventId) {
        try {
            Document lockedByThisUse = new Document("$eq", List.of("$lockedBy", literal(eventId)));
            collection().updateOne(
                    Filters.eq("_id", windowId(userId, action)),
                    List.of(set(new Document("events", filter("$events",
                                    new Document("$ne", List.of("$$this.eventId", literal(eventId)))))
                            .append("lockedUntil", cond(lockedByThisUse, "$$REMOVE", "$lockedUntil"))
                            .append("lockedBy", cond(lockedByThisUse, "$$REMOVE", "$lockedBy")))));
        } catch (RuntimeException e) {
            log.warn(ErrorCode.SYSTEM_INTERNAL_ERROR.getCode(), "Could not refund a usage event",
                    Map.of("userId", userId, "action", action.name()));
        }
    }

    public UsageResponse getUsage(String userId, String experienceLevel) {
        Tier tier = tierFor(experienceLevel);
        Instant now = clock.instant();
        return new UsageResponse(
                STUDENT_LEVEL.equals(experienceLevel) ? "STUDENT" : "STANDARD",
                window().toHours(),
                new TopicUsage(topicRepository.countByUserId(userId), tier.maxTopics()),
                actionUsage(userId, UsageAction.LEARN_MESSAGE, tier, now),
                actionUsage(userId, UsageAction.TEST, tier, now),
                actionUsage(userId, UsageAction.MOCK_INTERVIEW, tier, now));
    }

    private ActionUsage actionUsage(String userId, UsageAction action, Tier tier, Instant now) {
        int limit = action.limitIn(tier);
        UsageWindow window = mongoTemplate.findById(windowId(userId, action), UsageWindow.class);
        if (window == null) {
            return new ActionUsage(0, limit, limit, null);
        }
        int used = recentUses(window, now).size();
        Instant availableAt = retryAt(window, limit, now);
        int remaining = availableAt != null ? 0 : Math.max(0, limit - used);
        return new ActionUsage(used, limit, remaining, availableAt);
    }

    /** When the user may use the action again, or null if they may use it now. */
    private Instant retryAt(UsageWindow window, int limit, Instant now) {
        if (window.getLockedUntil() != null && window.getLockedUntil().isAfter(now)) {
            return window.getLockedUntil();
        }
        List<Instant> recent = recentUses(window, now);
        if (recent.isEmpty() || recent.size() < limit) {
            return null;
        }
        // Full but not locked: only happens when the limit dropped under the user (a config
        // change, or a profile switch to the student tier). A slot frees up once enough of
        // these uses leave the window.
        return recent.get(recent.size() - limit).plus(window());
    }

    private List<Instant> recentUses(UsageWindow window, Instant now) {
        Instant cutoff = now.minus(window());
        return window.getEvents().stream()
                .map(UsageWindow.Event::at)
                .filter(at -> at.isAfter(cutoff))
                .sorted()
                .toList();
    }

    /**
     * Mirrors {@link #retryAt}: a use is recorded only if the action is not locked and fewer
     * than {@code limit} uses are inside the window; the use that fills the window sets the lock.
     */
    private List<Document> consumePipeline(String userId, UsageAction action, String eventId, int limit, Instant now) {
        Date nowDate = Date.from(now);
        Date cutoff = Date.from(now.minus(window()));
        Date windowEnd = Date.from(now.plus(window()));
        Document size = new Document("$size", "$events");
        Document newEvent = new Document("eventId", eventId).append("at", nowDate);

        return List.of(
                // Forget uses that have slid out of the window
                set(new Document("userId", literal(userId))
                        .append("action", literal(action.name()))
                        .append("events", filter("$events", new Document("$gt", List.of("$$this.at", cutoff))))),
                set(new Document("allowed", new Document("$and", List.of(
                        new Document("$lte", List.of(new Document("$ifNull", List.of("$lockedUntil", NEVER)), nowDate)),
                        new Document("$lt", List.of(size, limit)))))),
                set(new Document("events", cond("$allowed",
                        new Document("$concatArrays", List.of("$events", literal(List.of(newEvent)))),
                        "$events"))),
                set(new Document("filled", new Document("$and", List.of("$allowed",
                        new Document("$gte", List.of(size, limit)))))),
                set(new Document("lockedUntil", cond("$filled", windowEnd, "$lockedUntil"))
                        .append("lockedBy", cond("$filled", literal(eventId), "$lockedBy"))
                        .append("expireAt", cond("$allowed", windowEnd,
                                new Document("$ifNull", List.of("$expireAt", windowEnd))))),
                new Document("$unset", List.of("allowed", "filled")));
    }

    private Duration window() {
        return properties.window();
    }

    private MongoCollection<Document> collection() {
        return mongoTemplate.getCollection(COLLECTION);
    }

    private static String windowId(String userId, UsageAction action) {
        return userId + ":" + action.name();
    }

    private static Document set(Document fields) {
        return new Document("$set", fields);
    }

    /** Keeps user-supplied strings from being read as field paths or operators. */
    private static Document literal(Object value) {
        return new Document("$literal", value);
    }

    private static Document cond(Object condition, Object then, Object otherwise) {
        return new Document("$cond", Arrays.asList(condition, then, otherwise));
    }

    private static Document filter(String arrayField, Document condition) {
        return new Document("$filter", new Document("input", new Document("$ifNull", List.of(arrayField, List.of())))
                .append("cond", condition));
    }
}
