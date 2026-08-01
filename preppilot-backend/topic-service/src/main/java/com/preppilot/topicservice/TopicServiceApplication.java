package com.preppilot.topicservice;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.mongodb.config.EnableMongoAuditing;

@SpringBootApplication
@EnableMongoAuditing
public class TopicServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(TopicServiceApplication.class, args);
    }
}
