package com.preppilot.topicservice.repository;

import com.preppilot.topicservice.model.MockInterviewSession;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface MockInterviewSessionRepository extends MongoRepository<MockInterviewSession, String> {
    Optional<MockInterviewSession> findByTopicIdAndUserIdAndStatus(String topicId, String userId, MockInterviewSession.Status status);
    List<MockInterviewSession> findByTopicIdAndUserId(String topicId, String userId);
}
