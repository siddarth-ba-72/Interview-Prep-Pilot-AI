package com.preppilot.topicservice.model;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

@Document(collection = "test_reports")
public class TestReport {

    @Id
    private String id;

    @Indexed
    private String testSessionId;

    @Indexed
    private String topicId;

    @Indexed
    private String userId;

    private Integer rawScore;          // sum of pointsAwarded; range -60 to +60

    private Integer maxScore;          // always 60

    private Integer passThreshold;     // always 36

    private Boolean passed;            // rawScore >= passThreshold

    private Double avgScoreAtTime;     // snapshot of topic's avgScore after this test

    private List<String> strengths;    // topic areas answered well

    private List<String> weaknesses;   // topic areas needing improvement

    private List<QuestionResult> questionSummary;

    private Integer attemptNumber;     // 1-based sequence of test attempts for this topic+user

    private Boolean basedOnPreviousAttempt;  // true if question generation was biased by a prior report

    @CreatedDate
    private Instant createdAt;

    public static class QuestionResult {
        public String questionId;
        public String section;         // "MCQ" or "SUBJECTIVE"
        public String questionText;
        public String userAnswer;      // nullable
        public String correctAnswer;   // revealed only after submission
        public Boolean isCorrect;
        public String evaluation;
        public Integer pointsAwarded;

        public QuestionResult() {}

        public QuestionResult(String questionId, String section, String questionText,
                             String userAnswer, String correctAnswer, Boolean isCorrect,
                             String evaluation, Integer pointsAwarded) {
            this.questionId = questionId;
            this.section = section;
            this.questionText = questionText;
            this.userAnswer = userAnswer;
            this.correctAnswer = correctAnswer;
            this.isCorrect = isCorrect;
            this.evaluation = evaluation;
            this.pointsAwarded = pointsAwarded;
        }
    }

    // Constructors
    public TestReport() {}

    public TestReport(String testSessionId, String topicId, String userId) {
        this.testSessionId = testSessionId;
        this.topicId = topicId;
        this.userId = userId;
        this.maxScore = 60;
        this.passThreshold = 36;
    }

    // Getters
    public String getId() { return id; }
    public String getTestSessionId() { return testSessionId; }
    public String getTopicId() { return topicId; }
    public String getUserId() { return userId; }
    public Integer getRawScore() { return rawScore; }
    public Integer getMaxScore() { return maxScore; }
    public Integer getPassThreshold() { return passThreshold; }
    public Boolean getPassed() { return passed; }
    public Double getAvgScoreAtTime() { return avgScoreAtTime; }
    public List<String> getStrengths() { return strengths; }
    public List<String> getWeaknesses() { return weaknesses; }
    public List<QuestionResult> getQuestionSummary() { return questionSummary; }
    public Integer getAttemptNumber() { return attemptNumber; }
    public Boolean getBasedOnPreviousAttempt() { return basedOnPreviousAttempt; }
    public Instant getCreatedAt() { return createdAt; }

    // Setters
    public void setRawScore(Integer rawScore) { this.rawScore = rawScore; }
    public void setPassed(Boolean passed) { this.passed = passed; }
    public void setAvgScoreAtTime(Double avgScoreAtTime) { this.avgScoreAtTime = avgScoreAtTime; }
    public void setStrengths(List<String> strengths) { this.strengths = strengths; }
    public void setWeaknesses(List<String> weaknesses) { this.weaknesses = weaknesses; }
    public void setQuestionSummary(List<QuestionResult> questionSummary) { this.questionSummary = questionSummary; }
    public void setAttemptNumber(Integer attemptNumber) { this.attemptNumber = attemptNumber; }
    public void setBasedOnPreviousAttempt(Boolean basedOnPreviousAttempt) { this.basedOnPreviousAttempt = basedOnPreviousAttempt; }
}
