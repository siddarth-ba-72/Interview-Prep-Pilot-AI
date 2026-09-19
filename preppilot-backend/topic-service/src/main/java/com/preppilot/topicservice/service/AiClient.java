package com.preppilot.topicservice.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.preppilot.topicservice.dto.MockInterviewDtos.GenerateInterviewReportExchangeRequest;
import com.preppilot.topicservice.dto.MockInterviewDtos.GenerateInterviewReportRequest;
import com.preppilot.topicservice.dto.MockInterviewDtos.GenerateInterviewReportResponse;
import com.preppilot.topicservice.dto.MockInterviewDtos.NextTurnRequest;
import com.preppilot.topicservice.dto.MockInterviewDtos.NextTurnResponse;
import com.preppilot.topicservice.dto.MockInterviewDtos.PlanInterviewRequest;
import com.preppilot.topicservice.dto.MockInterviewDtos.PlanInterviewResponse;
import com.preppilot.topicservice.dto.TestDtos.GenerateTestQuestionsRequest;
import com.preppilot.topicservice.dto.TestDtos.GenerateTestQuestionsResponse;
import com.preppilot.topicservice.dto.TestDtos.EvaluateAnswersRequest;
import com.preppilot.topicservice.dto.TestDtos.EvaluateAnswersResponse;
import com.preppilot.topicservice.model.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import reactor.core.publisher.Flux;
import reactor.util.retry.Retry;

import java.time.Duration;
import java.util.List;
import java.util.Map;

@Service
public class AiClient {

    private static final Logger log = LoggerFactory.getLogger(AiClient.class);

    /** Ceiling for a synchronous AI call. Past this the caller falls back rather than hanging. */
    private static final Duration AI_CALL_TIMEOUT = Duration.ofSeconds(90);

    private final WebClient aiWebClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AiClient(WebClient aiWebClient) {
        this.aiWebClient = aiWebClient;
    }

    public record ChatMessagePayload(String role, String content) {}

    public static ChatMessagePayload toPayload(Message message) {
        return new ChatMessagePayload(message.getRole().name(), message.getContent());
    }

    /** Streams tokens for a Learn Mode response. Completes normally on [DONE],
     * errors with {@link AiStreamException} if the AI Service reports an error. */
    public Flux<String> streamLearn(String topicName, String mode, List<ChatMessagePayload> messages) {
        Map<String, Object> body = Map.of(
                "topicName", topicName,
                "mode", mode,
                "messages", messages
        );

        return aiWebClient.post()
                .uri("/ai/learn/stream")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(body)
                .retrieve()
                .onStatus(status -> !status.is2xxSuccessful(),
                        response -> response.bodyToMono(String.class)
                                .map(body2 -> new AiStreamException("AI Service returned " + response.statusCode())))
                .bodyToFlux(new ParameterizedTypeReference<ServerSentEvent<String>>() {})
                .handle((event, sink) -> {
                    String data = event.data();
                    if (data == null) {
                        return;
                    }
                    if ("[DONE]".equals(data.trim())) {
                        sink.complete();
                        return;
                    }
                    JsonNode node;
                    try {
                        node = objectMapper.readTree(data);
                    } catch (Exception e) {
                        sink.error(new AiStreamException("Malformed response from AI Service"));
                        return;
                    }
                    if (node.has("error")) {
                        sink.error(new AiStreamException(node.get("error").asText()));
                    } else if (node.has("token")) {
                        sink.next(node.get("token").asText());
                    }
                });
    }

    /** Generates test questions (MCQ and Subjective) for a topic.
     * If strengths/weaknesses from a previous attempt are provided, the AI will bias
     * question selection toward the weak areas (with light spaced-repetition on strengths). */
    public GenerateTestQuestionsResponse generateTestQuestions(String topicName, List<String> strengths, List<String> weaknesses) {
        GenerateTestQuestionsRequest body = new GenerateTestQuestionsRequest(topicName, strengths, weaknesses);

        return aiWebClient.post()
                .uri("/ai/test/generate")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(body)
                .retrieve()
                .onStatus(status -> !status.is2xxSuccessful(),
                        response -> response.bodyToMono(String.class)
                                .map(body2 -> new RuntimeException("AI Service returned " + response.statusCode())))
                .bodyToMono(GenerateTestQuestionsResponse.class)
                .block();
    }

    /** Evaluates test answers and provides per-question feedback. */
    public EvaluateAnswersResponse evaluateAnswers(String topicName, EvaluateAnswersRequest request) {
        return aiWebClient.post()
                .uri("/ai/test/evaluate")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .retrieve()
                .onStatus(status -> !status.is2xxSuccessful(),
                        response -> response.bodyToMono(String.class)
                                .map(body -> new RuntimeException("AI Service returned " + response.statusCode())))
                .bodyToMono(EvaluateAnswersResponse.class)
                .block();
    }

    public PlanInterviewResponse planInterview(String topicName, String experienceLevel, String difficulty, Integer durationMinutes) {
        PlanInterviewRequest body = new PlanInterviewRequest(topicName, experienceLevel, difficulty, durationMinutes);
        return postToAi("/ai/interview/plan", body, PlanInterviewResponse.class);
    }

    public NextTurnResponse nextInterviewTurn(NextTurnRequest request) {
        return postToAi("/ai/interview/next-turn", request, NextTurnResponse.class);
    }

    public GenerateInterviewReportResponse generateInterviewReport(String topicName, String experienceLevel,
                                                                     String difficulty,
                                                                     List<GenerateInterviewReportExchangeRequest> exchanges) {
        GenerateInterviewReportRequest body = new GenerateInterviewReportRequest(topicName, experienceLevel, difficulty, exchanges);
        return postToAi("/ai/interview/generate-report", body, GenerateInterviewReportResponse.class);
    }

    /**
     * Interview calls are synchronous and user-facing, so they get a hard ceiling: without one
     * a hung LLM call blocks the request thread indefinitely. Malformed-JSON retries live in the
     * AI Service (where the bad output can actually be fed back for repair); retrying here would
     * only multiply that latency, so we retry solely on connection-level failures.
     */
    private <T> T postToAi(String uri, Object body, Class<T> responseType) {
        return aiWebClient.post()
                .uri(uri)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(body)
                .retrieve()
                .onStatus(status -> !status.is2xxSuccessful(),
                        response -> response.bodyToMono(String.class)
                                .defaultIfEmpty("")
                                .map(errorBody -> new AiCallException(
                                        "AI Service returned " + response.statusCode() + " for " + uri + ": " + errorBody)))
                .bodyToMono(responseType)
                .timeout(AI_CALL_TIMEOUT)
                .retryWhen(Retry.max(1).filter(this::isConnectionFailure))
                .block();
    }

    private boolean isConnectionFailure(Throwable throwable) {
        boolean retryable = throwable instanceof WebClientRequestException;
        if (retryable) {
            log.warn("Could not reach the AI Service, retrying once: {}", throwable.getMessage());
        }
        return retryable;
    }

    /** Distinguishes an AI-side failure from a bug in our own request handling. */
    public static class AiCallException extends RuntimeException {
        public AiCallException(String message) {
            super(message);
        }
    }
}
