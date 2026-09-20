package com.preppilot.topicservice.exception;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class ApiExceptionUnitTest {

    @Test
    void testApiExceptionWithErrorCode() {
        ApiException ex = new ApiException(
                ErrorCode.USER_INVALID_TOPIC,
                "Topic 'Rust' is out of scope"
        );

        assertEquals("USER_INVALID_TOPIC", ex.getCode());
        assertEquals("Topic 'Rust' is out of scope", ex.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, ex.getStatus());
    }

    @Test
    void testApiExceptionWithDefaultMessage() {
        ApiException ex = new ApiException(ErrorCode.USER_INVALID_TOPIC);

        assertEquals("USER_INVALID_TOPIC", ex.getCode());
        assertEquals("Invalid topic provided", ex.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, ex.getStatus());
    }

    @Test
    void testApiExceptionWithStringCode() {
        ApiException ex = new ApiException(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "CUSTOM_ERROR",
                "Custom error message"
        );

        assertEquals("CUSTOM_ERROR", ex.getCode());
        assertEquals("Custom error message", ex.getMessage());
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, ex.getStatus());
    }

    @Test
    void testApiExceptionIsRuntimeException() {
        ApiException ex = new ApiException(
                ErrorCode.USER_INVALID_TOPIC,
                "Test"
        );

        org.junit.jupiter.api.Assertions.assertTrue(ex instanceof RuntimeException);
    }

    @Test
    void testApiExceptionCanBeCaught() {
        try {
            throw new ApiException(ErrorCode.TOPIC_NOT_FOUND, "Not found");
        } catch (ApiException ex) {
            assertEquals("TOPIC_NOT_FOUND", ex.getCode());
            assertEquals(HttpStatus.NOT_FOUND, ex.getStatus());
        }
    }

    @Test
    void testApiExceptionCanBeCaughtAsRuntimeException() {
        try {
            throw new ApiException(ErrorCode.AI_SERVICE_ERROR, "AI error");
        } catch (RuntimeException ex) {
            org.junit.jupiter.api.Assertions.assertTrue(ex instanceof ApiException);
        }
    }

    @Test
    void testAllErrorCodesWithApiException() {
        for (ErrorCode code : ErrorCode.values()) {
            ApiException ex = new ApiException(code, "Test message");
            assertEquals(code.getCode(), ex.getCode());
            assertEquals(code.getStatus(), ex.getStatus());
        }
    }

    @Test
    void testApiExceptionWithSpecialCharacters() {
        String msgWithChars = "Topic has @#$%^&*() characters";
        ApiException ex = new ApiException(
                ErrorCode.USER_INVALID_TOPIC,
                msgWithChars
        );

        assertEquals(msgWithChars, ex.getMessage());
    }

    @Test
    void testApiExceptionCodeNotNull() {
        ApiException ex = new ApiException(ErrorCode.USER_INVALID_TOPIC);
        assertNotNull(ex.getCode());
    }

    @Test
    void testApiExceptionStatusNotNull() {
        ApiException ex = new ApiException(ErrorCode.USER_INVALID_TOPIC);
        assertNotNull(ex.getStatus());
    }

    @Test
    void testApiExceptionMessageNotNull() {
        ApiException ex = new ApiException(ErrorCode.USER_INVALID_TOPIC);
        assertNotNull(ex.getMessage());
    }

    @Test
    void testApiExceptionWith4xxErrorCode() {
        ApiException ex1 = new ApiException(ErrorCode.USER_INVALID_INPUT, "Invalid");
        org.junit.jupiter.api.Assertions.assertTrue(ex1.getStatus().is4xxClientError());

        ApiException ex2 = new ApiException(ErrorCode.AI_INVALID_REQUEST, "Invalid");
        org.junit.jupiter.api.Assertions.assertTrue(ex2.getStatus().is4xxClientError());
    }

    @Test
    void testApiExceptionWith5xxErrorCode() {
        ApiException ex1 = new ApiException(ErrorCode.SYSTEM_INTERNAL_ERROR, "Error");
        org.junit.jupiter.api.Assertions.assertTrue(ex1.getStatus().is5xxServerError());

        ApiException ex2 = new ApiException(ErrorCode.AI_SERVICE_ERROR, "Error");
        org.junit.jupiter.api.Assertions.assertTrue(ex2.getStatus().is5xxServerError());
    }

    @Test
    void testMultipleApiExceptionInstances() {
        ApiException ex1 = new ApiException(ErrorCode.USER_INVALID_TOPIC, "Msg 1");
        ApiException ex2 = new ApiException(ErrorCode.SYSTEM_INTERNAL_ERROR, "Msg 2");
        ApiException ex3 = new ApiException(ErrorCode.AI_SERVICE_ERROR, "Msg 3");

        assertEquals("USER_INVALID_TOPIC", ex1.getCode());
        assertEquals("SYSTEM_INTERNAL_ERROR", ex2.getCode());
        assertEquals("AI_SERVICE_ERROR", ex3.getCode());
    }

    @Test
    void testApiExceptionStackTraceAvailable() {
        ApiException ex = new ApiException(ErrorCode.USER_INVALID_TOPIC, "Test");
        StackTraceElement[] trace = ex.getStackTrace();
        org.junit.jupiter.api.Assertions.assertTrue(trace.length > 0);
    }

    @Test
    void testApiExceptionWithCustomHttpStatus() {
        ApiException ex = new ApiException(
                HttpStatus.BAD_REQUEST,
                "CUSTOM",
                "Custom message"
        );

        assertEquals(400, ex.getStatus().value());
    }
}
