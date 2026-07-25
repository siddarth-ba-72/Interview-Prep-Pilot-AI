package com.preppilot.topicservice.service;

import com.preppilot.topicservice.dto.TopicDtos.TopicResponse;
import com.preppilot.topicservice.exception.DuplicateTopicException;
import com.preppilot.topicservice.exception.TopicNotFoundException;
import com.preppilot.topicservice.model.Topic;
import com.preppilot.topicservice.repository.TopicRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TopicService {

    private final TopicRepository topicRepository;
    private final ChatSessionService chatSessionService;

    public TopicService(TopicRepository topicRepository, ChatSessionService chatSessionService) {
        this.topicRepository = topicRepository;
        this.chatSessionService = chatSessionService;
    }

    public TopicResponse create(String userId, String name) {
        if (topicRepository.existsByUserIdAndNameIgnoreCase(userId, name)) {
            throw new DuplicateTopicException(name);
        }
        Topic saved = topicRepository.save(new Topic(userId, name));
        return toResponse(saved);
    }

    public List<TopicResponse> list(String userId) {
        return topicRepository.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(this::toResponse)
                .toList();
    }

    public void delete(String userId, String topicId) {
        Topic topic = topicRepository.findByIdAndUserId(topicId, userId)
                .orElseThrow(() -> new TopicNotFoundException(topicId));
        chatSessionService.deleteForTopic(userId, topic.getId());
        topicRepository.deleteByIdAndUserId(topic.getId(), userId);
    }

    private TopicResponse toResponse(Topic topic) {
        return new TopicResponse(
            topic.getId(),
            topic.getName(),
            topic.getCreatedAt(),
            topic.getTestCount(),
            topic.getAvgScore()
        );
    }
}
