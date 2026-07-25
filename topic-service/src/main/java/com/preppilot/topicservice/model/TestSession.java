package com.preppilot.topicservice.model;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

@Document(collection = "test_sessions")
public class TestSession {

    @Id
    private String id;

    @Indexed
    private String topicId;

    @Indexed
    private String userId;

    private Status status;

    private List<Question> questions;

    private List<Answer> answers;

    private Integer rawScore;  // null until COMPLETED; range -60 to +60

    @CreatedDate
    private Instant createdAt;

    private Instant completedAt;

    public enum Status {
        IN_PROGRESS, COMPLETED
    }

    public static class Question {
        public String questionId;
        public Section section;
        public String text;
        public List<String> options;  // MCQ only; exactly 4 options
        public String correctOption;  // stored server-side ONLY, never sent to frontend
        public String modelAnswer;    // SUBJECTIVE only; never sent to frontend

        public Question() {}

        public Question(String questionId, Section section, String text, List<String> options,
                       String correctOption, String modelAnswer) {
            this.questionId = questionId;
            this.section = section;
            this.text = text;
            this.options = options;
            this.correctOption = correctOption;
            this.modelAnswer = modelAnswer;
        }
    }

    public enum Section {
        MCQ, SUBJECTIVE
    }

    public static class Answer {
        public String questionId;
        public String userAnswer;        // null if not answered
        public Boolean isCorrect;        // set after evaluation
        public String evaluation;        // AI feedback
        public Integer pointsAwarded;    // actual points

        public Answer() {}

        public Answer(String questionId, String userAnswer, Boolean isCorrect,
                     String evaluation, Integer pointsAwarded) {
            this.questionId = questionId;
            this.userAnswer = userAnswer;
            this.isCorrect = isCorrect;
            this.evaluation = evaluation;
            this.pointsAwarded = pointsAwarded;
        }
    }

    // Constructors
    public TestSession() {}

    public TestSession(String topicId, String userId) {
        this.topicId = topicId;
        this.userId = userId;
        this.status = Status.IN_PROGRESS;
    }

    // Getters
    public String getId() { return id; }
    public String getTopicId() { return topicId; }
    public String getUserId() { return userId; }
    public Status getStatus() { return status; }
    public List<Question> getQuestions() { return questions; }
    public List<Answer> getAnswers() { return answers; }
    public Integer getRawScore() { return rawScore; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getCompletedAt() { return completedAt; }

    // Setters
    public void setStatus(Status status) { this.status = status; }
    public void setQuestions(List<Question> questions) { this.questions = questions; }
    public void setAnswers(List<Answer> answers) { this.answers = answers; }
    public void setRawScore(Integer rawScore) { this.rawScore = rawScore; }
    public void setCompletedAt(Instant completedAt) { this.completedAt = completedAt; }
}
