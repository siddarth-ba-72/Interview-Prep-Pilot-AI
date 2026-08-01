package com.preppilot.topicservice.repository;

import com.preppilot.topicservice.model.Topic;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface TopicRepository extends MongoRepository<Topic, String> {

    List<Topic> findByUserIdOrderByCreatedAtDesc(String userId);

    Optional<Topic> findByIdAndUserId(String id, String userId);

    boolean existsByUserIdAndNameIgnoreCase(String userId, String name);

    void deleteByIdAndUserId(String id, String userId);
}
