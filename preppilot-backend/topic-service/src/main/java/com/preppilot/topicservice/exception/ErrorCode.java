package com.preppilot.topicservice.exception;

import org.springframework.http.HttpStatus;

public enum ErrorCode {
    // User errors (4xx) - Client-side errors
    USER_INVALID_INPUT(HttpStatus.BAD_REQUEST, "Invalid input provided"),
    USER_INVALID_TOPIC(HttpStatus.BAD_REQUEST, "Invalid topic provided"),
    USER_INVALID_CONFIG(HttpStatus.BAD_REQUEST, "Invalid configuration"),
    USER_UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "Unauthorized access"),

    // Not found (404)
    TOPIC_NOT_FOUND(HttpStatus.NOT_FOUND, "Topic not found"),
    CHAT_SESSION_NOT_FOUND(HttpStatus.NOT_FOUND, "Chat session not found"),
    MOCK_INTERVIEW_NOT_FOUND(HttpStatus.NOT_FOUND, "Mock interview not found"),

    // AI Service errors (400/502)
    AI_SERVICE_ERROR(HttpStatus.BAD_GATEWAY, "AI service error"),
    AI_INVALID_REQUEST(HttpStatus.BAD_REQUEST, "Invalid request for AI service"),
    AI_SERVICE_UNAVAILABLE(HttpStatus.BAD_GATEWAY, "AI service temporarily unavailable"),

    // System/Server errors (5xx)
    SYSTEM_INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error"),
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
