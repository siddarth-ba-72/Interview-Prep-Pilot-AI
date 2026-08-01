package com.preppilot.topicservice.repository;

import com.preppilot.topicservice.model.ChatSession;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface ChatSessionRepository extends MongoRepository<ChatSession, String> {

    Optional<ChatSession> findByUserIdAndTopicId(String userId, String topicId);

    void deleteByUserIdAndTopicId(String userId, String topicId);
}
