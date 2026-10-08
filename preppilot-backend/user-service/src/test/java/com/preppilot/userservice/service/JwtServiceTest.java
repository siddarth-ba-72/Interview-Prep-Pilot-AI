package com.preppilot.userservice.service;

import com.preppilot.userservice.model.AuthProvider;
import com.preppilot.userservice.model.User;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class JwtServiceTest {

    private final JwtService jwtService = new JwtService("test-secret-that-is-at-least-32-bytes-long!!", 1_800_000);

    @Test
    void aUserWithoutARoleGetsTheUserRoleClaim() {
        User user = new User("u1@example.com", "hash", AuthProvider.LOCAL, null, "U1");

        String token = jwtService.generateAccessToken(user);

        assertEquals("USER", jwtService.parseAccessToken(token).get("role", String.class));
    }
}
