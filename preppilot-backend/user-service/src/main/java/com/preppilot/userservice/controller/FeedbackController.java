package com.preppilot.userservice.controller;

import com.preppilot.userservice.dto.FeedbackDtos.FeedbackReceipt;
import com.preppilot.userservice.dto.FeedbackDtos.SubmitFeedbackRequest;
import com.preppilot.userservice.service.FeedbackService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** Under /api/v1/users/**, so JwtAuthFilter sets X-User-Id from the verified token. */
@RestController
@RequestMapping("/api/v1/users/me/feedback")
public class FeedbackController {

    private final FeedbackService feedbackService;

    public FeedbackController(FeedbackService feedbackService) {
        this.feedbackService = feedbackService;
    }

    @PostMapping
    public ResponseEntity<FeedbackReceipt> submit(@RequestHeader("X-User-Id") String userId,
                                                  @Valid @RequestBody SubmitFeedbackRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(feedbackService.submit(userId, request.message()));
    }
}
