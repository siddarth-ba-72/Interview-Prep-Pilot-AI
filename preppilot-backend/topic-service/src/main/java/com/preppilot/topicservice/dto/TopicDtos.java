package com.preppilot.topicservice.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.time.Instant;

public class TopicDtos {

    public record CreateTopicRequest(
        @NotBlank(message = "Topic name is required")
        @Size(max = 100, message = "Topic name must be at most 100 characters")
        String name
    ) {}

    public record TopicResponse(
        String id,
        String name,
        Instant createdAt,
        Integer testCount,
        Double avgScore
    ) {}
}
