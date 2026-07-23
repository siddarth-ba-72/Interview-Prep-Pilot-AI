package com.preppilot.topicservice.dto;

import jakarta.validation.constraints.NotBlank;

import java.time.Instant;
import java.util.List;

public class ChatDtos {

    public record MessageResponse(
        String role,
        String content,
        Instant timestamp
    ) {}

    public record ChatSessionResponse(
        String topicId,
        List<MessageResponse> messages
    ) {}

    public record SendMessageRequest(
        @NotBlank(message = "Message content is required")
        String content
    ) {}
}
