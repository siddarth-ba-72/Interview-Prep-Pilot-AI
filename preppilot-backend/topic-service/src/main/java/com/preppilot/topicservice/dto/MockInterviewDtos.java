package com.preppilot.topicservice.dto;

import java.time.Instant;
import java.util.List;

public class MockInterviewDtos {

    public record StartInterviewRequest(
            String experienceLevel,
            String difficulty,
            Integer durationMinutes
    ) {}

    public record AnswerInterviewRequest(
            String answer
    ) {}

    /** A row in the interview history list. `score`, `maxScore` and `passed` are null until the
     * report exists - reports are generated lazily on first fetch, so a session can be COMPLETED
     * with no report yet. `answeredCount` comes off the session, so it is always available. */
    public record MockInterviewSummaryResponse(
            String sessionId,
            String status,
            String completionReason,
            MockInterviewConfigResponse config,
            Integer score,
            Integer maxScore,
            Boolean passed,
            Integer answeredCount,
            Instant createdAt,
            Instant completedAt
    ) {}

    public record MockInterviewStartResponse(
            String sessionId,
            Instant deadlineAt,
            Long remainingSeconds,
            MockInterviewQuestionResponse currentQuestion,
            ThemeProgressResponse themeProgress,
            String status,
            MockInterviewConfigResponse config,
            List<MockInterviewExchangeResponse> exchanges,
            boolean resumed
    ) {}

    public record MockInterviewStateResponse(
            boolean isComplete,
            String sessionId,
            String status,
            Instant deadlineAt,
            Long remainingSeconds,
            MockInterviewQuestionResponse currentQuestion,
            ThemeProgressResponse themeProgress,
            List<MockInterviewExchangeResponse> exchanges,
            String completionReason,
            MockInterviewConfigResponse config,
            MockInterviewReportResponse report
    ) {}

    public record MockInterviewAnswerResponse(
            MockInterviewEvaluationResponse evaluation,
            MockInterviewQuestionResponse nextQuestion,
            ThemeProgressResponse themeProgress,
            MockInterviewExchangeResponse exchange,
            Long remainingSeconds,
            boolean isComplete
    ) {}

    public record MockInterviewEvaluationResponse(
            String rating,
            String feedback,
            Integer points
    ) {}

    public record MockInterviewQuestionResponse(
            String question,
            String theme,
            boolean isFollowUp
    ) {}

    public record ThemeProgressResponse(
            Integer currentThemeIndex,
            Integer totalThemes
    ) {}

    public record MockInterviewExchangeResponse(
            Integer index,
            String question,
            String theme,
            boolean isFollowUp,
            String userAnswer,
            String rating,
            Integer points,
            String feedback
    ) {}

    public record MockInterviewReportResponse(
            String sessionId,
            Integer score,
            Integer maxScore,
            Integer passThreshold,
            boolean passed,
            List<String> strengths,
            List<String> weaknesses,
            List<MockInterviewImprovementSuggestionResponse> improvementSuggestions,
            String overallSummary,
            MockInterviewConfigResponse config,
            String completionReason,
            List<MockInterviewExchangeResponse> exchangeSummary,
            Instant createdAt
    ) {}

    public record MockInterviewImprovementSuggestionResponse(
            String question,
            String userAnswer,
            String theme,
            String betterAnswer
    ) {}

    public record MockInterviewConfigResponse(
            String experienceLevel,
            String difficulty,
            Integer durationMinutes
    ) {}

    public record PlanInterviewRequest(
            String topicName,
            String experienceLevel,
            String difficulty,
            Integer durationMinutes
    ) {}

    public record PlanInterviewResponse(
            List<String> themes
    ) {}

    public record NextTurnRequest(
            String topicName,
            String experienceLevel,
            String difficulty,
            List<String> themePlan,
            Integer currentThemeIndex,
            Integer currentFollowUpCount,
            Long remainingSeconds,
            List<NextTurnExchangeRequest> priorExchanges,
            String lastAnswer,
            NextTurnQuestionContext currentQuestion,
            boolean mustAdvanceTheme,
            Integer maxFollowUps
    ) {}

    /** The question `lastAnswer` responds to. Sent so the AI grades the right question
     * instead of inferring it from the transcript. */
    public record NextTurnQuestionContext(
            String question,
            String theme,
            boolean isFollowUp
    ) {}

    public record NextTurnExchangeRequest(
            String question,
            String userAnswer,
            String theme,
            boolean isFollowUp,
            String rating
    ) {}

    public record NextTurnResponse(
            MockInterviewEvaluationResponse evaluation,
            MockInterviewNextQuestionResponse next
    ) {}

    public record MockInterviewNextQuestionResponse(
            String question,
            String theme,
            boolean isFollowUp,
            boolean advanceTheme
    ) {}

    public record GenerateInterviewReportRequest(
            String topicName,
            String experienceLevel,
            String difficulty,
            List<GenerateInterviewReportExchangeRequest> exchanges
    ) {}

    public record GenerateInterviewReportExchangeRequest(
            String question,
            String userAnswer,
            String theme,
            String rating
    ) {}

    public record GenerateInterviewReportResponse(
            List<String> strengths,
            List<String> weaknesses,
            String overallSummary,
            List<MockInterviewImprovementSuggestionResponse> improvementSuggestions
    ) {}
}
