package com.preppilot.topicservice.repository;

import com.preppilot.topicservice.model.TestSession;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TestSessionRepository extends MongoRepository<TestSession, String> {
    Optional<TestSession> findByTopicIdAndUserIdAndStatus(String topicId, String userId, TestSession.Status status);
    List<TestSession> findByTopicIdAndUserIdAndStatus(String topicId, String userId, TestSession.Status status, org.springframework.data.domain.Pageable pageable);
    List<TestSession> findByTopicIdAndUserId(String topicId, String userId);
}
