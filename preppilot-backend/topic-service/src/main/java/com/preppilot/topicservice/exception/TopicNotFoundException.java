package com.preppilot.topicservice.exception;

import org.springframework.http.HttpStatus;

public class TopicNotFoundException extends ApiException {
    public TopicNotFoundException(String topicId) {
        super(HttpStatus.NOT_FOUND, "TOPIC_NOT_FOUND", "Topic not found: " + topicId);
    }
}
