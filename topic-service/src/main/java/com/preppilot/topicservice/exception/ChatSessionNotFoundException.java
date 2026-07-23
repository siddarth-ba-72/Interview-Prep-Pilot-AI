package com.preppilot.topicservice.exception;

import org.springframework.http.HttpStatus;

public class ChatSessionNotFoundException extends ApiException {
    public ChatSessionNotFoundException(String topicId) {
        super(HttpStatus.NOT_FOUND, "CHAT_SESSION_NOT_FOUND",
                "No chat session found for topic: " + topicId + ". Open Learn Mode first.");
    }
}
