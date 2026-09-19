package com.preppilot.topicservice.service;

import com.preppilot.topicservice.dto.MockInterviewDtos.MockInterviewEvaluationResponse;
import com.preppilot.topicservice.dto.MockInterviewDtos.MockInterviewNextQuestionResponse;
import com.preppilot.topicservice.dto.MockInterviewDtos.NextTurnRequest;
import com.preppilot.topicservice.dto.MockInterviewDtos.NextTurnResponse;
import com.preppilot.topicservice.dto.MockInterviewDtos.PlanInterviewResponse;
import com.preppilot.topicservice.dto.MockInterviewDtos.StartInterviewRequest;
import com.preppilot.topicservice.exception.ApiException;
import com.preppilot.topicservice.model.MockInterviewSession;
import com.preppilot.topicservice.model.Topic;
import com.preppilot.topicservice.repository.MockInterviewReportRepository;
import com.preppilot.topicservice.repository.MockInterviewSessionRepository;
import com.preppilot.topicservice.repository.TopicRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MockInterviewServiceTest {

    private MockInterviewSessionRepository sessionRepository;
    private MockInterviewReportRepository reportRepository;
    private TopicRepository topicRepository;
    private AiClient aiClient;
    private MockInterviewService service;

    @BeforeEach
    void setUp() {
        sessionRepository = mock(MockInterviewSessionRepository.class);
        reportRepository = mock(MockInterviewReportRepository.class);
        topicRepository = mock(TopicRepository.class);
        aiClient = mock(AiClient.class);
        service = new MockInterviewService(sessionRepository, reportRepository, topicRepository, aiClient);

        when(topicRepository.findByIdAndUserId("topic-1", "user-1")).thenReturn(Optional.of(new Topic("user-1", "Spring Boot")));
        when(sessionRepository.save(any(MockInterviewSession.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(reportRepository.findByMockInterviewSessionId(anyString())).thenReturn(Optional.empty());
    }

    private MockInterviewSession inProgressSession(String question, String theme) {
        MockInterviewSession session = new MockInterviewSession("topic-1", "user-1");
        session.setExperienceLevel("SENIOR");
        session.setDifficulty("MEDIUM");
        session.setDurationMinutes(30);
        session.setStartedAt(Instant.now());
        session.setDeadlineAt(Instant.now().plus(20, ChronoUnit.MINUTES));
        session.setThemePlan(new ArrayList<>(List.of("Core IoC & Beans", "Auto-configuration")));
        session.setCurrentQuestion(new MockInterviewSession.QuestionState(question, theme, false));
        session.setExchanges(new ArrayList<>());
        when(sessionRepository.findById(any())).thenReturn(Optional.of(session));
        return session;
    }

    private NextTurnResponse turn(String rating, String question, String theme, boolean followUp, boolean advance) {
        return new NextTurnResponse(
                new MockInterviewEvaluationResponse(rating, "feedback", null),
                new MockInterviewNextQuestionResponse(question, theme, followUp, advance));
    }

    @Test
    void calculateScoreUsesMeanOfExchangePoints() {
        int score = service.calculateScore(List.of(
                new MockInterviewSession.Exchange("q1", "theme-1", false, "answer-1", MockInterviewSession.Rating.STRONG, 100, "Great"),
                new MockInterviewSession.Exchange("q2", "theme-1", true, "answer-2", MockInterviewSession.Rating.SATISFACTORY, 60, "Okay"),
                new MockInterviewSession.Exchange("q3", "theme-2", false, "answer-3", MockInterviewSession.Rating.WEAK, 20, "Needs work")
        ));

        assertEquals(60, score);
    }

    @Test
    void startInterviewFallsBackWhenAiServiceIsUnavailable() {
        when(sessionRepository.findByTopicIdAndUserIdAndStatus(anyString(), anyString(), any())).thenReturn(Optional.empty());
        when(aiClient.planInterview(anyString(), anyString(), anyString(), anyInt()))
                .thenThrow(new RuntimeException("AI service unavailable"));

        var response = service.startInterview("user-1", "topic-1", new StartInterviewRequest("JUNIOR", "MEDIUM", 30));

        assertNotNull(response.currentQuestion());
        assertFalse(response.resumed());
        assertEquals(1, response.themeProgress().currentThemeIndex());
        assertEquals(4, response.themeProgress().totalThemes());
    }

    @Test
    void startInterviewRejectsAnUnknownExperienceLevel() {
        when(sessionRepository.findByTopicIdAndUserIdAndStatus(anyString(), anyString(), any())).thenReturn(Optional.empty());

        assertThrows(ApiException.class,
                () -> service.startInterview("user-1", "topic-1", new StartInterviewRequest("WIZARD", "MEDIUM", 30)));
    }

    @Test
    void startInterviewRejectsAnUnsupportedDuration() {
        when(sessionRepository.findByTopicIdAndUserIdAndStatus(anyString(), anyString(), any())).thenReturn(Optional.empty());

        assertThrows(ApiException.class,
                () -> service.startInterview("user-1", "topic-1", new StartInterviewRequest("SENIOR", "HARD", 25)));
    }

    @Test
    void startInterviewResumesAnInProgressSessionInsteadOfCreatingANewOne() {
        MockInterviewSession existing = inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        when(sessionRepository.findByTopicIdAndUserIdAndStatus(anyString(), anyString(), any())).thenReturn(Optional.of(existing));

        var response = service.startInterview("user-1", "topic-1", new StartInterviewRequest("JUNIOR", "EASY", 60));

        assertTrue(response.resumed());
        assertEquals("Explain bean scopes.", response.currentQuestion().question());
        // Config from the request is ignored on resume - the original session config wins.
        assertEquals("SENIOR", response.config().experienceLevel());
        assertEquals(30, response.config().durationMinutes());
    }

    @Test
    void answerSendsTheQuestionBeingGradedToTheAiService() {
        inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        when(aiClient.nextInterviewTurn(any())).thenReturn(
                turn("STRONG", "How would singleton scope break with stateful beans?", "Core IoC & Beans", true, false));

        service.answerInterview("user-1", "topic-1", "session-1", "Singleton, prototype, request, session.");

        ArgumentCaptor<NextTurnRequest> captor = ArgumentCaptor.forClass(NextTurnRequest.class);
        verify(aiClient).nextInterviewTurn(captor.capture());
        NextTurnRequest sent = captor.getValue();

        assertNotNull(sent.currentQuestion(), "the graded question must be sent to the AI service");
        assertEquals("Explain bean scopes.", sent.currentQuestion().question());
        assertEquals("Singleton, prototype, request, session.", sent.lastAnswer());
        assertFalse(sent.mustAdvanceTheme());
    }

    @Test
    void strongAnswerFollowUpStaysOnTheSameThemeAndIncrementsTheBudget() {
        MockInterviewSession session = inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        when(aiClient.nextInterviewTurn(any())).thenReturn(
                turn("STRONG", "Where does prototype scope surprise people?", "Core IoC & Beans", true, false));

        var response = service.answerInterview("user-1", "topic-1", "session-1", "A thorough answer.");

        assertEquals("STRONG", response.evaluation().rating());
        assertEquals(100, response.evaluation().points());
        assertEquals(0, session.getCurrentThemeIndex());
        assertEquals(1, session.getCurrentFollowUpCount());
        assertEquals(1, response.themeProgress().currentThemeIndex());
    }

    @Test
    void followUpCapForcesTheThemeToAdvanceEvenIfTheAiWantsToStay() {
        MockInterviewSession session = inProgressSession("Yet another follow-up.", "Core IoC & Beans");
        session.setCurrentFollowUpCount(MockInterviewService.MAX_FOLLOW_UPS_PER_THEME);
        // The AI tries to keep drilling the same theme.
        when(aiClient.nextInterviewTurn(any())).thenReturn(
                turn("STRONG", "One more on beans?", "Core IoC & Beans", true, false));

        service.answerInterview("user-1", "topic-1", "session-1", "Another good answer.");

        ArgumentCaptor<NextTurnRequest> captor = ArgumentCaptor.forClass(NextTurnRequest.class);
        verify(aiClient).nextInterviewTurn(captor.capture());
        assertTrue(captor.getValue().mustAdvanceTheme(), "the cap must be signalled to the AI service");

        assertEquals(1, session.getCurrentThemeIndex(), "the theme must advance regardless of the AI response");
        assertEquals(0, session.getCurrentFollowUpCount());
    }

    @Test
    void blankAnswerScoresZeroWithoutTrustingTheAiRating() {
        MockInterviewSession session = inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        when(aiClient.nextInterviewTurn(any())).thenReturn(
                turn("STRONG", "Let's talk auto-configuration.", "Auto-configuration", false, true));

        var response = service.answerInterview("user-1", "topic-1", "session-1", "   ");

        assertEquals("WEAK", response.evaluation().rating());
        assertEquals(0, response.evaluation().points());
        assertEquals(0, session.getExchanges().get(0).points);
        assertEquals(1, session.getCurrentThemeIndex());
    }

    @Test
    void themePlanGrowsWhenTheAiInventsAnAdjacentThemeAfterThePlanIsExhausted() {
        MockInterviewSession session = inProgressSession("Last planned question.", "Auto-configuration");
        session.setCurrentThemeIndex(1);  // on the final planned theme
        when(aiClient.nextInterviewTurn(any())).thenReturn(
                turn("SATISFACTORY", "How do you approach observability?", "Actuator & Observability", false, true));

        var response = service.answerInterview("user-1", "topic-1", "session-1", "A partial answer.");

        assertEquals(3, session.getThemePlan().size(), "an invented theme should extend the plan");
        assertEquals("Actuator & Observability", session.getThemePlan().get(2));
        assertEquals(3, response.themeProgress().currentThemeIndex());
        assertEquals(3, response.themeProgress().totalThemes(), "progress must never exceed its own total");
    }

    @Test
    void answerAfterTheDeadlineFinalizesInsteadOfRecordingTheAnswer() {
        MockInterviewSession session = inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        session.setDeadlineAt(Instant.now().minusSeconds(60));

        var response = service.answerInterview("user-1", "topic-1", "session-1", "Too late.");

        assertTrue(response.isComplete());
        assertEquals(MockInterviewSession.Status.COMPLETED, session.getStatus());
        assertEquals(MockInterviewSession.CompletionReason.TIME_EXPIRED, session.getCompletionReason());
        assertTrue(session.getExchanges().isEmpty(), "a late answer must not be recorded");
    }

    @Test
    void resumingAnExpiredSessionFinalizesItAndReturnsTheReport() {
        MockInterviewSession session = inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        session.setDeadlineAt(Instant.now().minusSeconds(30));
        session.setExchanges(new ArrayList<>(List.of(
                new MockInterviewSession.Exchange("q1", "Core IoC & Beans", false, "a1", MockInterviewSession.Rating.STRONG, 100, "Good"))));
        when(aiClient.generateInterviewReport(anyString(), anyString(), anyString(), any()))
                .thenThrow(new RuntimeException("AI service unavailable"));

        var state = service.getInterview("user-1", "topic-1", "session-1");

        assertTrue(state.isComplete());
        assertEquals("TIME_EXPIRED", state.completionReason());
        assertNotNull(state.report(), "an expired session must still produce a report");
        assertEquals(100, state.report().score());
        assertTrue(state.report().passed());
    }

    @Test
    void endInterviewWithNoAnswersScoresZeroAndFails() {
        inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        when(aiClient.generateInterviewReport(anyString(), anyString(), anyString(), any()))
                .thenReturn(new com.preppilot.topicservice.dto.MockInterviewDtos.GenerateInterviewReportResponse(
                        List.of(), List.of(), "You ended early.", List.of()));

        var report = service.endInterview("user-1", "topic-1", "session-1");

        assertEquals(0, report.score());
        assertFalse(report.passed());
        assertEquals(75, report.passThreshold());
    }

    @Test
    void interviewSurvivesAnAiFailureWithARealNextQuestion() {
        MockInterviewSession session = inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        when(aiClient.nextInterviewTurn(any())).thenThrow(new RuntimeException("AI service unavailable"));

        var response = service.answerInterview("user-1", "topic-1", "session-1", "Some answer.");

        assertFalse(response.isComplete(), "an AI hiccup must not end the interview");
        assertNotNull(response.nextQuestion());
        assertEquals(1, session.getExchanges().size());
        assertEquals("SATISFACTORY", response.evaluation().rating());
    }

    @Test
    void consecutiveAiFailuresDoNotRepeatTheSameFallbackQuestion() {
        MockInterviewSession session = inProgressSession("Explain bean scopes.", "Core IoC & Beans");
        when(aiClient.nextInterviewTurn(any())).thenThrow(new RuntimeException("AI service unavailable"));

        String first = service.answerInterview("user-1", "topic-1", "session-1", "answer one").nextQuestion().question();
        session.setCurrentQuestion(new MockInterviewSession.QuestionState(first, "theme", false));
        String second = service.answerInterview("user-1", "topic-1", "session-1", "answer two").nextQuestion().question();

        assertFalse(first.equals(second), "repeating the same fallback is what makes the interview feel stuck");
    }
}
