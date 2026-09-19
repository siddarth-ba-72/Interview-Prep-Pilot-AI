package com.preppilot.topicservice.model;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

@Document(collection = "mock_interview_sessions")
public class MockInterviewSession {

    @Id
    private String id;

    @Indexed
    private String topicId;

    @Indexed
    private String userId;

    private Status status;

    private CompletionReason completionReason;

    private String experienceLevel;

    private String difficulty;

    private Integer durationMinutes;

    private Instant startedAt;

    private Instant deadlineAt;

    private List<String> themePlan;

    private Integer currentThemeIndex;

    private Integer currentFollowUpCount;

    private QuestionState currentQuestion;

    private List<Exchange> exchanges;

    @CreatedDate
    private Instant createdAt;

    private Instant completedAt;

    public enum Status { IN_PROGRESS, COMPLETED }

    public enum CompletionReason { USER_ENDED, TIME_EXPIRED, COMPLETED_NATURALLY }

    public enum Rating { STRONG, SATISFACTORY, WEAK }

    public static class QuestionState {
        public String question;
        public String theme;
        public boolean isFollowUp;

        public QuestionState() {}

        public QuestionState(String question, String theme, boolean isFollowUp) {
            this.question = question;
            this.theme = theme;
            this.isFollowUp = isFollowUp;
        }
    }

    public static class Exchange {
        public String question;
        public String theme;
        public boolean isFollowUp;
        public String userAnswer;
        public Rating rating;
        public Integer points;
        public String feedback;

        public Exchange() {}

        public Exchange(String question, String theme, boolean isFollowUp,
                        String userAnswer, Rating rating, Integer points, String feedback) {
            this.question = question;
            this.theme = theme;
            this.isFollowUp = isFollowUp;
            this.userAnswer = userAnswer;
            this.rating = rating;
            this.points = points;
            this.feedback = feedback;
        }
    }

    public MockInterviewSession() {}

    public MockInterviewSession(String topicId, String userId) {
        this.topicId = topicId;
        this.userId = userId;
        this.status = Status.IN_PROGRESS;
        this.currentThemeIndex = 0;
        this.currentFollowUpCount = 0;
    }

    public String getId() { return id; }
    public String getTopicId() { return topicId; }
    public String getUserId() { return userId; }
    public Status getStatus() { return status; }
    public CompletionReason getCompletionReason() { return completionReason; }
    public String getExperienceLevel() { return experienceLevel; }
    public String getDifficulty() { return difficulty; }
    public Integer getDurationMinutes() { return durationMinutes; }
    public Instant getStartedAt() { return startedAt; }
    public Instant getDeadlineAt() { return deadlineAt; }
    public List<String> getThemePlan() { return themePlan; }
    public Integer getCurrentThemeIndex() { return currentThemeIndex; }
    public Integer getCurrentFollowUpCount() { return currentFollowUpCount; }
    public QuestionState getCurrentQuestion() { return currentQuestion; }
    public List<Exchange> getExchanges() { return exchanges; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getCompletedAt() { return completedAt; }

    public void setStatus(Status status) { this.status = status; }
    public void setCompletionReason(CompletionReason completionReason) { this.completionReason = completionReason; }
    public void setExperienceLevel(String experienceLevel) { this.experienceLevel = experienceLevel; }
    public void setDifficulty(String difficulty) { this.difficulty = difficulty; }
    public void setDurationMinutes(Integer durationMinutes) { this.durationMinutes = durationMinutes; }
    public void setStartedAt(Instant startedAt) { this.startedAt = startedAt; }
    public void setDeadlineAt(Instant deadlineAt) { this.deadlineAt = deadlineAt; }
    public void setThemePlan(List<String> themePlan) { this.themePlan = themePlan; }
    public void setCurrentThemeIndex(Integer currentThemeIndex) { this.currentThemeIndex = currentThemeIndex; }
    public void setCurrentFollowUpCount(Integer currentFollowUpCount) { this.currentFollowUpCount = currentFollowUpCount; }
    public void setCurrentQuestion(QuestionState currentQuestion) { this.currentQuestion = currentQuestion; }
    public void setExchanges(List<Exchange> exchanges) { this.exchanges = exchanges; }
    public void setCompletedAt(Instant completedAt) { this.completedAt = completedAt; }
}
