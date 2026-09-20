package com.preppilot.topicservice.exception;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class ErrorCodeTest {

    @Test
    void testAllErrorCodesExist() {
        assertNotNull(ErrorCode.USER_INVALID_INPUT);
        assertNotNull(ErrorCode.USER_INVALID_TOPIC);
        assertNotNull(ErrorCode.USER_INVALID_CONFIG);
        assertNotNull(ErrorCode.USER_UNAUTHORIZED);
        assertNotNull(ErrorCode.TOPIC_NOT_FOUND);
        assertNotNull(ErrorCode.AI_INVALID_REQUEST);
        assertNotNull(ErrorCode.AI_SERVICE_ERROR);
        assertNotNull(ErrorCode.SYSTEM_INTERNAL_ERROR);
        assertNotNull(ErrorCode.STREAMING_ERROR);
    }

    @Test
    void testUserErrorCodesReturn400() {
        assertEquals(HttpStatus.BAD_REQUEST, ErrorCode.USER_INVALID_INPUT.getStatus());
        assertEquals(HttpStatus.BAD_REQUEST, ErrorCode.USER_INVALID_TOPIC.getStatus());
        assertEquals(HttpStatus.BAD_REQUEST, ErrorCode.USER_INVALID_CONFIG.getStatus());
    }

    @Test
    void testUnauthorizedReturns401() {
        assertEquals(HttpStatus.UNAUTHORIZED, ErrorCode.USER_UNAUTHORIZED.getStatus());
    }

    @Test
    void testNotFoundReturns404() {
        assertEquals(HttpStatus.NOT_FOUND, ErrorCode.TOPIC_NOT_FOUND.getStatus());
    }

    @Test
    void testAiInvalidReturns400() {
        assertEquals(HttpStatus.BAD_REQUEST, ErrorCode.AI_INVALID_REQUEST.getStatus());
    }

    @Test
    void testAiServiceErrorReturns502() {
        assertEquals(HttpStatus.BAD_GATEWAY, ErrorCode.AI_SERVICE_ERROR.getStatus());
    }

    @Test
    void testSystemErrorReturns500() {
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, ErrorCode.SYSTEM_INTERNAL_ERROR.getStatus());
    }

    @Test
    void testErrorCodeGetCodeReturnsEnumName() {
        assertEquals("USER_INVALID_INPUT", ErrorCode.USER_INVALID_INPUT.getCode());
        assertEquals("USER_INVALID_TOPIC", ErrorCode.USER_INVALID_TOPIC.getCode());
        assertEquals("AI_SERVICE_ERROR", ErrorCode.AI_SERVICE_ERROR.getCode());
    }

    @Test
    void testErrorCodeGetMessageReturnsDescription() {
        assertNotNull(ErrorCode.USER_INVALID_INPUT.getMessage());
        assertNotNull(ErrorCode.AI_SERVICE_ERROR.getMessage());
        assertNotNull(ErrorCode.SYSTEM_INTERNAL_ERROR.getMessage());
    }

    @Test
    void testAllErrorCodesHaveStatus() {
        for (ErrorCode code : ErrorCode.values()) {
            assertNotNull(code.getStatus(), "ErrorCode " + code + " should have status");
            boolean is4xx = code.getStatus().is4xxClientError();
            boolean is5xx = code.getStatus().is5xxServerError();
            org.junit.jupiter.api.Assertions.assertTrue(is4xx || is5xx,
                    "ErrorCode " + code + " should be 4xx or 5xx");
        }
    }

    @Test
    void testErrorCodeEnumConsistency() {
        assertEquals("USER_INVALID_INPUT", ErrorCode.USER_INVALID_INPUT.getCode());
        assertEquals("USER_INVALID_TOPIC", ErrorCode.USER_INVALID_TOPIC.getCode());
        assertEquals("USER_INVALID_CONFIG", ErrorCode.USER_INVALID_CONFIG.getCode());
        assertEquals("USER_UNAUTHORIZED", ErrorCode.USER_UNAUTHORIZED.getCode());
        assertEquals("TOPIC_NOT_FOUND", ErrorCode.TOPIC_NOT_FOUND.getCode());
        assertEquals("CHAT_SESSION_NOT_FOUND", ErrorCode.CHAT_SESSION_NOT_FOUND.getCode());
        assertEquals("MOCK_INTERVIEW_NOT_FOUND", ErrorCode.MOCK_INTERVIEW_NOT_FOUND.getCode());
        assertEquals("AI_INVALID_REQUEST", ErrorCode.AI_INVALID_REQUEST.getCode());
        assertEquals("AI_SERVICE_ERROR", ErrorCode.AI_SERVICE_ERROR.getCode());
        assertEquals("AI_SERVICE_UNAVAILABLE", ErrorCode.AI_SERVICE_UNAVAILABLE.getCode());
        assertEquals("SYSTEM_INTERNAL_ERROR", ErrorCode.SYSTEM_INTERNAL_ERROR.getCode());
        assertEquals("STREAMING_ERROR", ErrorCode.STREAMING_ERROR.getCode());
    }

    @Test
    void testUserErrorsAre4xx() {
        for (ErrorCode code : ErrorCode.values()) {
            if (code.getCode().startsWith("USER_")) {
                org.junit.jupiter.api.Assertions.assertTrue(code.getStatus().is4xxClientError(),
                        code + " should be 4xx");
            }
        }
    }

    @Test
    void testSystemErrorsAre5xx() {
        for (ErrorCode code : ErrorCode.values()) {
            if (code.getCode().startsWith("SYSTEM_") || code.getCode().equals("STREAMING_ERROR")) {
                org.junit.jupiter.api.Assertions.assertTrue(code.getStatus().is5xxServerError(),
                        code + " should be 5xx");
            }
        }
    }
}
