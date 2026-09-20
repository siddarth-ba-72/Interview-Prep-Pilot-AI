# Error Handling & Structured Logging Guide

This document describes the comprehensive error handling and structured logging system implemented across PrepPilot services.

## Overview

The system provides:
- **Structured JSON logging** with user context (user ID, request ID)
- **Standardized error codes** across services
- **Meaningful error messages** without internal details
- **No stack traces in production logs** (debug-only)
- **Easy extension** for new error types

## Error Code Categories

### User Errors (4xx)
These are client-side errors caused by invalid input or requests. They should be communicated clearly to users.

| Code | Status | Meaning |
|------|--------|---------|
| `USER_INVALID_INPUT` | 400 | General input validation failed |
| `USER_INVALID_TOPIC` | 400 | Topic is invalid or out of scope |
| `USER_INVALID_CONFIG` | 400 | Invalid interview/test configuration |
| `USER_UNAUTHORIZED` | 401 | Missing or invalid authentication |

### System Errors (5xx)
These are server-side errors indicating system problems.

| Code | Status | Meaning |
|------|--------|---------|
| `SYSTEM_INTERNAL_ERROR` | 500 | Unexpected internal error |
| `SYSTEM_TIMEOUT` | 504 | Request timed out |
| `SYSTEM_SERVICE_UNAVAILABLE` | 503 | Dependent service unavailable |

### AI Service Errors (4xx/5xx)
These are errors from the AI service integration.

| Code | Status | Meaning |
|------|--------|---------|
| `AI_INVALID_REQUEST` | 400 | Invalid request to AI service |
| `AI_SERVICE_ERROR` | 502 | AI service returned an error |
| `AI_SERVICE_UNAVAILABLE` | 502 | AI service is unavailable |

---

## Java Implementation (topic-service)

### Using Structured Logging

```java
import com.preppilot.topicservice.util.StructuredLogger;
import com.preppilot.topicservice.exception.ErrorCode;

public class MyService {
    private static final StructuredLogger log = new StructuredLogger(MyService.class);
    
    public void doSomething(String userId) {
        // Simple info log
        log.info("Processing request", Map.of("action", "process"));
        
        // Error with context
        log.error(
            ErrorCode.USER_INVALID_TOPIC.getCode(),
            "Topic 'InvalidTopic' is out of scope",
            Map.of("topic", "InvalidTopic")
        );
        
        // Error with exception
        try {
            // something
        } catch (Exception e) {
            log.error(
                ErrorCode.AI_SERVICE_ERROR.getCode(),
                "Failed to call AI service",
                e,
                Map.of("endpoint", "/ai/test/generate")
            );
        }
    }
}
```

### Throwing Exceptions

```java
// Using ErrorCode enum for type safety
if (topic == null) {
    throw new ApiException(ErrorCode.TOPIC_NOT_FOUND, "Topic not found");
}

// With additional context
if (invalidConfig) {
    throw new ApiException(
        ErrorCode.USER_INVALID_CONFIG,
        "Interview duration must be between 15 and 120 minutes"
    );
}

// Custom message overriding default
throw new ApiException(
    ErrorCode.AI_SERVICE_ERROR,
    "AI service returned 500: Internal Server Error"
);
```

### In Exception Handlers

```java
@ExceptionHandler(SomeException.class)
public ResponseEntity<Object> handleSpecificError(SomeException ex) {
    log.error(
        ErrorCode.SYSTEM_INTERNAL_ERROR.getCode(),
        "Something went wrong: " + ex.getMessage(),
        ex,
        Map.of("action", "process_topic")
    );
    
    return ResponseEntity
        .status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(Map.of(
            "error", Map.of(
                "code", ErrorCode.SYSTEM_INTERNAL_ERROR.getCode(),
                "message", "An unexpected error occurred"
            )
        ));
}
```

---

## Python Implementation (ai-service)

### Using Structured Logging

```python
import logging
from app.logging_config import user_id_context
from app.exceptions import InvalidTopicError, ErrorCode

logger = logging.getLogger(__name__)

async def process_topic(topic_name: str):
    user_id = user_id_context.get()  # Automatic user context
    
    # Simple log
    logger.info(f"Processing topic: {topic_name}")
    
    # Log with context data
    if not is_valid(topic_name):
        log_record = logging.LogRecord(
            name=logger.name,
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Invalid topic",
            args=(),
            exc_info=None,
        )
        log_record.context_data = {
            "error_code": ErrorCode.USER_INVALID_TOPIC,
            "topic": topic_name,
        }
        logger.handle(log_record)
        raise InvalidTopicError(f"Topic '{topic_name}' is not supported")
```

### Custom Exceptions

```python
from app.exceptions import AppException, ErrorCode, ValidationError

# Built-in exception for validation errors
raise ValidationError("Interview duration must be between 15 and 120 minutes")

# Built-in exception for invalid topics
raise InvalidTopicError("Topic 'Blockchain' is out of scope")

# Custom exception for specific scenarios
raise AppException(
    code=ErrorCode.USER_INVALID_INPUT,
    message="Invalid number of mock interview questions",
    status_code=400,
    context={"max_questions": 10, "provided": 50}
)
```

### In Error Handlers

Error handlers are automatically registered in `app/error_handlers.py`. Exceptions are caught globally and logged with user context. No stack traces are exposed to clients.

---

## Log Output Format

All logs are output as JSON for easy parsing and analysis:

```json
{
  "timestamp": "2025-09-20 10:30:45,123",
  "level": "ERROR",
  "logger": "com.preppilot.topicservice.service.AiClient",
  "message": "AI Service error",
  "user_id": "user123",
  "request_id": "req-456",
  "error_code": "AI_SERVICE_ERROR",
  "topic": "Python",
  "endpoint": "/ai/test/generate"
}
```

### Log Fields

- **timestamp**: When the log was created
- **level**: Log level (INFO, WARNING, ERROR, etc.)
- **logger**: Class/module that generated the log
- **message**: Main log message
- **user_id**: User ID from X-User-Id header (if available)
- **request_id**: Request ID for tracing
- **error_code**: Error code enum value
- **exception_type**: Exception class name (for errors)
- **exception_message**: Exception message (for errors)
- **context fields**: Custom fields like topic, endpoint, etc.

---

## Best Practices

### 1. Use Appropriate Error Codes
Choose the error code that best describes the error:
- **4xx codes** for user-caused errors (invalid input, missing resources)
- **5xx codes** for system problems (unexpected failures, timeouts)

### 2. Provide User-Friendly Messages
```java
// ❌ Bad - exposes internal details
throw new ApiException(ErrorCode.SYSTEM_INTERNAL_ERROR, 
    "NullPointerException at line 42 in AiClient.java");

// ✅ Good - clear but safe
throw new ApiException(ErrorCode.AI_SERVICE_ERROR, 
    "AI service encountered an error. Please try again later.");
```

### 3. Include Context in Logs
```java
// ❌ Bad - missing context
log.error(ErrorCode.TOPIC_NOT_FOUND.getCode(), "Topic not found");

// ✅ Good - includes topic name and user info
log.error(
    ErrorCode.TOPIC_NOT_FOUND.getCode(),
    "Topic not found",
    Map.of("topic", topicName, "user", userId)
);
```

### 4. Don't Log Stack Traces in Production
- Stack traces are only logged when log level is DEBUG
- Production logs only include exception type and message
- Stack traces are valuable for development and debugging

### 5. Create Custom Exception Classes for Domain Concepts
```java
// Create new exception class for repeated scenarios
public class TopicOutOfScopeException extends ApiException {
    public TopicOutOfScopeException(String topicName) {
        super(
            ErrorCode.USER_INVALID_TOPIC,
            String.format("Topic '%s' is out of scope", topicName)
        );
    }
}

// Usage is cleaner
if (!isInScope(topic)) {
    throw new TopicOutOfScopeException(topic);
}
```

---

## Adding New Error Scenarios

### Step 1: Add Error Code
Add a new entry to the `ErrorCode` enum in both services:

**Java** (`topic-service/src/main/java/.../exception/ErrorCode.java`):
```java
MY_NEW_ERROR(HttpStatus.BAD_REQUEST, "Description of error");
```

**Python** (`ai-service/app/exceptions.py`):
```python
MY_NEW_ERROR = "MY_NEW_ERROR"
```

### Step 2: Create Exception Class (if needed)
For repeated error scenarios, create a specific exception:

```java
public class MySpecificException extends ApiException {
    public MySpecificException(String message) {
        super(ErrorCode.MY_NEW_ERROR, message);
    }
}
```

```python
class MySpecificError(AppException):
    def __init__(self, message: str):
        super().__init__(
            code=ErrorCode.MY_NEW_ERROR,
            message=message,
            status_code=400
        )
```

### Step 3: Use in Code
```java
throw new MySpecificException("Details about what went wrong");
```

```python
raise MySpecificError("Details about what went wrong")
```

### Step 4: Update Documentation
Add the new error code to this guide with its meaning and when it occurs.

---

## Debugging with Structured Logs

### Finding Errors for a Specific User
```bash
# Using grep and jq
cat logs/*.json | jq 'select(.user_id == "user123") | select(.level == "ERROR")'
```

### Tracing a Request
```bash
# Find all logs for a specific request
cat logs/*.json | jq 'select(.request_id == "req-456")'
```

### Analyzing Error Frequency
```bash
# Count errors by error code
cat logs/*.json | jq -r '.error_code' | sort | uniq -c
```

---

## Related Files

- **Java**: 
  - `ErrorCode.java` - Enum of all error codes
  - `StructuredLogger.java` - Logging utility
  - `GlobalExceptionHandler.java` - Global error handler
  - `ApiException.java` - Base exception class

- **Python**:
  - `app/exceptions.py` - Exception classes and ErrorCode enum
  - `app/logging_config.py` - Structured logging setup
  - `app/error_handlers.py` - Global error handlers
  - `app/middleware.py` - User context middleware

---

## Testing Error Scenarios

### Unit Testing Error Logging

```java
@Test
void testErrorLogging() {
    assertThrows(TopicNotFoundException.class, () -> {
        service.getTopic("nonexistent");
    });
    // Verify log was created with correct error code
}
```

### Integration Testing Error Responses

```java
@Test
void testErrorResponse() {
    MvcResult result = mockMvc.perform(post("/api/v1/topics")
        .contentType(MediaType.APPLICATION_JSON)
        .content("{\"name\": \"Invalid Topic\"}")
    ).andExpect(status().isBadRequest()).andReturn();
    
    String body = result.getResponse().getContentAsString();
    assertTrue(body.contains("USER_INVALID_TOPIC"));
}
```

