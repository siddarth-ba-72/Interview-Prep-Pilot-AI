package com.preppilot.topicservice.service;

import com.preppilot.topicservice.dto.ChatDtos.ChatSessionResponse;
import com.preppilot.topicservice.dto.ChatDtos.MessageResponse;
import com.preppilot.topicservice.dto.ChatDtos.PagedMessagesResponse;
import com.preppilot.topicservice.exception.ChatSessionNotFoundException;
import com.preppilot.topicservice.exception.TopicNotFoundException;
import com.preppilot.topicservice.model.ChatSession;
import com.preppilot.topicservice.model.Message;
import com.preppilot.topicservice.model.Topic;
import com.preppilot.topicservice.repository.ChatSessionRepository;
import com.preppilot.topicservice.repository.TopicRepository;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Instant;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@Service
public class ChatSessionService {

    private static final int PAGE_SIZE = 20;
    private static final String MODE_CLARIFY = "CLARIFY";
    private static final String MODE_GENERATE_CONTENT = "GENERATE_CONTENT";
    private static final String MODE_FOLLOW_UP = "FOLLOW_UP";

    private final ChatSessionRepository chatSessionRepository;
    private final TopicRepository topicRepository;
    private final AiClient aiClient;
    private final MongoTemplate mongoTemplate;

    public ChatSessionService(ChatSessionRepository chatSessionRepository,
                               TopicRepository topicRepository,
                               AiClient aiClient,
                               MongoTemplate mongoTemplate) {
        this.chatSessionRepository = chatSessionRepository;
        this.topicRepository = topicRepository;
        this.aiClient = aiClient;
        this.mongoTemplate = mongoTemplate;
    }

    /** Returns the session with the most recent PAGE_SIZE messages. */
    public ChatSessionResponse getOrCreate(String userId, String topicId) {
        ChatSession session = chatSessionRepository.findByUserIdAndTopicId(userId, topicId)
                .orElseGet(() -> createSession(userId, topicId));
        return toPagedResponse(session);
    }

    /**
     * Returns PAGE_SIZE messages older than {@code before} (exclusive).
     * Pass null to get the most recent page.
     */
    public PagedMessagesResponse getMessages(String userId, String topicId, Instant before) {
        ChatSession session = chatSessionRepository.findByUserIdAndTopicId(userId, topicId)
                .orElseThrow(() -> new ChatSessionNotFoundException(topicId));

        List<Message> all = session.getMessages();
        int total = all.size();

        // Determine the end index (exclusive) — everything before the cursor
        int endIndex = total;
        if (before != null) {
            for (int i = total - 1; i >= 0; i--) {
                if (all.get(i).getTimestamp().isBefore(before)) {
                    endIndex = i + 1;
                    break;
                }
                // If no message is before the cursor, return empty
                if (i == 0) endIndex = 0;
            }
        }

        int startIndex = Math.max(0, endIndex - PAGE_SIZE);
        List<Message> slice = all.subList(startIndex, endIndex);
        boolean hasMore = startIndex > 0;

        List<MessageResponse> messages = slice.stream()
                .map(m -> new MessageResponse(m.getRole().name(), m.getContent(), m.getTimestamp()))
                .toList();

        return new PagedMessagesResponse(messages, hasMore);
    }

    private ChatSession createSession(String userId, String topicId) {
        Topic topic = topicRepository.findByIdAndUserId(topicId, userId)
                .orElseThrow(() -> new TopicNotFoundException(topicId));

        String clarifyContent = aiClient.streamLearn(topic.getName(), MODE_CLARIFY, List.of())
                .collect(StringBuilder::new, StringBuilder::append)
                .map(StringBuilder::toString)
                .block();

        ChatSession session = new ChatSession(userId, topicId);
        session.addMessage(new Message(Message.Role.AI, clarifyContent, Instant.now()));
        return chatSessionRepository.save(session);
    }

    public SseEmitter streamReply(String userId, String topicId, String userContent) {
        Topic topic = topicRepository.findByIdAndUserId(topicId, userId)
                .orElseThrow(() -> new TopicNotFoundException(topicId));
        ChatSession session = chatSessionRepository.findByUserIdAndTopicId(userId, topicId)
                .orElseThrow(() -> new ChatSessionNotFoundException(topicId));

        String mode = determineMode(session.getMessages().size());

        session.addMessage(new Message(Message.Role.USER, userContent, Instant.now()));
        chatSessionRepository.save(session);

        // Pass full history to AI for context, not just the visible page
        List<AiClient.ChatMessagePayload> history = session.getMessages().stream()
                .map(AiClient::toPayload)
                .toList();

        SseEmitter emitter = new SseEmitter(0L);
        StringBuilder buffer = new StringBuilder();

        aiClient.streamLearn(topic.getName(), mode, history).subscribe(
                token -> {
                    buffer.append(token);
                    sendEvent(emitter, Map.of("token", token));
                },
                error -> {
                    sendEvent(emitter, Map.of("error", "The AI response could not be completed. Please try again."));
                    emitter.complete();
                },
                () -> {
                    session.addMessage(new Message(Message.Role.AI, buffer.toString(), Instant.now()));
                    chatSessionRepository.save(session);
                    sendDone(emitter);
                    emitter.complete();
                }
        );

        return emitter;
    }

    public void deleteForTopic(String userId, String topicId) {
        chatSessionRepository.deleteByUserIdAndTopicId(userId, topicId);
    }

    private String determineMode(int messageCountBeforeReply) {
        return messageCountBeforeReply <= 1 ? MODE_GENERATE_CONTENT : MODE_FOLLOW_UP;
    }

    private void sendEvent(SseEmitter emitter, Map<String, String> payload) {
        try {
            emitter.send(SseEmitter.event().data(payload, MediaType.APPLICATION_JSON));
        } catch (IOException e) {
            emitter.completeWithError(e);
        }
    }

    private void sendDone(SseEmitter emitter) {
        try {
            emitter.send(SseEmitter.event().data("[DONE]"));
        } catch (IOException ignored) {
        }
    }

    private ChatSessionResponse toPagedResponse(ChatSession session) {
        List<Message> all = session.getMessages();
        int total = all.size();
        int startIndex = Math.max(0, total - PAGE_SIZE);
        List<Message> slice = all.subList(startIndex, total);
        boolean hasMore = startIndex > 0;

        List<MessageResponse> messages = slice.stream()
                .map(m -> new MessageResponse(m.getRole().name(), m.getContent(), m.getTimestamp()))
                .toList();
        return new ChatSessionResponse(session.getTopicId(), messages, hasMore);
    }
}

