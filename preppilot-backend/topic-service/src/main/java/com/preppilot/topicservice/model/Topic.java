package com.preppilot.topicservice.model;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.CompoundIndexes;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document(collection = "topics")
@CompoundIndexes({
    @CompoundIndex(name = "user_name_unique", def = "{'userId': 1, 'name': 1}", unique = true)
})
public class Topic {

    @Id
    private String id;

    private String userId;

    private String name;

    private Integer testCount;  // Total completed tests for this user+topic

    private Double avgScore;    // Running average rawScore across all tests (null until first test)

    @CreatedDate
    private Instant createdAt;

    public Topic() {}

    public Topic(String userId, String name) {
        this.userId = userId;
        this.name = name;
        this.testCount = 0;
        this.avgScore = null;
    }

    public String getId() { return id; }
    public String getUserId() { return userId; }
    public String getName() { return name; }
    public Integer getTestCount() { return testCount; }
    public Double getAvgScore() { return avgScore; }
    public Instant getCreatedAt() { return createdAt; }

    public void setTestCount(Integer testCount) { this.testCount = testCount; }
    public void setAvgScore(Double avgScore) { this.avgScore = avgScore; }
}
