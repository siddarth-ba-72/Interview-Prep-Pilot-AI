package com.preppilot.topicservice.controller;

import com.preppilot.topicservice.dto.TopicDtos.CreateTopicRequest;
import com.preppilot.topicservice.dto.TopicDtos.TopicResponse;
import com.preppilot.topicservice.service.TopicService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/topics")
public class TopicController {

    private final TopicService topicService;

    public TopicController(TopicService topicService) {
        this.topicService = topicService;
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
}
