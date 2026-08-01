package com.preppilot.userservice.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document(collection = "refresh_tokens")
public class RefreshToken {

    @Id
    private String id;

    @Indexed
    private String userId;

    private String tokenHash;

    @Indexed(expireAfter = "0s")
    private Instant expiresAt;

    private Instant createdAt = Instant.now();

    public RefreshToken() {}

    public RefreshToken(String userId, String tokenHash, Instant expiresAt) {
        this.userId = userId;
        this.tokenHash = tokenHash;
        this.expiresAt = expiresAt;
    }

    public String getId() { return id; }
    public String getUserId() { return userId; }
    public String getTokenHash() { return tokenHash; }
    public Instant getExpiresAt() { return expiresAt; }
    public Instant getCreatedAt() { return createdAt; }
}
