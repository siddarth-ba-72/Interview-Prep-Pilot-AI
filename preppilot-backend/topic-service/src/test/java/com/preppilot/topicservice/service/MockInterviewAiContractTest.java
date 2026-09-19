package com.preppilot.topicservice.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.preppilot.topicservice.dto.MockInterviewDtos.MockInterviewQuestionResponse;
import com.preppilot.topicservice.dto.MockInterviewDtos.NextTurnExchangeRequest;
import com.preppilot.topicservice.dto.MockInterviewDtos.NextTurnQuestionContext;
import com.preppilot.topicservice.dto.MockInterviewDtos.NextTurnRequest;
import com.preppilot.topicservice.dto.MockInterviewDtos.NextTurnResponse;
import com.preppilot.topicservice.dto.MockInterviewDtos.GenerateInterviewReportResponse;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Pins the JSON field names exchanged with the (Python) AI Service. Jackson's record naming
 * and Pydantic's aliases have to agree exactly - a silent mismatch on a boolean like
 * `advanceTheme` would deserialize to false and quietly break theme progression.
 */
class MockInterviewAiContractTest {

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void nextTurnRequestSerializesTheFieldNamesTheAiServiceExpects() throws Exception {
        NextTurnRequest request = new NextTurnRequest(
                "Spring Boot", "SENIOR", "MEDIUM", List.of("Beans", "Security"), 1, 2, 540L,
                List.of(new NextTurnExchangeRequest("Q1", "A1", "Beans", false, "STRONG")),
                "my answer",
                new NextTurnQuestionContext("Explain bean scopes.", "Beans", true),
                true, 4);

        JsonNode json = mapper.readTree(mapper.writeValueAsString(request));

        assertTrue(json.has("topicName"));
        assertTrue(json.has("experienceLevel"));
        assertTrue(json.has("themePlan"));
        assertTrue(json.has("currentThemeIndex"));
        assertTrue(json.has("currentFollowUpCount"));
        assertTrue(json.has("remainingSeconds"));
        assertTrue(json.has("priorExchanges"));
        assertTrue(json.has("lastAnswer"));
        assertTrue(json.has("maxFollowUps"));

        assertTrue(json.has("mustAdvanceTheme"), "boolean must not be renamed by Jackson");
        assertTrue(json.get("mustAdvanceTheme").asBoolean());

        JsonNode currentQuestion = json.get("currentQuestion");
        assertTrue(currentQuestion != null && !currentQuestion.isNull(),
                "the graded question must reach the AI service");
        assertEquals("Explain bean scopes.", currentQuestion.get("question").asText());
        assertTrue(currentQuestion.has("isFollowUp"));

        JsonNode exchange = json.get("priorExchanges").get(0);
        assertTrue(exchange.has("isFollowUp"));
        assertEquals("STRONG", exchange.get("rating").asText(),
                "prior ratings let the AI calibrate the next question");
    }

    @Test
    void nextTurnResponseDeserializesTheAiServicePayload() throws Exception {
        String payload = """
                {
                  "evaluation": { "rating": "STRONG", "feedback": "Clear and specific." },
                  "next": {
                    "question": "How would you secure an actuator endpoint?",
                    "theme": "Security",
                    "isFollowUp": false,
                    "advanceTheme": true
                  }
                }
                """;

        NextTurnResponse response = mapper.readValue(payload, NextTurnResponse.class);

        assertEquals("STRONG", response.evaluation().rating());
        assertEquals("Clear and specific.", response.evaluation().feedback());
        assertEquals("Security", response.next().theme());
        assertTrue(response.next().advanceTheme(), "advanceTheme must survive the round trip");
        assertFalse(response.next().isFollowUp());
    }

    @Test
    void reportResponseDeserializesCamelCaseSuggestions() throws Exception {
        String payload = """
                {
                  "strengths": ["Beans"],
                  "weaknesses": ["Security"],
                  "overallSummary": "You were strong on fundamentals.",
                  "improvementSuggestions": [
                    { "question": "Q", "userAnswer": "A", "theme": "Security", "betterAnswer": "Better" }
                  ]
                }
                """;

        GenerateInterviewReportResponse response = mapper.readValue(payload, GenerateInterviewReportResponse.class);

        assertEquals("You were strong on fundamentals.", response.overallSummary());
        assertEquals("Better", response.improvementSuggestions().get(0).betterAnswer());
        assertEquals("A", response.improvementSuggestions().get(0).userAnswer());
    }

    @Test
    void questionResponseKeepsTheIsFollowUpNameTheFrontendReads() throws Exception {
        JsonNode json = mapper.readTree(mapper.writeValueAsString(
                new MockInterviewQuestionResponse("Q", "Beans", true)));

        assertTrue(json.has("isFollowUp"), "the frontend reads currentQuestion.isFollowUp");
        assertTrue(json.get("isFollowUp").asBoolean());
    }
}
