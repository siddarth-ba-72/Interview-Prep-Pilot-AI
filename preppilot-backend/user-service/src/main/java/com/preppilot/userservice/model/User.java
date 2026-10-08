package com.preppilot.userservice.model;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document(collection = "users")
public class User {

    @Id
    private String id;

    @Indexed(unique = true)
    private String email;

    private String passwordHash;

    private AuthProvider authProvider = AuthProvider.LOCAL;

    @Indexed(sparse = true, unique = true)
    private String googleId;

    private String displayName;

    // Onboarding questionnaire answers; both stay null until the user completes it
    private String preferredDomain;

    private ExperienceLevel experienceLevel;

    // Absent on almost every document: users are USER unless an admin was set by hand
    private Role role;

    @CreatedDate
    private Instant createdAt;

    @LastModifiedDate
    private Instant updatedAt;

    public User() {}

    public User(String email, String passwordHash, AuthProvider authProvider,
                String googleId, String displayName) {
        this.email = email;
        this.passwordHash = passwordHash;
        this.authProvider = authProvider;
        this.googleId = googleId;
        this.displayName = displayName;
    }

    public String getId() { return id; }
    public String getEmail() { return email; }
    public String getPasswordHash() { return passwordHash; }
    public AuthProvider getAuthProvider() { return authProvider; }
    public String getGoogleId() { return googleId; }
    public String getDisplayName() { return displayName; }
    public String getPreferredDomain() { return preferredDomain; }
    public ExperienceLevel getExperienceLevel() { return experienceLevel; }
    public boolean isOnboardingCompleted() { return experienceLevel != null; }
    public Role getRole() { return role != null ? role : Role.USER; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public void setGoogleId(String googleId) { this.googleId = googleId; }
    public void setPreferredDomain(String preferredDomain) { this.preferredDomain = preferredDomain; }
    public void setExperienceLevel(ExperienceLevel experienceLevel) { this.experienceLevel = experienceLevel; }
}
