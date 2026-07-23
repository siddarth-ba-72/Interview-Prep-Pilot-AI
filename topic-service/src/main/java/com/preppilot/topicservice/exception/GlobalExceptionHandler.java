package com.preppilot.topicservice.exception;

import com.preppilot.topicservice.service.AiStreamException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<Object> handleApiException(ApiException ex) {
        return ResponseEntity.status(ex.getStatus()).body(errorBody(ex.getCode(), ex.getMessage()));
    }

    @ExceptionHandler(AiStreamException.class)
    public ResponseEntity<Object> handleAiStreamException(AiStreamException ex) {
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(errorBody("AI_SERVICE_ERROR", ex.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Object> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(f -> f.getDefaultMessage())
                .orElse("Validation failed");
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorBody("VALIDATION_ERROR", message));
    }

    @ExceptionHandler(MissingRequestHeaderException.class)
    public ResponseEntity<Object> handleMissingHeader(MissingRequestHeaderException ex) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(errorBody("MISSING_USER_CONTEXT", "Missing required header: " + ex.getHeaderName()));
    }

    private Map<String, Object> errorBody(String code, String message) {
        return Map.of("error", Map.of("code", code, "message", message));
    }
}
