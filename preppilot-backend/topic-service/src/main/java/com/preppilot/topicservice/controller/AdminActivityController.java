package com.preppilot.topicservice.controller;

import com.preppilot.topicservice.dto.AdminDtos.ActivitySummary;
import com.preppilot.topicservice.dto.AdminDtos.UserActivity;
import com.preppilot.topicservice.dto.AdminDtos.UserActivityDetail;
import com.preppilot.topicservice.service.AdminActivityService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/** Read-only. Only admins get here: AdminAccessInterceptor checks the token's role first. */
@RestController
@RequestMapping("/api/v1/admin/activity")
public class AdminActivityController {

    private final AdminActivityService adminActivityService;

    public AdminActivityController(AdminActivityService adminActivityService) {
        this.adminActivityService = adminActivityService;
    }

    @GetMapping("/summary")
    public ResponseEntity<ActivitySummary> summary() {
        return ResponseEntity.ok(adminActivityService.summary());
    }

    /** Counts for a page of users from user-service's admin list: {@code ?ids=a,b,c}. */
    @GetMapping("/users")
    public ResponseEntity<List<UserActivity>> usersActivity(@RequestParam(required = false) List<String> ids) {
        return ResponseEntity.ok(adminActivityService.usersActivity(ids != null ? ids : List.of()));
    }

    @GetMapping("/users/{userId}")
    public ResponseEntity<UserActivityDetail> userActivity(@PathVariable String userId) {
        return ResponseEntity.ok(adminActivityService.userActivity(userId));
    }
}
