# Error Handling Quick Reference

## Common Error Codes

| Code | Status | Use When |
|------|--------|----------|
| `USER_INVALID_INPUT` | 400 | User provides invalid data |
| `USER_INVALID_TOPIC` | 400 | Topic is out of scope |
| `USER_INVALID_CONFIG` | 400 | Invalid interview/test settings |
| `USER_UNAUTHORIZED` | 401 | Missing/invalid credentials |
| `TOPIC_NOT_FOUND` | 404 | Topic doesn't exist |
| `SYSTEM_INTERNAL_ERROR` | 500 | Unexpected server error |
| `AI_INVALID_REQUEST` | 400 | Bad request to AI service |
| `AI_SERVICE_ERROR` | 502 | AI service returned error |

---

## Java Quick Snippets

### Log an error with context
```java
log.error(
    ErrorCode.USER_INVALID_TOPIC.getCode(),
    "Topic not in scope",
    Map.of("topic", topicName, "reason", "AI limitation")
);
```

### Throw an exception
```java
throw new ApiException(
    ErrorCode.TOPIC_NOT_FOUND,
    "Topic 'Rust' not found"
);
```

### Log with exception
```java
try {
    // code
} catch (Exception e) {
    log.error(ErrorCode.SYSTEM_INTERNAL_ERROR.getCode(), "Failed", e);
}
```

---

## Python Quick Snippets

### Log an error with context
```python
log_record = logging.LogRecord(
    name=logger.name, level=logging.WARNING,
    pathname="", lineno=0, msg="Topic invalid",
    args=(), exc_info=None
)
log_record.context_data = {
    "error_code": ErrorCode.USER_INVALID_TOPIC,
    "topic": topic_name
}
logger.handle(log_record)
```

### Throw an exception
```python
raise InvalidTopicError("Topic 'Blockchain' is out of scope")
```

### Validation error
```python
raise ValidationError("Interview duration must be 15-120 minutes")
```

---

## Log Output Format

```json
{
  "timestamp": "2025-09-20 14:30:45,123",
  "level": "ERROR",
  "logger": "com.preppilot.service.MyClass",
  "message": "Brief description",
  "user_id": "user123",
  "error_code": "USER_INVALID_TOPIC",
  "topic": "Custom context data"
}
```

---

## Response Format to Client

```json
{
  "error": {
    "code": "USER_INVALID_TOPIC",
    "message": "Topic 'Python' is out of scope"
  }
}
```

**No stack traces. No internal details.**

---

## When to Use Each Error Code

### 4xx Client Errors (USER_*, AI_INVALID_REQUEST)
- ✅ Bad input from user
- ✅ Missing required fields
- ✅ Out of scope topic
- ✅ Invalid configuration

### 5xx Server Errors (SYSTEM_*)
- ✅ Unexpected exceptions
- ✅ Database failures
- ✅ Timeouts
- ✅ Dependencies down

### Service Errors (AI_SERVICE_*)
- ✅ AI service returned 4xx → Use `AI_INVALID_REQUEST`
- ✅ AI service returned 5xx → Use `AI_SERVICE_ERROR`
- ✅ Can't reach AI service → Use `AI_SERVICE_UNAVAILABLE`

---

## Debugging Tips

### Find errors for a user
```bash
grep "user_id.*user123" logs/*.json | jq '.'
```

### Find all error codes
```bash
jq -r '.error_code' logs/*.json | sort | uniq -c
```

### Find specific error type
```bash
jq 'select(.error_code == "USER_INVALID_TOPIC")' logs/*.json
```

### Trace a request
```bash
jq 'select(.request_id == "xyz123")' logs/*.json
```

---

## Common Mistakes to Avoid

❌ **Don't** expose internal details
```java
// Bad
throw new ApiException(ErrorCode.SYSTEM_INTERNAL_ERROR,
    "NullPointerException at AiClient.java:160");

// Good
throw new ApiException(ErrorCode.SYSTEM_INTERNAL_ERROR,
    "Failed to generate test questions");
```

❌ **Don't** use wrong error code
```java
// Bad - This is a user error, not system error
throw new ApiException(ErrorCode.SYSTEM_INTERNAL_ERROR,
    "Topic 'Python' not found");

// Good
throw new ApiException(ErrorCode.TOPIC_NOT_FOUND,
    "Topic 'Python' not found");
```

❌ **Don't** forget context
```java
// Bad - No way to know what topic caused the error
log.error(ErrorCode.USER_INVALID_TOPIC.getCode(), "Topic invalid");

// Good
log.error(ErrorCode.USER_INVALID_TOPIC.getCode(),
    "Topic invalid", Map.of("topic", topicName));
```

❌ **Don't** log passwords or sensitive data
```java
// Bad
log.error("Auth failed", Map.of("password", password));

// Good
log.error("Auth failed", Map.of("username", username));
```

---

## File Locations

**Error handling files:**
- Java: `topic-service/src/main/java/com/preppilot/topicservice/exception/`
- Python: `ai-service/app/exceptions.py`, `logging_config.py`, `error_handlers.py`

**Documentation:**
- `docs/ERROR_HANDLING_GUIDE.md` - Full guide
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- This file - Quick reference

---

## See Also

- `docs/ERROR_HANDLING_GUIDE.md` - Complete guide with examples and best practices
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- Error handling code in both services
