package com.preppilot.topicservice.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

/**
 * One user's recent uses of one {@link UsageAction}, keyed {@code <userId>:<action>}.
 * Written only by {@code UsageLimitService} through atomic pipeline updates; this class is
 * for reading it back and for creating the TTL index.
 */
@Document(collection = "usage_windows")
public class UsageWindow {

    @Id
    private String id;

    private String userId;

    private String action;

    /** Uses still inside the window, oldest first. */
    private List<Event> events;

    /** Set when a use fills the window: no more uses until this time. */
    private Instant lockedUntil;

    /** Id of the event that set {@link #lockedUntil}, so refunding that event lifts the lock. */
    private String lockedBy;

    /** MongoDB deletes the document once nothing in it can matter any more. (Not
     * expireAfter = "0s": Spring Data skips a zero duration and creates a plain index.) */
    @Indexed(expireAfterSeconds = 0)
    private Instant expireAt;

    /** Not named {@code id}: Spring Data would map that to {@code _id} inside the array. */
    public record Event(String eventId, Instant at) {}

    public UsageWindow() {}

    public String getId() { return id; }
    public String getUserId() { return userId; }
    public String getAction() { return action; }
    public List<Event> getEvents() { return events != null ? events : List.of(); }
    public Instant getLockedUntil() { return lockedUntil; }
    public String getLockedBy() { return lockedBy; }
    public Instant getExpireAt() { return expireAt; }
}
