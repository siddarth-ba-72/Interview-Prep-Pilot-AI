package com.preppilot.userservice.dto;

import com.preppilot.userservice.model.AuthProvider;
import com.preppilot.userservice.model.ExperienceLevel;
import com.preppilot.userservice.model.Role;
import com.preppilot.userservice.model.User;

import java.time.Instant;
import java.util.List;

/** Read-only views for the admin dashboard. Never carries the password hash or Google id. */
public class AdminDtos {

    public record AdminUser(
        String id,
        String email,
        String displayName,
        AuthProvider authProvider,
        ExperienceLevel experienceLevel,
        String preferredDomain,
        Role role,
        Instant createdAt
    ) {
        public static AdminUser from(User user) {
            return new AdminUser(user.getId(), user.getEmail(), user.getDisplayName(), user.getAuthProvider(),
                    user.getExperienceLevel(), user.getPreferredDomain(), user.getRole(), user.getCreatedAt());
        }
    }

    /** {@code total} counts every user matching the search, across all pages. */
    public record AdminUserPage(List<AdminUser> users, int page, int size, long total) {}

    public record AdminUserStats(long totalUsers) {}
}
