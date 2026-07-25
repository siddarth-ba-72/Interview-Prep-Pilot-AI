package com.preppilot.topicservice.repository;

import com.preppilot.topicservice.model.TestReport;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TestReportRepository extends MongoRepository<TestReport, String> {
    Optional<TestReport> findByTestSessionId(String testSessionId);
    List<TestReport> findByTopicIdAndUserId(String topicId, String userId);
}
