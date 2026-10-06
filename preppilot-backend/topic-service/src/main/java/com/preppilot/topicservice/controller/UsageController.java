package com.preppilot.topicservice.controller;

import com.preppilot.topicservice.dto.UsageDtos.UsageResponse;
import com.preppilot.topicservice.service.UsageLimitService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/usage")
public class UsageController {

    private final UsageLimitService usageLimitService;

    public UsageController(UsageLimitService usageLimitService) {
        this.usageLimitService = usageLimitService;
    }

    /** The caller's limits and what is left of them, for the dashboard and the mode pages. */
    @GetMapping
    public ResponseEntity<UsageResponse> getUsage(
            @RequestHeader("X-User-Id") String userId,
            @RequestHeader(value = "X-User-Experience", required = false) String experienceLevel) {
        return ResponseEntity.ok(usageLimitService.getUsage(userId, experienceLevel));
    }
}
