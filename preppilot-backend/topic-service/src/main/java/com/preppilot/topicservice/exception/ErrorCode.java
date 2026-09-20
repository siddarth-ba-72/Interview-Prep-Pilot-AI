package com.preppilot.topicservice.exception;

import org.springframework.http.HttpStatus;

public enum ErrorCode {
    // Validation errors (400)
    VALIDATION_ERROR(HttpStatus.BAD_REQUEST, "Validation failed"),
    INVALID_TOPIC(HttpStatus.BAD_REQUEST, "Invalid topic provided"),
    OUT_OF_SCOPE_TOPIC(HttpStatus.BAD_REQUEST, "Topic is out of scope"),
    DUPLICATE_TOPIC(HttpStatus.BAD_REQUEST, "Topic already exists"),

    // Missing context (401)
    MISSING_USER_CONTEXT(HttpStatus.UNAUTHORIZED, "Missing required user context"),

    // Not found (404)
    TOPIC_NOT_FOUND(HttpStatus.NOT_FOUND, "Topic not found"),
    CHAT_SESSION_NOT_FOUND(HttpStatus.NOT_FOUND, "Chat session not found"),
    MOCK_INTERVIEW_NOT_FOUND(HttpStatus.NOT_FOUND, "Mock interview not found"),

    // AI Service errors (400/502)
    AI_SERVICE_ERROR(HttpStatus.BAD_GATEWAY, "AI service error"),
    AI_INVALID_REQUEST(HttpStatus.BAD_REQUEST, "Invalid request for AI service"),
    AI_SERVICE_UNAVAILABLE(HttpStatus.BAD_GATEWAY, "AI service temporarily unavailable"),

    // Internal server errors (500)
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error"),
    STREAMING_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "Error during streaming operation");

    private final HttpStatus status;
    private final String message;

    ErrorCode(HttpStatus status, String message) {
        this.status = status;
        this.message = message;
    }

    public HttpStatus getStatus() {
        return status;
    }

    public String getMessage() {
        return message;
    }

    public String getCode() {
        return this.name();
    }
}
