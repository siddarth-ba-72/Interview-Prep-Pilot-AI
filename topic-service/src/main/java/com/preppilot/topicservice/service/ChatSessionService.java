package com.preppilot.topicservice.service;

import com.preppilot.topicservice.dto.ChatDtos.ChatSessionResponse;
import com.preppilot.topicservice.dto.ChatDtos.MessageResponse;
import com.preppilot.topicservice.exception.ChatSessionNotFoundException;
import com.preppilot.topicservice.exception.TopicNotFoundException;
import com.preppilot.topicservice.model.ChatSession;
import com.preppilot.topicservice.model.Message;
import com.preppilot.topicservice.model.Topic;
import com.preppilot.topicservice.repository.ChatSessionRepository;
import com.preppilot.topicservice.repository.TopicRepository;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Instant;
import java.util.List;
import java.util.Map;

@Service
public class ChatSessionService {

    private static final String MODE_CLARIFY = "CLARIFY";
    private static final String MODE_GENERATE_CONTENT = "GENERATE_CONTENT";
    private static final String MODE_FOLLOW_UP = "FOLLOW_UP";

    private final ChatSessionRepository chatSessionRepository;
    private final TopicRepository topicRepository;
    private final AiClient aiClient;

    public ChatSessionService(ChatSessionRepository chatSessionRepository,
                               TopicRepository topicRepository,
                               AiClient aiClient) {
        this.chatSessionRepository = chatSessionRepository;
        this.topicRepository = topicRepository;
        this.aiClient = aiClient;
    }

    public ChatSessionResponse getOrCreate(String userId, String topicId) {
        ChatSession session = chatSessionRepository.findByUserIdAndTopicId(userId, topicId)
                .orElseGet(() -> createSession(userId, topicId));
        return toResponse(session);
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
            // client disconnected; nothing to persist beyond what's already saved
        }
    }

    private ChatSessionResponse toResponse(ChatSession session) {
        List<MessageResponse> messages = session.getMessages().stream()
                .map(m -> new MessageResponse(m.getRole().name(), m.getContent(), m.getTimestamp()))
                .toList();
        return new ChatSessionResponse(session.getTopicId(), messages);
    }
}
