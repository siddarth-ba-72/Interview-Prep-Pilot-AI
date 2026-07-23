package com.preppilot.topicservice.model;

import java.time.Instant;

public class Message {

    public enum Role { USER, AI }

    private Role role;
    private String content;
    private Instant timestamp;

    public Message() {}

    public Message(Role role, String content, Instant timestamp) {
        this.role = role;
        this.content = content;
        this.timestamp = timestamp;
    }

    public Role getRole() { return role; }
    public String getContent() { return content; }
    public Instant getTimestamp() { return timestamp; }
}
