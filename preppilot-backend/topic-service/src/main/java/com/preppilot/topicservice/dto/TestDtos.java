package com.preppilot.topicservice.dto;

import java.time.Instant;
import java.util.List;

public class TestDtos {

    // Test Session DTOs
    public record TestSessionStartResponse(
        String sessionId,
        List<TestQuestionResponse> questions,
        Integer attemptNumber,
        Boolean basedOnPreviousAttempt
    ) {}

    public record TestQuestionResponse(
        String questionId,
        String section,      // "MCQ" or "SUBJECTIVE"
        String text,
        List<String> options // MCQ only; null for subjective
    ) {}

    public record SubmitAnswerRequest(
        String questionId,
        String userAnswer    // null if not answered
    ) {}

    public record SubmitTestRequest(
        List<SubmitAnswerRequest> answers
    ) {}

    public record TestReportResponse(
        String testSessionId,
        Integer rawScore,
        Integer maxScore,
        Integer passThreshold,
        Boolean passed,
        Double avgScoreAtTime,
        List<String> strengths,
        List<String> weaknesses,
        List<QuestionResultResponse> questionSummary,
        Integer attemptNumber,
        Boolean basedOnPreviousAttempt,
        Instant createdAt
    ) {}

    public record QuestionResultResponse(
        String questionId,
        String section,
        String questionText,
        String userAnswer,
        String correctAnswer,
        Boolean isCorrect,
        String evaluation,
        Integer pointsAwarded
    ) {}

    public record TestSessionListItemResponse(
        String sessionId,
        Instant completedAt,
        Integer rawScore,
        Integer attemptNumber
    ) {}

    // AI Request/Response DTOs
    public record GenerateTestQuestionsRequest(
        String topicName,
        List<String> strengths,   // nullable; from previous attempt's report
        List<String> weaknesses   // nullable; from previous attempt's report
    ) {}

    public record GenerateTestQuestionsResponse(
        List<QuestionWithAnswersResponse> questions
    ) {}

    public record QuestionWithAnswersResponse(
        String questionId,
        String section,
        String text,
        List<String> options,
        String correctOption,
        String modelAnswer
    ) {}

    public record EvaluateAnswersRequest(
        String topicName,
        List<AnswerForEvaluationRequest> answers
    ) {}

    public record AnswerForEvaluationRequest(
        String questionId,
        String section,
        String question,
        String correctAnswer,
        String userAnswer
    ) {}

    public record EvaluateAnswersResponse(
        List<QuestionEvaluationResponse> perQuestion,
        List<String> strengths,
        List<String> weaknesses
    ) {}

    public record QuestionEvaluationResponse(
        String questionId,
        Boolean isCorrect,
        String evaluation
    ) {}
}
