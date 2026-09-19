package com.preppilot.topicservice.service;

import com.preppilot.topicservice.dto.MockInterviewDtos.*;
import com.preppilot.topicservice.exception.ApiException;
import com.preppilot.topicservice.exception.MockInterviewNotFoundException;
import com.preppilot.topicservice.exception.TopicNotFoundException;
import com.preppilot.topicservice.model.MockInterviewReport;
import com.preppilot.topicservice.model.MockInterviewSession;
import com.preppilot.topicservice.model.Topic;
import com.preppilot.topicservice.repository.MockInterviewReportRepository;
import com.preppilot.topicservice.repository.MockInterviewSessionRepository;
import com.preppilot.topicservice.repository.TopicRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class MockInterviewService {

    private static final Logger log = LoggerFactory.getLogger(MockInterviewService.class);

    /** Hard cap on follow-ups within one theme (Phase 4 spec section 1). Enforced here, not by the AI. */
    static final int MAX_FOLLOW_UPS_PER_THEME = 4;

    private static final Set<Integer> ALLOWED_DURATIONS = Set.of(30, 45, 60);
    private static final Set<String> ALLOWED_EXPERIENCE_LEVELS =
            Set.of("JUNIOR", "INTERMEDIATE", "SENIOR", "MASTER", "ADVANCED");
    private static final Set<String> ALLOWED_DIFFICULTIES = Set.of("EASY", "MEDIUM", "HARD");

    /** Rotated (rather than reused verbatim) so a run of AI failures doesn't show the
     * candidate the same sentence over and over - the symptom that reads as "stuck". */
    private static final List<String> FALLBACK_QUESTION_TEMPLATES = List.of(
            "Let's move on to %s. What are the most important things to get right there, and where do people usually go wrong?",
            "Thinking about %s: describe how you would approach it in a real project, and what you would watch out for.",
            "How would you explain %s to a teammate who has never worked with it, and what caveat would you flag for them?",
            "What trade-offs would you weigh when applying %s in a production system, and how would you decide?"
    );

    private final MockInterviewSessionRepository sessionRepository;
    private final MockInterviewReportRepository reportRepository;
    private final TopicRepository topicRepository;
    private final AiClient aiClient;

    public MockInterviewService(MockInterviewSessionRepository sessionRepository,
                                MockInterviewReportRepository reportRepository,
                                TopicRepository topicRepository,
                                AiClient aiClient) {
        this.sessionRepository = sessionRepository;
        this.reportRepository = reportRepository;
        this.topicRepository = topicRepository;
        this.aiClient = aiClient;
    }

    // ------------------------------------------------------------------ start / resume

    public MockInterviewStartResponse startInterview(String userId, String topicId, StartInterviewRequest request) {
        Topic topic = requireTopic(userId, topicId);
        String internalTopicId = topic.getId();

        Optional<MockInterviewSession> existing =
                sessionRepository.findByTopicIdAndUserIdAndStatus(internalTopicId, userId, MockInterviewSession.Status.IN_PROGRESS);
        if (existing.isPresent()) {
            MockInterviewSession session = existing.get();
            if (Instant.now().isBefore(session.getDeadlineAt())) {
                // Resume: the config in this request is deliberately ignored (spec section 5).
                return toStartResponse(session, true);
            }
            // Deadline already passed while the user was away - finalize it before starting a fresh one.
            finalizeSession(session, MockInterviewSession.CompletionReason.TIME_EXPIRED);
        }

        String experienceLevel = requireEnum(request.experienceLevel(), ALLOWED_EXPERIENCE_LEVELS, "experienceLevel");
        String difficulty = requireEnum(request.difficulty(), ALLOWED_DIFFICULTIES, "difficulty");
        if (request.durationMinutes() == null || !ALLOWED_DURATIONS.contains(request.durationMinutes())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "INVALID_INTERVIEW_CONFIG",
                    "durationMinutes must be one of 30, 45, or 60");
        }

        MockInterviewSession session = new MockInterviewSession(internalTopicId, userId);
        session.setExperienceLevel(experienceLevel);
        session.setDifficulty(difficulty);
        session.setDurationMinutes(request.durationMinutes());
        Instant now = Instant.now();
        session.setStartedAt(now);
        session.setDeadlineAt(now.plus(request.durationMinutes(), ChronoUnit.MINUTES));
        session.setThemePlan(planThemes(topic.getName(), session));
        session.setExchanges(new ArrayList<>());
        session.setCurrentQuestion(openingQuestion(topic.getName(), session));
        sessionRepository.save(session);

        return toStartResponse(session, false);
    }

    private List<String> planThemes(String topicName, MockInterviewSession session) {
        try {
            PlanInterviewResponse plan = aiClient.planInterview(
                    topicName, session.getExperienceLevel(), session.getDifficulty(), session.getDurationMinutes());
            List<String> themes = dedupeThemes(plan == null ? null : plan.themes());
            if (!themes.isEmpty()) {
                return themes;
            }
            log.warn("AI Service returned an empty theme plan for topic '{}'; using the default plan", topicName);
        } catch (Exception ex) {
            log.warn("Theme planning failed for topic '{}'; using the default plan", topicName, ex);
        }
        return defaultThemePlan(topicName, session.getDurationMinutes());
    }

    private MockInterviewSession.QuestionState openingQuestion(String topicName, MockInterviewSession session) {
        try {
            NextTurnResponse firstTurn = aiClient.nextInterviewTurn(new NextTurnRequest(
                    topicName,
                    session.getExperienceLevel(),
                    session.getDifficulty(),
                    session.getThemePlan(),
                    0,
                    0,
                    (long) session.getDurationMinutes() * 60L,
                    List.of(),
                    null,
                    null,
                    false,
                    MAX_FOLLOW_UPS_PER_THEME
            ));
            if (firstTurn != null && firstTurn.next() != null && hasText(firstTurn.next().question())) {
                return new MockInterviewSession.QuestionState(
                        firstTurn.next().question(),
                        firstText(firstTurn.next().theme(), session.getThemePlan().get(0)),
                        false);
            }
            log.warn("AI Service returned no opening question for topic '{}'; using the fallback opener", topicName);
        } catch (Exception ex) {
            log.warn("Opening question generation failed for topic '{}'; using the fallback opener", topicName, ex);
        }
        String firstTheme = session.getThemePlan().get(0);
        return new MockInterviewSession.QuestionState(
                "To get started, tell me about your experience with " + firstTheme
                        + " and how you have applied it in practice.",
                firstTheme,
                false);
    }

    // ------------------------------------------------------------------ read state

    public MockInterviewStateResponse getInterview(String userId, String topicId, String sessionId) {
        MockInterviewSession session = requireSession(userId, topicId, sessionId);

        if (session.getStatus() == MockInterviewSession.Status.IN_PROGRESS
                && Instant.now().isAfter(session.getDeadlineAt())) {
            finalizeSession(session, MockInterviewSession.CompletionReason.TIME_EXPIRED);
        }

        boolean isComplete = session.getStatus() == MockInterviewSession.Status.COMPLETED;
        return new MockInterviewStateResponse(
                isComplete,
                session.getId(),
                session.getStatus().name(),
                session.getDeadlineAt(),
                isComplete ? 0L : remainingSeconds(session.getDeadlineAt()),
                isComplete ? null : toQuestionResponse(session.getCurrentQuestion()),
                toThemeProgress(session),
                toExchangeResponses(session.getExchanges()),
                session.getCompletionReason() == null ? null : session.getCompletionReason().name(),
                toConfigResponse(session),
                isComplete ? ensureReport(session) : null
        );
    }

    // ------------------------------------------------------------------ answer a question

    public MockInterviewAnswerResponse answerInterview(String userId, String topicId, String sessionId, String answer) {
        MockInterviewSession session = requireSession(userId, topicId, sessionId);

        if (session.getStatus() != MockInterviewSession.Status.IN_PROGRESS) {
            throw new ApiException(HttpStatus.CONFLICT, "INTERVIEW_ALREADY_COMPLETED",
                    "This interview has already been completed.");
        }

        // ~5s grace absorbs network latency; beyond that the answer is not recorded (spec section 2).
        if (Instant.now().isAfter(session.getDeadlineAt().plusSeconds(5))) {
            finalizeSession(session, MockInterviewSession.CompletionReason.TIME_EXPIRED);
            return new MockInterviewAnswerResponse(null, null, toThemeProgress(session), null, 0L, true);
        }

        MockInterviewSession.QuestionState currentQuestion = session.getCurrentQuestion();
        if (currentQuestion == null) {
            throw new ApiException(HttpStatus.CONFLICT, "NO_ACTIVE_QUESTION",
                    "There is no question awaiting an answer on this interview.");
        }

        String topicName = requireTopic(userId, topicId).getName();
        String normalizedAnswer = answer == null ? "" : answer.trim();
        boolean isBlank = normalizedAnswer.isEmpty();

        int followUpsUsed = valueOrZero(session.getCurrentFollowUpCount());
        boolean mustAdvanceTheme = isBlank || followUpsUsed >= MAX_FOLLOW_UPS_PER_THEME;

        NextTurnResponse aiResponse = requestNextTurn(session, topicName, currentQuestion, normalizedAnswer, mustAdvanceTheme);

        MockInterviewSession.Rating rating;
        String feedback;
        boolean advanceTheme;
        MockInterviewSession.QuestionState nextQuestionState;

        if (isBlank) {
            // Scoring for a blank answer is deterministic (spec section 6) - we never let the AI
            // grade an empty box - but we still use its next question so the interview stays sharp.
            rating = MockInterviewSession.Rating.WEAK;
            feedback = "No answer was submitted for this question, so it scores zero.";
            advanceTheme = true;
            nextQuestionState = aiNextQuestion(aiResponse)
                    .orElseGet(() -> fallbackNextQuestion(session, topicName));
        } else if (aiResponse == null || aiResponse.evaluation() == null || aiResponse.next() == null
                || !hasText(aiResponse.next().question())) {
            log.warn("Falling back to a deterministic turn for interview {} - the AI Service returned no usable turn", sessionId);
            rating = MockInterviewSession.Rating.SATISFACTORY;
            feedback = "We couldn't score this answer automatically, but it has been recorded.";
            advanceTheme = true;
            nextQuestionState = fallbackNextQuestion(session, topicName);
        } else {
            rating = parseRating(aiResponse.evaluation().rating());
            feedback = firstText(aiResponse.evaluation().feedback(), "This answer was recorded.");
            advanceTheme = aiResponse.next().advanceTheme() || mustAdvanceTheme;
            nextQuestionState = new MockInterviewSession.QuestionState(
                    aiResponse.next().question(),
                    firstText(aiResponse.next().theme(), currentQuestion.theme),
                    aiResponse.next().isFollowUp() && !advanceTheme);
        }

        MockInterviewSession.Exchange exchange = new MockInterviewSession.Exchange(
                currentQuestion.question,
                currentQuestion.theme,
                currentQuestion.isFollowUp,
                normalizedAnswer,
                rating,
                pointsForRating(isBlank ? null : rating),
                feedback);

        List<MockInterviewSession.Exchange> exchanges =
                session.getExchanges() == null ? new ArrayList<>() : new ArrayList<>(session.getExchanges());
        exchanges.add(exchange);
        session.setExchanges(exchanges);

        // Relabel the question with the theme the session actually landed on, so the UI never
        // shows a question tagged with a theme the interview has already moved past.
        nextQuestionState.theme = applyThemeTransition(session, advanceTheme, nextQuestionState.theme, topicName);
        session.setCurrentQuestion(nextQuestionState);
        sessionRepository.save(session);

        return new MockInterviewAnswerResponse(
                new MockInterviewEvaluationResponse(rating.name(), feedback, exchange.points),
                toQuestionResponse(nextQuestionState),
                toThemeProgress(session),
                toExchangeResponse(exchanges.size(), exchange),
                remainingSeconds(session.getDeadlineAt()),
                false
        );
    }

    private NextTurnResponse requestNextTurn(MockInterviewSession session, String topicName,
                                             MockInterviewSession.QuestionState currentQuestion,
                                             String answer, boolean mustAdvanceTheme) {
        try {
            return aiClient.nextInterviewTurn(new NextTurnRequest(
                    topicName,
                    session.getExperienceLevel(),
                    session.getDifficulty(),
                    session.getThemePlan(),
                    valueOrZero(session.getCurrentThemeIndex()),
                    valueOrZero(session.getCurrentFollowUpCount()),
                    remainingSeconds(session.getDeadlineAt()),
                    toNextTurnExchanges(session.getExchanges()),
                    answer,
                    new NextTurnQuestionContext(currentQuestion.question, currentQuestion.theme, currentQuestion.isFollowUp),
                    mustAdvanceTheme,
                    MAX_FOLLOW_UPS_PER_THEME
            ));
        } catch (Exception ex) {
            log.warn("next-turn call failed for interview {}", session.getId(), ex);
            return null;
        }
    }

    private Optional<MockInterviewSession.QuestionState> aiNextQuestion(NextTurnResponse response) {
        if (response == null || response.next() == null || !hasText(response.next().question())) {
            return Optional.empty();
        }
        return Optional.of(new MockInterviewSession.QuestionState(
                response.next().question(), response.next().theme(), false));
    }

    /**
     * Moves the session onto the theme the next question actually belongs to and returns that
     * theme's canonical label. Growing the plan when the AI invents an adjacent theme keeps the
     * progress indicator honest ("Theme 7 of ~6" was the old symptom), and never moving the
     * index backwards keeps the follow-up cap from being undone by an AI that wants to stay put.
     */
    private String applyThemeTransition(MockInterviewSession session, boolean advanceTheme, String nextTheme, String topicName) {
        List<String> plan = session.getThemePlan() == null ? new ArrayList<>() : new ArrayList<>(session.getThemePlan());
        int themeIndex = valueOrZero(session.getCurrentThemeIndex());

        if (advanceTheme) {
            int target = themeIndex + 1;
            int matching = indexOfIgnoreCase(plan, nextTheme);
            if (matching >= target) {
                themeIndex = matching;              // the AI skipped ahead in the plan - follow it
            } else if (target >= plan.size()) {
                // Plan exhausted: adopt the adjacent theme the AI invented so the plan keeps growing.
                plan.add(matching >= 0 || !hasText(nextTheme) ? "More on " + topicName : nextTheme);
                themeIndex = plan.size() - 1;
            } else {
                themeIndex = target;                // normal step down the plan
            }
            session.setCurrentFollowUpCount(0);
        } else {
            session.setCurrentFollowUpCount(valueOrZero(session.getCurrentFollowUpCount()) + 1);
        }

        themeIndex = Math.min(themeIndex, Math.max(0, plan.size() - 1));
        session.setThemePlan(plan);
        session.setCurrentThemeIndex(themeIndex);
        return plan.isEmpty() ? firstText(nextTheme, topicName) : plan.get(themeIndex);
    }

    /** Deterministic next question used when the AI call failed. Rotates through templates
     * so consecutive failures don't produce the same sentence twice. */
    private MockInterviewSession.QuestionState fallbackNextQuestion(MockInterviewSession session, String topicName) {
        List<String> plan = session.getThemePlan();
        int nextThemeIndex = valueOrZero(session.getCurrentThemeIndex()) + 1;
        String theme = (plan != null && nextThemeIndex < plan.size())
                ? plan.get(nextThemeIndex)
                : "advanced " + topicName + " topics";
        int rotation = session.getExchanges() == null ? 0 : session.getExchanges().size();
        String template = FALLBACK_QUESTION_TEMPLATES.get(rotation % FALLBACK_QUESTION_TEMPLATES.size());
        return new MockInterviewSession.QuestionState(String.format(template, theme), theme, false);
    }

    // ------------------------------------------------------------------ finalize / report

    public MockInterviewReportResponse endInterview(String userId, String topicId, String sessionId) {
        MockInterviewSession session = requireSession(userId, topicId, sessionId);

        if (session.getStatus() == MockInterviewSession.Status.IN_PROGRESS) {
            boolean expired = Instant.now().isAfter(session.getDeadlineAt());
            finalizeSession(session, expired
                    ? MockInterviewSession.CompletionReason.TIME_EXPIRED
                    : MockInterviewSession.CompletionReason.USER_ENDED);
        }
        return ensureReport(session);
    }

    public MockInterviewReportResponse getInterviewReport(String userId, String topicId, String sessionId) {
        MockInterviewSession session = requireSession(userId, topicId, sessionId);
        if (session.getStatus() != MockInterviewSession.Status.COMPLETED) {
            throw new ApiException(HttpStatus.CONFLICT, "INTERVIEW_NOT_COMPLETED",
                    "This interview is still in progress - no report has been generated yet.");
        }
        return ensureReport(session);
    }

    /** Newest first, so the caller can number attempts by position. */
    public List<MockInterviewSummaryResponse> listInterviews(String userId, String topicId) {
        Topic topic = requireTopic(userId, topicId);
        List<MockInterviewSession> sessions = sessionRepository.findByTopicIdAndUserId(topic.getId(), userId).stream()
                .sorted((a, b) -> {
                    Instant left = a.getCreatedAt();
                    Instant right = b.getCreatedAt();
                    if (left == null && right == null) return 0;
                    if (left == null) return 1;
                    if (right == null) return -1;
                    return right.compareTo(left);
                })
                .toList();

        // Batched so the list costs two queries regardless of how many interviews the user has run.
        Map<String, MockInterviewReport> reportsBySessionId =
                reportRepository.findByMockInterviewSessionIdIn(sessions.stream().map(MockInterviewSession::getId).toList())
                        .stream()
                        .collect(Collectors.toMap(MockInterviewReport::getMockInterviewSessionId, report -> report, (a, b) -> a));

        return sessions.stream()
                .map(session -> {
                    MockInterviewReport report = reportsBySessionId.get(session.getId());
                    return new MockInterviewSummaryResponse(
                            session.getId(),
                            session.getStatus().name(),
                            session.getCompletionReason() == null ? null : session.getCompletionReason().name(),
                            toConfigResponse(session),
                            report == null ? null : report.getScore(),
                            report == null ? null : report.getMaxScore(),
                            report == null ? null : report.getPassed(),
                            session.getExchanges() == null ? 0 : session.getExchanges().size(),
                            session.getCreatedAt(),
                            session.getCompletedAt()
                    );
                })
                .toList();
    }

    private void finalizeSession(MockInterviewSession session, MockInterviewSession.CompletionReason reason) {
        if (session.getStatus() == MockInterviewSession.Status.COMPLETED) {
            return;
        }
        session.setStatus(MockInterviewSession.Status.COMPLETED);
        session.setCompletionReason(reason);
        session.setCompletedAt(Instant.now());
        session.setCurrentQuestion(null);
        sessionRepository.save(session);
    }

    /**
     * Returns the report for a completed session, generating it on first request. Report
     * generation is the one step that can legitimately fail transiently, so it is kept
     * separate from finalization: a failed AI call leaves the session completed and the
     * report is regenerated the next time it is fetched.
     */
    private MockInterviewReportResponse ensureReport(MockInterviewSession session) {
        Optional<MockInterviewReport> existing = reportRepository.findByMockInterviewSessionId(session.getId());
        if (existing.isPresent()) {
            return toReportResponse(existing.get());
        }

        String topicName = topicRepository.findByIdAndUserId(session.getTopicId(), session.getUserId())
                .map(Topic::getName)
                .orElse("this topic");

        GenerateInterviewReportResponse aiReport;
        try {
            aiReport = aiClient.generateInterviewReport(
                    topicName,
                    session.getExperienceLevel(),
                    session.getDifficulty(),
                    toGenerateReportExchanges(session.getExchanges()));
        } catch (Exception ex) {
            log.warn("Report generation failed for interview {}; storing a minimal report", session.getId(), ex);
            aiReport = null;
        }

        MockInterviewReport report = new MockInterviewReport(session.getId(), session.getTopicId(), session.getUserId());
        report.setScore(calculateScore(session.getExchanges()));
        report.setPassed(report.getScore() >= report.getPassThreshold());
        report.setStrengths(aiReport == null || aiReport.strengths() == null ? List.of() : aiReport.strengths());
        report.setWeaknesses(aiReport == null || aiReport.weaknesses() == null ? List.of() : aiReport.weaknesses());
        report.setImprovementSuggestions(aiReport == null || aiReport.improvementSuggestions() == null
                ? List.of()
                : aiReport.improvementSuggestions().stream()
                        .map(s -> new MockInterviewReport.ImprovementSuggestion(s.question(), s.userAnswer(), s.theme(), s.betterAnswer()))
                        .toList());
        report.setOverallSummary(aiReport == null || !hasText(aiReport.overallSummary())
                ? defaultSummary(session)
                : aiReport.overallSummary());
        report.setConfig(new MockInterviewReport.Config(
                session.getExperienceLevel(), session.getDifficulty(), session.getDurationMinutes()));
        report.setCompletionReason(session.getCompletionReason() == null ? null : session.getCompletionReason().name());
        report.setExchangeSummary(session.getExchanges() == null ? List.of() : session.getExchanges());
        reportRepository.save(report);

        return toReportResponse(report);
    }

    private String defaultSummary(MockInterviewSession session) {
        int answered = session.getExchanges() == null ? 0 : session.getExchanges().size();
        if (answered == 0) {
            return "This interview ended before any questions were answered, so there is nothing to assess yet. "
                    + "Start a new interview when you're ready.";
        }
        return "You answered " + answered + " question" + (answered == 1 ? "" : "s")
                + ". A detailed written assessment could not be generated this time, but your per-question "
                + "ratings and feedback below are complete.";
    }

    int calculateScore(List<MockInterviewSession.Exchange> exchanges) {
        if (exchanges == null || exchanges.isEmpty()) {
            return 0;
        }
        int total = exchanges.stream().mapToInt(exchange -> exchange.points == null ? 0 : exchange.points).sum();
        return Math.round((float) total / exchanges.size());
    }

    // ------------------------------------------------------------------ helpers

    private Topic requireTopic(String userId, String topicId) {
        return topicRepository.findByPublicIdAndUserId(topicId, userId)
                .orElseThrow(() -> new TopicNotFoundException(topicId));
    }

    private MockInterviewSession requireSession(String userId, String topicId, String sessionId) {
        Topic topic = requireTopic(userId, topicId);
        return sessionRepository.findById(sessionId)
                .filter(s -> s.getUserId().equals(userId) && s.getTopicId().equals(topic.getId()))
                .orElseThrow(() -> new MockInterviewNotFoundException(sessionId));
    }

    private String requireEnum(String value, Set<String> allowed, String field) {
        String normalized = value == null ? "" : value.trim().toUpperCase(Locale.ROOT);
        if (!allowed.contains(normalized)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "INVALID_INTERVIEW_CONFIG",
                    field + " must be one of " + allowed);
        }
        return normalized;
    }

    private MockInterviewSession.Rating parseRating(String rating) {
        if (rating == null) {
            return MockInterviewSession.Rating.SATISFACTORY;
        }
        try {
            return MockInterviewSession.Rating.valueOf(rating.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            return MockInterviewSession.Rating.SATISFACTORY;
        }
    }

    private Integer pointsForRating(MockInterviewSession.Rating rating) {
        if (rating == null) {
            return 0;  // blank / timed-out answer
        }
        return switch (rating) {
            case STRONG -> 100;
            case SATISFACTORY -> 60;
            case WEAK -> 20;
        };
    }

    private List<String> dedupeThemes(List<String> themes) {
        if (themes == null) {
            return List.of();
        }
        Set<String> seen = new LinkedHashSet<>();
        List<String> result = new ArrayList<>();
        for (String theme : themes) {
            if (!hasText(theme)) {
                continue;
            }
            String trimmed = theme.trim();
            if (seen.add(trimmed.toLowerCase(Locale.ROOT))) {
                result.add(trimmed);
            }
        }
        return result;
    }

    private List<String> defaultThemePlan(String topicName, Integer durationMinutes) {
        List<String> plan = new ArrayList<>(List.of(
                topicName + " fundamentals",
                topicName + " in practice",
                "Design and trade-offs in " + topicName,
                "Debugging and testing " + topicName));
        if (durationMinutes != null && durationMinutes >= 45) {
            plan.add("Performance and scaling with " + topicName);
            plan.add("Real-world " + topicName + " scenarios");
        }
        if (durationMinutes != null && durationMinutes >= 60) {
            plan.add("Advanced " + topicName + " internals");
            plan.add("Ecosystem and tooling around " + topicName);
        }
        return plan;
    }

    private int indexOfIgnoreCase(List<String> values, String candidate) {
        if (!hasText(candidate)) {
            return -1;
        }
        for (int i = 0; i < values.size(); i++) {
            if (values.get(i) != null && values.get(i).equalsIgnoreCase(candidate.trim())) {
                return i;
            }
        }
        return -1;
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private static String firstText(String preferred, String fallback) {
        return hasText(preferred) ? preferred : fallback;
    }

    private static int valueOrZero(Integer value) {
        return value == null ? 0 : value;
    }

    private Long remainingSeconds(Instant deadlineAt) {
        if (deadlineAt == null) {
            return 0L;
        }
        return Math.max(0L, ChronoUnit.SECONDS.between(Instant.now(), deadlineAt));
    }

    // ------------------------------------------------------------------ response mapping

    private MockInterviewStartResponse toStartResponse(MockInterviewSession session, boolean resumed) {
        return new MockInterviewStartResponse(
                session.getId(),
                session.getDeadlineAt(),
                remainingSeconds(session.getDeadlineAt()),
                toQuestionResponse(session.getCurrentQuestion()),
                toThemeProgress(session),
                session.getStatus().name(),
                toConfigResponse(session),
                toExchangeResponses(session.getExchanges()),
                resumed
        );
    }

    private MockInterviewConfigResponse toConfigResponse(MockInterviewSession session) {
        return new MockInterviewConfigResponse(
                session.getExperienceLevel(), session.getDifficulty(), session.getDurationMinutes());
    }

    private ThemeProgressResponse toThemeProgress(MockInterviewSession session) {
        int total = session.getThemePlan() == null ? 0 : session.getThemePlan().size();
        int current = Math.min(valueOrZero(session.getCurrentThemeIndex()) + 1, Math.max(total, 1));
        return new ThemeProgressResponse(current, total);
    }

    private MockInterviewQuestionResponse toQuestionResponse(MockInterviewSession.QuestionState question) {
        if (question == null) {
            return null;
        }
        return new MockInterviewQuestionResponse(question.question, question.theme, question.isFollowUp);
    }

    private MockInterviewExchangeResponse toExchangeResponse(int index, MockInterviewSession.Exchange exchange) {
        return new MockInterviewExchangeResponse(
                index,
                exchange.question,
                exchange.theme,
                exchange.isFollowUp,
                exchange.userAnswer,
                exchange.rating == null ? null : exchange.rating.name(),
                exchange.points,
                exchange.feedback);
    }

    private List<MockInterviewExchangeResponse> toExchangeResponses(List<MockInterviewSession.Exchange> exchanges) {
        if (exchanges == null) {
            return List.of();
        }
        List<MockInterviewExchangeResponse> response = new ArrayList<>();
        for (int i = 0; i < exchanges.size(); i++) {
            response.add(toExchangeResponse(i + 1, exchanges.get(i)));
        }
        return response;
    }

    private List<NextTurnExchangeRequest> toNextTurnExchanges(List<MockInterviewSession.Exchange> exchanges) {
        if (exchanges == null) {
            return List.of();
        }
        return exchanges.stream()
                .map(exchange -> new NextTurnExchangeRequest(
                        exchange.question,
                        exchange.userAnswer,
                        exchange.theme,
                        exchange.isFollowUp,
                        exchange.rating == null ? null : exchange.rating.name()))
                .toList();
    }

    private List<GenerateInterviewReportExchangeRequest> toGenerateReportExchanges(List<MockInterviewSession.Exchange> exchanges) {
        if (exchanges == null) {
            return List.of();
        }
        return exchanges.stream()
                .map(exchange -> new GenerateInterviewReportExchangeRequest(
                        exchange.question,
                        exchange.userAnswer,
                        exchange.theme,
                        exchange.rating == null ? null : exchange.rating.name()))
                .toList();
    }

    private MockInterviewReportResponse toReportResponse(MockInterviewReport report) {
        return new MockInterviewReportResponse(
                report.getMockInterviewSessionId(),
                report.getScore(),
                report.getMaxScore(),
                report.getPassThreshold(),
                Boolean.TRUE.equals(report.getPassed()),
                report.getStrengths() == null ? List.of() : report.getStrengths(),
                report.getWeaknesses() == null ? List.of() : report.getWeaknesses(),
                report.getImprovementSuggestions() == null ? List.of() : report.getImprovementSuggestions().stream()
                        .map(s -> new MockInterviewImprovementSuggestionResponse(s.question, s.userAnswer, s.theme, s.betterAnswer))
                        .toList(),
                report.getOverallSummary(),
                report.getConfig() == null ? null : new MockInterviewConfigResponse(
                        report.getConfig().experienceLevel, report.getConfig().difficulty, report.getConfig().durationMinutes),
                report.getCompletionReason(),
                report.getExchangeSummary() == null ? List.of() : toExchangeResponses(report.getExchangeSummary()),
                report.getCreatedAt()
        );
    }
}
