package com.preppilot.topicservice.exception;

import com.preppilot.topicservice.service.AiStreamException;
import com.preppilot.topicservice.util.StructuredLogger;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final StructuredLogger log = new StructuredLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<Object> handleApiException(ApiException ex) {
        log.error(ex.getCode(), ex.getMessage());
        return ResponseEntity.status(ex.getStatus()).body(errorBody(ex.getCode(), ex.getMessage()));
    }

    @ExceptionHandler(AiStreamException.class)
    public ResponseEntity<Object> handleAiStreamException(AiStreamException ex) {
        log.error(ErrorCode.AI_SERVICE_ERROR.getCode(), ex.getMessage(), ex);
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(errorBody(ErrorCode.AI_SERVICE_ERROR.getCode(), "AI service error"));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Object> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(f -> f.getDefaultMessage())
                .orElse("Validation failed");
        log.error(ErrorCode.USER_INVALID_INPUT.getCode(), message);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorBody(ErrorCode.USER_INVALID_INPUT.getCode(), message));
    }

    @ExceptionHandler(MissingRequestHeaderException.class)
    public ResponseEntity<Object> handleMissingHeader(MissingRequestHeaderException ex) {
        log.error(ErrorCode.USER_UNAUTHORIZED.getCode(), "Missing header: " + ex.getHeaderName());
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(errorBody(ErrorCode.USER_UNAUTHORIZED.getCode(), "Missing required header"));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Object> handleGenericException(Exception ex) {
        log.error(ErrorCode.SYSTEM_INTERNAL_ERROR.getCode(), "Unexpected error", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorBody(ErrorCode.SYSTEM_INTERNAL_ERROR.getCode(), "Internal server error"));
    }

    private Map<String, Object> errorBody(String code, String message) {
        return Map.of("error", Map.of("code", code, "message", message));
    }
}
