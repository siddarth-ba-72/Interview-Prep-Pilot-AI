package com.preppilot.topicservice.exception;

import org.springframework.http.HttpStatus;

public class ApiException extends RuntimeException {

    private final HttpStatus status;
    private final String code;

    public ApiException(HttpStatus status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }

    public ApiException(ErrorCode errorCode, String message) {
        super(message != null ? message : errorCode.getMessage());
        this.status = errorCode.getStatus();
        this.code = errorCode.getCode();
    }

    public ApiException(ErrorCode errorCode) {
        this(errorCode, errorCode.getMessage());
    }

    public HttpStatus getStatus() { return status; }
    public String getCode() { return code; }
}
