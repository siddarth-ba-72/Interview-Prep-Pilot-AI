package com.preppilot.topicservice.model;

import com.preppilot.topicservice.config.UsageLimitProperties.Tier;

/** The AI-backed actions that count against a user's usage limits. */
public enum UsageAction {
    LEARN_MESSAGE("Learn message"),
    TEST("test"),
    MOCK_INTERVIEW("mock interview");

    private final String label;

    UsageAction(String label) {
        this.label = label;
    }

    /** Name used in the message shown when the limit is reached, e.g. "2 tests". */
    public String describe(int count) {
        return count + " " + label + (count == 1 ? "" : "s");
    }

    public int limitIn(Tier tier) {
        return switch (this) {
            case LEARN_MESSAGE -> tier.learnMessages();
            case TEST -> tier.tests();
            case MOCK_INTERVIEW -> tier.mockInterviews();
        };
    }
}
