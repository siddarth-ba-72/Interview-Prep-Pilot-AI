package com.preppilot.userservice.config;

import com.preppilot.userservice.service.JwtService;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

class JwtAuthFilterTest {

    private static final String SECRET = "test-secret-that-is-at-least-32-bytes-long!!";

    private final JwtAuthFilter filter = new JwtAuthFilter(new JwtService(SECRET, 1_800_000));

    @Test
    void userEndpointsRejectARequestWithoutAToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/users/me");
        request.addHeader("X-User-Id", "someone-else");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertEquals(401, response.getStatus());
        assertNull(chain.getRequest(), "the request must not reach the controller");
    }

    @Test
    void userEndpointsRejectAnExpiredToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("PUT", "/api/v1/users/me/profile");
        request.addHeader("Authorization", "Bearer " + token(SECRET, -60_000));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertEquals(401, response.getStatus());
        assertNull(chain.getRequest());
    }

    @Test
    void theUserIdComesFromTheTokenNotFromTheCaller() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/users/me");
        request.addHeader("Authorization", "Bearer " + token(SECRET, 60_000));
        request.addHeader("X-User-Id", "someone-else");
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, new MockHttpServletResponse(), chain);

        HttpServletRequest passed = (HttpServletRequest) chain.getRequest();
        assertNotNull(passed);
        assertEquals("u1", passed.getHeader("X-User-Id"));
    }

    @Test
    void authEndpointsStayOpen() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v1/auth/login");
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, new MockHttpServletResponse(), chain);

        assertNotNull(chain.getRequest());
    }

    private static String token(String secret, long expiresInMs) {
        Date now = new Date();
        return Jwts.builder()
                .claims(Map.of("userId", "u1", "email", "u1@example.com"))
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expiresInMs))
                .signWith(Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }
}
