package com.preppilot.topicservice.model;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

@Document(collection = "mock_interview_reports")
public class MockInterviewReport {

    @Id
    private String id;

    @Indexed
    private String mockInterviewSessionId;

    @Indexed
    private String topicId;

    @Indexed
    private String userId;

    private Integer score;

    private Integer maxScore;

    private Integer passThreshold;

    private Boolean passed;

    private List<String> strengths;

    private List<String> weaknesses;

    private List<ImprovementSuggestion> improvementSuggestions;

    private String overallSummary;

    private Config config;

    private String completionReason;

    private List<MockInterviewSession.Exchange> exchangeSummary;

    @CreatedDate
    private Instant createdAt;

    public static class ImprovementSuggestion {
        public String question;
        public String userAnswer;
        public String theme;
        public String betterAnswer;

        public ImprovementSuggestion() {}

        public ImprovementSuggestion(String question, String userAnswer, String theme, String betterAnswer) {
            this.question = question;
            this.userAnswer = userAnswer;
            this.theme = theme;
            this.betterAnswer = betterAnswer;
        }
    }

    public static class Config {
        public String experienceLevel;
        public String difficulty;
        public Integer durationMinutes;

        public Config() {}

        public Config(String experienceLevel, String difficulty, Integer durationMinutes) {
            this.experienceLevel = experienceLevel;
            this.difficulty = difficulty;
            this.durationMinutes = durationMinutes;
        }
    }

    public MockInterviewReport() {}

    public MockInterviewReport(String sessionId, String topicId, String userId) {
        this.mockInterviewSessionId = sessionId;
        this.topicId = topicId;
        this.userId = userId;
        this.maxScore = 100;
        this.passThreshold = 75;
    }

    public String getId() { return id; }
    public String getMockInterviewSessionId() { return mockInterviewSessionId; }
    public String getTopicId() { return topicId; }
    public String getUserId() { return userId; }
    public Integer getScore() { return score; }
    public Integer getMaxScore() { return maxScore; }
    public Integer getPassThreshold() { return passThreshold; }
    public Boolean getPassed() { return passed; }
    public List<String> getStrengths() { return strengths; }
    public List<String> getWeaknesses() { return weaknesses; }
    public List<ImprovementSuggestion> getImprovementSuggestions() { return improvementSuggestions; }
    public String getOverallSummary() { return overallSummary; }
    public Config getConfig() { return config; }
    public String getCompletionReason() { return completionReason; }
    public List<MockInterviewSession.Exchange> getExchangeSummary() { return exchangeSummary; }
    public Instant getCreatedAt() { return createdAt; }

    public void setScore(Integer score) { this.score = score; }
    public void setPassed(Boolean passed) { this.passed = passed; }
    public void setStrengths(List<String> strengths) { this.strengths = strengths; }
    public void setWeaknesses(List<String> weaknesses) { this.weaknesses = weaknesses; }
    public void setImprovementSuggestions(List<ImprovementSuggestion> improvementSuggestions) { this.improvementSuggestions = improvementSuggestions; }
    public void setOverallSummary(String overallSummary) { this.overallSummary = overallSummary; }
    public void setConfig(Config config) { this.config = config; }
    public void setCompletionReason(String completionReason) { this.completionReason = completionReason; }
    public void setExchangeSummary(List<MockInterviewSession.Exchange> exchangeSummary) { this.exchangeSummary = exchangeSummary; }
}
