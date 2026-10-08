package com.preppilot.userservice.repository;

import com.preppilot.userservice.model.Feedback;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface FeedbackRepository extends MongoRepository<Feedback, String> {
}
