package com.preppilot.topicservice.controller;

import com.preppilot.topicservice.dto.TopicDtos.CreateTopicRequest;
import com.preppilot.topicservice.dto.TopicDtos.TopicResponse;
import com.preppilot.topicservice.dto.TestDtos.*;
import com.preppilot.topicservice.service.TopicService;
import com.preppilot.topicservice.service.TestService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/topics")
public class TopicController {

    private final TopicService topicService;
    private final TestService testService;

    public TopicController(TopicService topicService, TestService testService) {
        this.topicService = topicService;
        this.testService = testService;
    }

    @PostMapping
    public ResponseEntity<TopicResponse> create(@RequestHeader("X-User-Id") String userId,
                                                 @Valid @RequestBody CreateTopicRequest request) {
        TopicResponse created = topicService.create(userId, request.name());
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping
    public ResponseEntity<List<TopicResponse>> list(@RequestHeader("X-User-Id") String userId) {
        return ResponseEntity.ok(topicService.list(userId));
    }

    @DeleteMapping("/{topicId}")
    public ResponseEntity<Void> delete(@RequestHeader("X-User-Id") String userId,
                                        @PathVariable String topicId) {
        topicService.delete(userId, topicId);
        return ResponseEntity.noContent().build();
    }

    // Test Mode Endpoints

    @PostMapping("/{topicId}/tests")
    public ResponseEntity<TestSessionStartResponse> startTest(@RequestHeader("X-User-Id") String userId,
                                                              @PathVariable String topicId) {
        TestSessionStartResponse response = testService.startTest(userId, topicId);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/{topicId}/tests/{testId}")
    public ResponseEntity<TestSessionStartResponse> getTest(@RequestHeader("X-User-Id") String userId,
                                                             @PathVariable String topicId,
                                                             @PathVariable String testId) {
        TestSessionStartResponse response = testService.getTest(userId, topicId, testId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{topicId}/tests/{testId}/submit")
    public ResponseEntity<TestReportResponse> submitTest(@RequestHeader("X-User-Id") String userId,
                                                         @PathVariable String topicId,
                                                         @PathVariable String testId,
                                                         @Valid @RequestBody SubmitTestRequest request) {
        TestReportResponse response = testService.submitTest(userId, topicId, testId, request);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{topicId}/tests/{testId}/report")
    public ResponseEntity<TestReportResponse> getTestReport(@RequestHeader("X-User-Id") String userId,
                                                            @PathVariable String topicId,
                                                            @PathVariable String testId) {
        TestReportResponse response = testService.getTestReport(userId, topicId, testId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{topicId}/tests")
    public ResponseEntity<List<TestSessionListItemResponse>> listTestSessions(@RequestHeader("X-User-Id") String userId,
                                                                              @PathVariable String topicId) {
        List<TestSessionListItemResponse> response = testService.listTestSessions(userId, topicId);
        return ResponseEntity.ok(response);
    }
}
