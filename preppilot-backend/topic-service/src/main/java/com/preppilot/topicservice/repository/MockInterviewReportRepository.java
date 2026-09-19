package com.preppilot.topicservice.repository;

import com.preppilot.topicservice.model.MockInterviewReport;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

@Repository
public interface MockInterviewReportRepository extends MongoRepository<MockInterviewReport, String> {
    Optional<MockInterviewReport> findByMockInterviewSessionId(String sessionId);
    List<MockInterviewReport> findByTopicIdAndUserId(String topicId, String userId);

    /** Batch lookup for the history list - one query instead of one per session. */
    List<MockInterviewReport> findByMockInterviewSessionIdIn(Collection<String> sessionIds);
}
