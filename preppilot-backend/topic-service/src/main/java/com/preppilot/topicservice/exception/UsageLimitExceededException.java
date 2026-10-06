package com.preppilot.topicservice.exception;

import java.time.Instant;

/** The user has used up an action's limit; {@code retryAt} is when they may use it again. */
public class UsageLimitExceededException extends ApiException {

    private final Instant retryAt;

    public UsageLimitExceededException(String message, Instant retryAt) {
        super(ErrorCode.USAGE_LIMIT_REACHED, message);
        this.retryAt = retryAt;
    }

    public Instant getRetryAt() { return retryAt; }
}
