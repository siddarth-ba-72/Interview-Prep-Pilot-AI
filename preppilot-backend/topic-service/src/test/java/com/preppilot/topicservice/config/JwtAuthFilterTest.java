package com.preppilot.topicservice.config;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

class JwtAuthFilterTest {

    private static final String SECRET = "test-secret-that-is-at-least-32-bytes-long!!";

    private final JwtAuthFilter filter = new JwtAuthFilter(SECRET);

    @Test
    void rejectsARequestWithoutAToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/topics");
        request.addHeader("X-User-Id", "someone-else");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertEquals(401, response.getStatus());
        assertNull(chain.getRequest(), "the request must not reach the controllers");
    }

    @Test
    void rejectsATokenSignedWithAnotherSecret() throws Exception {
        String forged = token("other-secret-that-is-also-32-bytes-long!!!", Map.of("userId", "u1"));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(withBearer(forged), response, chain);

        assertEquals(401, response.getStatus());
        assertNull(chain.getRequest());
    }

    @Test
    void identityHeadersComeFromTheTokenNotFromTheCaller() throws Exception {
        MockHttpServletRequest request = withBearer(token(SECRET, Map.of(
                "userId", "u1", "email", "u1@example.com", "experienceLevel", "STUDENT")));
        request.addHeader("X-User-Id", "someone-else");
        request.addHeader("X-User-Experience", "YEARS_13_PLUS");
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, new MockHttpServletResponse(), chain);

        HttpServletRequest passed = (HttpServletRequest) chain.getRequest();
        assertNotNull(passed);
        assertEquals("u1", passed.getHeader("X-User-Id"));
        assertEquals("u1", passed.getHeader("x-user-id"));
        assertEquals(List.of("u1"), Collections.list(passed.getHeaders("X-User-Id")));
        assertEquals("u1@example.com", passed.getHeader("X-User-Email"));
        assertEquals("STUDENT", passed.getHeader("X-User-Experience"));
    }

    @Test
    void aCallerCannotAddAnExperienceLevelTheTokenDoesNotHave() throws Exception {
        MockHttpServletRequest request = withBearer(token(SECRET, Map.of("userId", "u1")));
        request.addHeader("X-User-Experience", "YEARS_13_PLUS");
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, new MockHttpServletResponse(), chain);

        HttpServletRequest passed = (HttpServletRequest) chain.getRequest();
        assertNotNull(passed);
        assertNull(passed.getHeader("X-User-Experience"));
        assertFalse(passed.getHeaders("X-User-Experience").hasMoreElements());
        assertFalse(Collections.list(passed.getHeaderNames()).stream()
                .anyMatch("X-User-Experience"::equalsIgnoreCase));
    }

    @Test
    void healthCheckNeedsNoToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/actuator/health");
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, new MockHttpServletResponse(), chain);

        assertNotNull(chain.getRequest());
    }

    private static MockHttpServletRequest withBearer(String token) {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/topics");
        request.addHeader("Authorization", "Bearer " + token);
        return request;
    }

    private static String token(String secret, Map<String, Object> claims) {
        Date now = new Date();
        return Jwts.builder()
                .claims(claims)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + 60_000))
                .signWith(Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }
}
