package com.preppilot.topicservice.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.preppilot.topicservice.dto.ChatDtos.ChatSessionResponse;
import com.preppilot.topicservice.dto.ChatDtos.PagedMessagesResponse;
import com.preppilot.topicservice.dto.ChatDtos.SendMessageRequest;
import com.preppilot.topicservice.exception.ApiException;
import com.preppilot.topicservice.service.ChatSessionService;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Instant;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/topics/{topicId}/chat")
public class ChatController {

    private final ChatSessionService chatSessionService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ChatController(ChatSessionService chatSessionService) {
        this.chatSessionService = chatSessionService;
    }

    @GetMapping
    public ResponseEntity<ChatSessionResponse> getOrCreate(@RequestHeader("X-User-Id") String userId,
                                                            @PathVariable String topicId) {
        return ResponseEntity.ok(chatSessionService.getOrCreate(userId, topicId));
    }

    @GetMapping("/messages")
    public ResponseEntity<PagedMessagesResponse> getMessages(
            @RequestHeader("X-User-Id") String userId,
            @PathVariable String topicId,
            @RequestParam(required = false) String before) {
        Instant beforeInstant = before != null ? Instant.parse(before) : null;
        return ResponseEntity.ok(chatSessionService.getMessages(userId, topicId, beforeInstant));
    }

    @PostMapping(value = "/messages", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter sendMessage(@RequestHeader("X-User-Id") String userId,
                                   @PathVariable String topicId,
                                   @Valid @RequestBody SendMessageRequest request) {
        try {
            return chatSessionService.streamReply(userId, topicId, request.content());
        } catch (ApiException ex) {
            return errorEmitter(ex.getMessage());
        }
    }

    private SseEmitter errorEmitter(String message) {
        SseEmitter emitter = new SseEmitter(0L);
        try {
            String data = objectMapper.writeValueAsString(Map.of("error", message));
            emitter.send(SseEmitter.event().data(data, MediaType.APPLICATION_JSON));
        } catch (IOException ignored) {
        }
        emitter.complete();
        return emitter;
    }
}
