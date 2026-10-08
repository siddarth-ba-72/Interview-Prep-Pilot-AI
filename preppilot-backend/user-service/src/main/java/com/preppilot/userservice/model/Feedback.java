package com.preppilot.userservice.model;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

/** A message a user sent from the "Feedback" button. Only admins can read it. */
@Document(collection = "feedback")
public class Feedback {

    @Id
    private String id;

    @Indexed
    private String userId;

    // Copied from the user at the time of sending, so admins see who sent it without a lookup
    private String email;

    private String displayName;

    private String message;

    @CreatedDate
    @Indexed
    private Instant createdAt;

    public Feedback() {}

    public Feedback(String userId, String email, String displayName, String message) {
        this.userId = userId;
        this.email = email;
        this.displayName = displayName;
        this.message = message;
    }

    public String getId() { return id; }
    public String getUserId() { return userId; }
    public String getEmail() { return email; }
    public String getDisplayName() { return displayName; }
    public String getMessage() { return message; }
    public Instant getCreatedAt() { return createdAt; }
}
