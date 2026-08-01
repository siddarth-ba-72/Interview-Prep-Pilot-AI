package com.preppilot.topicservice.service;

import com.preppilot.topicservice.dto.TestDtos.*;
import com.preppilot.topicservice.exception.TopicNotFoundException;
import com.preppilot.topicservice.model.TestReport;
import com.preppilot.topicservice.model.TestSession;
import com.preppilot.topicservice.model.Topic;
import com.preppilot.topicservice.repository.TestReportRepository;
import com.preppilot.topicservice.repository.TestSessionRepository;
import com.preppilot.topicservice.repository.TopicRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class TestService {

    private final TestSessionRepository testSessionRepository;
    private final TestReportRepository testReportRepository;
    private final TopicRepository topicRepository;
    private final AiClient aiClient;

    public TestService(TestSessionRepository testSessionRepository,
                      TestReportRepository testReportRepository,
                      TopicRepository topicRepository,
                      AiClient aiClient) {
        this.testSessionRepository = testSessionRepository;
        this.testReportRepository = testReportRepository;
        this.topicRepository = topicRepository;
        this.aiClient = aiClient;
    }

    /**
     * Starts a new test session for a topic.
     * Returns existing IN_PROGRESS test if one exists (idempotent).
     */
    public TestSessionStartResponse startTest(String userId, String topicId) {
        Topic topic = topicRepository.findByIdAndUserId(topicId, userId)
                .orElseThrow(() -> new TopicNotFoundException(topicId));

        // Check if test is already in progress
        Optional<TestSession> existingSession = testSessionRepository
                .findByTopicIdAndUserIdAndStatus(topicId, userId, TestSession.Status.IN_PROGRESS);

        if (existingSession.isPresent()) {
            return toTestSessionStartResponse(existingSession.get(), false);
        }

        // Compute attempt number: count of all prior sessions (in-progress or completed) + 1
        int attemptNumber = testSessionRepository.findByTopicIdAndUserId(topicId, userId).size() + 1;

        // Look up the most recent completed report to bias question generation toward weak areas
        Optional<TestReport> previousReport = testReportRepository
                .findTopByTopicIdAndUserIdOrderByAttemptNumberDesc(topicId, userId);

        List<String> strengths = previousReport.map(TestReport::getStrengths).orElse(null);
        List<String> weaknesses = previousReport.map(TestReport::getWeaknesses).orElse(null);
        boolean basedOnPreviousAttempt = previousReport.isPresent()
                && weaknesses != null && !weaknesses.isEmpty();

        // Generate questions from AI
        GenerateTestQuestionsResponse aiResponse = aiClient.generateTestQuestions(topic.getName(), strengths, weaknesses);

        // Create and save test session with questions
        TestSession session = new TestSession(topicId, userId);
        session.setAttemptNumber(attemptNumber);
        session.setBasedOnPreviousAttempt(basedOnPreviousAttempt);
        List<TestSession.Question> questions = aiResponse.questions().stream()
                .map(q -> new TestSession.Question(
                        q.questionId(),
                        TestSession.Section.valueOf(q.section()),
                        q.text(),
                        q.options(),
                        q.correctOption(),
                        q.modelAnswer()
                ))
                .toList();

        session.setQuestions(questions);
        TestSession saved = testSessionRepository.save(session);

        return toTestSessionStartResponse(saved, basedOnPreviousAttempt);
    }

    /**
     * Retrieves an in-progress or completed test session.
     * Strips sensitive fields (correctOption, modelAnswer) if test is not yet completed.
     */
    public TestSessionStartResponse getTest(String userId, String topicId, String testId) {
        TestSession session = testSessionRepository.findById(testId)
                .filter(s -> s.getUserId().equals(userId) && s.getTopicId().equals(topicId))
                .orElseThrow(() -> new RuntimeException("Test not found"));

        return toTestSessionStartResponse(session, false);
    }

    /**
     * Submits answers, evaluates them, generates report, and updates aggregate score.
     */
    public TestReportResponse submitTest(String userId, String topicId, String testId, SubmitTestRequest request) {
        TestSession session = testSessionRepository.findById(testId)
                .filter(s -> s.getUserId().equals(userId) && s.getTopicId().equals(topicId))
                .orElseThrow(() -> new RuntimeException("Test not found"));

        if (!session.getStatus().equals(TestSession.Status.IN_PROGRESS)) {
            throw new RuntimeException("Test is already completed");
        }

        Topic topic = topicRepository.findByIdAndUserId(topicId, userId)
                .orElseThrow(() -> new TopicNotFoundException(topicId));

        // Build evaluation request
        List<AnswerForEvaluationRequest> answersForEval = new ArrayList<>();
        Map<String, String> userAnswersMap = new HashMap<>();
        for (SubmitAnswerRequest a : request.answers()) {
            userAnswersMap.put(a.questionId(), a.userAnswer());
        }

        for (TestSession.Question q : session.getQuestions()) {
            String correctAnswer = q.section == TestSession.Section.MCQ ? q.correctOption : q.modelAnswer;
            String userAnswer = userAnswersMap.getOrDefault(q.questionId, null);

            answersForEval.add(new AnswerForEvaluationRequest(
                    q.questionId,
                    q.section.name(),
                    q.text,
                    correctAnswer,
                    userAnswer
            ));
        }

        // Call AI to evaluate
        EvaluateAnswersResponse aiEvaluation = aiClient.evaluateAnswers(
                topic.getName(),
                new EvaluateAnswersRequest(topic.getName(), answersForEval)
        );

        // Build answers with scoring
        List<TestSession.Answer> answers = new ArrayList<>();
        int rawScore = 0;

        // Build map for lookup - filter out null questionIds
        Map<String, QuestionEvaluationResponse> evalMap = new HashMap<>();
        for (QuestionEvaluationResponse eval : aiEvaluation.perQuestion()) {
            if (eval.questionId() != null && !eval.questionId().isEmpty()) {
                evalMap.put(eval.questionId(), eval);
            }
        }

        // If no valid questionIds, fall back to position-based matching
        boolean usePositionMatching = evalMap.isEmpty() && !aiEvaluation.perQuestion().isEmpty();

        for (int i = 0; i < session.getQuestions().size(); i++) {
            TestSession.Question q = session.getQuestions().get(i);
            String userAnswer = userAnswersMap.getOrDefault(q.questionId, null);
            
            // Get evaluation by questionId, or by position if questionId lookup fails
            QuestionEvaluationResponse eval = evalMap.get(q.questionId);
            if (eval == null && usePositionMatching && i < aiEvaluation.perQuestion().size()) {
                eval = aiEvaluation.perQuestion().get(i);
            }
            
            if (eval == null) {
                throw new RuntimeException("No evaluation found for question: " + q.questionId);
            }

            int points = calculatePoints(q.section, userAnswer, eval.isCorrect());
            rawScore += points;

            answers.add(new TestSession.Answer(
                    q.questionId,
                    userAnswer,
                    userAnswer == null ? false : eval.isCorrect(),
                    userAnswer == null ? "Not answered." : eval.evaluation(),
                    points
            ));
        }

        // Update session with answers and mark as completed
        session.setAnswers(answers);
        session.setRawScore(rawScore);
        session.setStatus(TestSession.Status.COMPLETED);
        session.setCompletedAt(Instant.now());
        testSessionRepository.save(session);

        // Create report
        TestReport report = new TestReport(testId, topicId, userId);
        report.setRawScore(rawScore);
        report.setPassed(rawScore >= 36);
        report.setStrengths(aiEvaluation.strengths());
        report.setWeaknesses(aiEvaluation.weaknesses());
        report.setAttemptNumber(session.getAttemptNumber());
        report.setBasedOnPreviousAttempt(session.getBasedOnPreviousAttempt() != null && session.getBasedOnPreviousAttempt());

        // Build question summary
        List<TestReport.QuestionResult> questionResults = new ArrayList<>();
        for (TestSession.Question q : session.getQuestions()) {
            TestSession.Answer answer = answers.stream()
                    .filter(a -> a.questionId.equals(q.questionId))
                    .findFirst()
                    .orElseThrow();

            String correctAnswer = q.section == TestSession.Section.MCQ ? q.correctOption : q.modelAnswer;

            questionResults.add(new TestReport.QuestionResult(
                    q.questionId,
                    q.section.name(),
                    q.text,
                    answer.userAnswer,
                    correctAnswer,
                    answer.isCorrect,
                    answer.evaluation,
                    answer.pointsAwarded
            ));
        }
        report.setQuestionSummary(questionResults);

        // Update topic's aggregate score atomically
        synchronized (topicRepository) {
            int currentCount = topic.getTestCount() != null ? topic.getTestCount() : 0;
            topic.setTestCount(currentCount + 1);

            if (topic.getAvgScore() == null) {
                topic.setAvgScore((double) rawScore);
            } else {
                double newAvg = ((topic.getAvgScore() * (topic.getTestCount() - 1)) + rawScore) / topic.getTestCount();
                topic.setAvgScore(newAvg);
            }

            topicRepository.save(topic);
        }

        report.setAvgScoreAtTime(topic.getAvgScore());
        testReportRepository.save(report);

        return toTestReportResponse(report);
    }

    /**
     * Retrieves a test report.
     */
    public TestReportResponse getTestReport(String userId, String topicId, String testId) {
        TestSession session = testSessionRepository.findById(testId)
                .filter(s -> s.getUserId().equals(userId) && s.getTopicId().equals(topicId))
                .orElseThrow(() -> new RuntimeException("Test not found"));

        TestReport report = testReportRepository.findByTestSessionId(testId)
                .orElseThrow(() -> new RuntimeException("Report not found"));

        return toTestReportResponse(report);
    }

    /**
     * Lists completed test sessions for a topic.
     */
    public List<TestSessionListItemResponse> listTestSessions(String userId, String topicId) {
        return testReportRepository.findByTopicIdAndUserId(topicId, userId).stream()
                .map(report -> new TestSessionListItemResponse(
                        report.getTestSessionId(),
                        testSessionRepository.findById(report.getTestSessionId())
                                .map(TestSession::getCompletedAt)
                                .orElse(null),
                        report.getRawScore(),
                        report.getAttemptNumber()
                ))
                .collect(Collectors.toList());
    }

    private int calculatePoints(TestSession.Section section, String userAnswer, Boolean isCorrect) {
        if (userAnswer == null) {
            return 0; // Not answered
        }
        if (section == TestSession.Section.MCQ) {
            return isCorrect ? 1 : -1;
        } else { // SUBJECTIVE
            return isCorrect ? 5 : -5;
        }
    }

    private TestSessionStartResponse toTestSessionStartResponse(TestSession session, boolean basedOnPreviousAttempt) {
        List<TestQuestionResponse> questions = session.getQuestions().stream()
                .map(q -> new TestQuestionResponse(
                        q.questionId,
                        q.section.name(),
                        q.text,
                        q.options
                ))
                .toList();

        return new TestSessionStartResponse(
                session.getId(),
                questions,
                session.getAttemptNumber(),
                session.getBasedOnPreviousAttempt() != null ? session.getBasedOnPreviousAttempt() : basedOnPreviousAttempt
        );
    }

    private TestReportResponse toTestReportResponse(TestReport report) {
        List<QuestionResultResponse> questionResults = report.getQuestionSummary().stream()
                .map(qr -> new QuestionResultResponse(
                        qr.questionId,
                        qr.section,
                        qr.questionText,
                        qr.userAnswer,
                        qr.correctAnswer,
                        qr.isCorrect,
                        qr.evaluation,
                        qr.pointsAwarded
                ))
                .toList();

        return new TestReportResponse(
                report.getTestSessionId(),
                report.getRawScore(),
                report.getMaxScore(),
                report.getPassThreshold(),
                report.getPassed(),
                report.getAvgScoreAtTime(),
                report.getStrengths(),
                report.getWeaknesses(),
                questionResults,
                report.getAttemptNumber(),
                report.getBasedOnPreviousAttempt(),
                report.getCreatedAt()
        );
    }
}
