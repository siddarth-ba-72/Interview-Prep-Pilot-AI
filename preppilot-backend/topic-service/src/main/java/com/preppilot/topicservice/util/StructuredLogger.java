package com.preppilot.topicservice.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import jakarta.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.Map;

public class StructuredLogger {
    private final Logger logger;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public StructuredLogger(Class<?> clazz) {
        this.logger = LoggerFactory.getLogger(clazz);
    }

    private String getUserId() {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                return request.getHeader("X-User-Id");
            }
        } catch (Exception e) {
            // Request context not available
        }
        return null;
    }

    private String getUserEmail() {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                return request.getHeader("X-User-Email");
            }
        } catch (Exception e) {
            // Request context not available
        }
        return null;
    }

    private Map<String, Object> buildContext(String errorCode, String message, Map<String, Object> additionalContext) {
        Map<String, Object> context = new HashMap<>();
        context.put("timestamp", System.currentTimeMillis());
        context.put("errorCode", errorCode);
        context.put("message", message);

        String userId = getUserId();
        String userEmail = getUserEmail();
        if (userId != null) {
            context.put("userId", userId);
        }
        if (userEmail != null) {
            context.put("userEmail", userEmail);
        }

        if (additionalContext != null) {
            context.putAll(additionalContext);
        }

        return context;
    }

    public void error(String errorCode, String message) {
        logError(errorCode, message, (Map<String, Object>) null);
    }

    public void error(String errorCode, String message, Map<String, Object> additionalContext) {
        logError(errorCode, message, additionalContext);
    }

    public void error(String errorCode, String message, Throwable throwable) {
        logError(errorCode, message, throwable, null);
    }

    public void error(String errorCode, String message, Throwable throwable, Map<String, Object> additionalContext) {
        logError(errorCode, message, throwable, additionalContext);
    }

    private void logError(String errorCode, String message, Map<String, Object> additionalContext) {
        Map<String, Object> context = buildContext(errorCode, message, additionalContext);
        logger.error(toJson(context));
    }

    private void logError(String errorCode, String message, Throwable throwable, Map<String, Object> additionalContext) {
        Map<String, Object> context = buildContext(errorCode, message, additionalContext);
        context.put("exception", throwable.getClass().getName());
        context.put("exceptionMessage", throwable.getMessage());
        // Only log stack trace at debug level to avoid noise
        logger.error(toJson(context));
        if (logger.isDebugEnabled()) {
            logger.debug("Stack trace for {}", errorCode, throwable);
        }
    }

    public void warn(String errorCode, String message) {
        warn(errorCode, message, null);
    }

    public void warn(String errorCode, String message, Map<String, Object> additionalContext) {
        Map<String, Object> context = buildContext(errorCode, message, additionalContext);
        logger.warn(toJson(context));
    }

    public void info(String message) {
        info(message, null);
    }

    public void info(String message, Map<String, Object> additionalContext) {
        Map<String, Object> context = buildContext(null, message, additionalContext);
        context.remove("errorCode");
        logger.info(toJson(context));
    }

    private String toJson(Map<String, Object> context) {
        try {
            return objectMapper.writeValueAsString(context);
        } catch (Exception e) {
            return context.toString();
        }
    }
}
