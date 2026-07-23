package com.preppilot.topicservice.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.preppilot.topicservice.model.Message;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import java.util.List;
import java.util.Map;

@Service
public class AiClient {

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
}
