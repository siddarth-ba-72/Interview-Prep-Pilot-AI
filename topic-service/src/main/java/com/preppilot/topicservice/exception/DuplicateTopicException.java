package com.preppilot.topicservice.exception;

import org.springframework.http.HttpStatus;

public class DuplicateTopicException extends ApiException {
    public DuplicateTopicException(String name) {
        super(HttpStatus.CONFLICT, "DUPLICATE_TOPIC", "Topic already exists: " + name);
    }
}
