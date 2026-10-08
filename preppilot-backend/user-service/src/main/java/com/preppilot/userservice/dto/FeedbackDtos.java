package com.preppilot.userservice.dto;

import com.preppilot.userservice.model.Feedback;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.time.Instant;
import java.util.List;

public class FeedbackDtos {

    public static final int MAX_MESSAGE_LENGTH = 2000;

    public record SubmitFeedbackRequest(
        @NotBlank(message = "Feedback is required")
        @Size(max = MAX_MESSAGE_LENGTH, message = "Feedback must be at most 2000 characters")
        String message
    ) {}

    /** What the sender gets back: just enough to confirm it was saved. */
    public record FeedbackReceipt(String id, Instant createdAt) {}

    /** Admin view: who sent it and what. */
    public record AdminFeedback(
        String id,
        String userId,
        String email,
        String displayName,
        String message,
        Instant createdAt
    ) {
        public static AdminFeedback from(Feedback feedback) {
            return new AdminFeedback(feedback.getId(), feedback.getUserId(), feedback.getEmail(),
                    feedback.getDisplayName(), feedback.getMessage(), feedback.getCreatedAt());
        }
    }

    /** {@code total} counts all feedback, across all pages. */
    public record AdminFeedbackPage(List<AdminFeedback> feedback, int page, int size, long total) {}
}
