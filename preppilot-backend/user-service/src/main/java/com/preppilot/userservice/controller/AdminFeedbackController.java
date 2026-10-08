package com.preppilot.userservice.controller;

import com.preppilot.userservice.dto.FeedbackDtos.AdminFeedbackPage;
import com.preppilot.userservice.service.FeedbackService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** Read-only. Only admins get here: AdminAccessInterceptor checks the token's role first. */
@RestController
@RequestMapping("/api/v1/admin/feedback")
public class AdminFeedbackController {

    private final FeedbackService feedbackService;

    public AdminFeedbackController(FeedbackService feedbackService) {
        this.feedbackService = feedbackService;
    }

    @GetMapping
    public ResponseEntity<AdminFeedbackPage> list(@RequestParam(defaultValue = "0") int page,
                                                  @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(feedbackService.list(page, size));
    }
}
