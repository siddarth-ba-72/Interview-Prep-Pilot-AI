package com.preppilot.topicservice.model;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.CompoundIndexes;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Document(collection = "chat_sessions")
@CompoundIndexes({
    @CompoundIndex(name = "user_topic_unique", def = "{'userId': 1, 'topicId': 1}", unique = true)
})
public class ChatSession {

    @Id
    private String id;

    private String userId;

    private String topicId;

    private List<Message> messages = new ArrayList<>();

    @CreatedDate
    private Instant createdAt;

    @LastModifiedDate
    private Instant updatedAt;

    public ChatSession() {}

    public ChatSession(String userId, String topicId) {
        this.userId = userId;
        this.topicId = topicId;
    }

    public String getId() { return id; }
    public String getUserId() { return userId; }
    public String getTopicId() { return topicId; }
    public List<Message> getMessages() { return messages; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public void addMessage(Message message) {
        this.messages.add(message);
    }
}
