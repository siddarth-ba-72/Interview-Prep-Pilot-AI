package com.preppilot.topicservice.exception;

import org.springframework.http.HttpStatus;

public class MockInterviewNotFoundException extends ApiException {
    public MockInterviewNotFoundException(String sessionId) {
        super(HttpStatus.NOT_FOUND, "MOCK_INTERVIEW_NOT_FOUND",
                "No mock interview session found with id: " + sessionId);
    }
}
