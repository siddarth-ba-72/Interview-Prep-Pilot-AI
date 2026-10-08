package com.preppilot.topicservice.config;

import com.preppilot.topicservice.exception.ApiException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AdminAccessInterceptorTest {

    private static final String SECRET = "test-secret-that-is-at-least-32-bytes-long!!";

    private final AdminAccessInterceptor interceptor = new AdminAccessInterceptor(SECRET);

    @Test
    void rejectsARequestWithoutAToken() {
        assertEquals(HttpStatus.UNAUTHORIZED, rejection(request(null)));
    }

    @Test
    void rejectsAnExpiredAdminToken() {
        assertEquals(HttpStatus.UNAUTHORIZED, rejection(request(token(SECRET, "ADMIN", -60_000))));
    }

    @Test
    void rejectsAnAdminTokenSignedWithAnotherKey() {
        String forged = token("another-secret-that-is-at-least-32-bytes-long", "ADMIN", 60_000);
        assertEquals(HttpStatus.UNAUTHORIZED, rejection(request(forged)));
    }

    @Test
    void rejectsARegularUser() {
        assertEquals(HttpStatus.FORBIDDEN, rejection(request(token(SECRET, "USER", 60_000))));
    }

    @Test
    void rejectsATokenIssuedBeforeRolesExisted() {
        assertEquals(HttpStatus.FORBIDDEN, rejection(request(token(SECRET, null, 60_000))));
    }

    @Test
    void ignoresARoleHeaderTheCallerSent() {
        MockHttpServletRequest request = request(token(SECRET, "USER", 60_000));
        request.addHeader("X-User-Role", "ADMIN");
        assertEquals(HttpStatus.FORBIDDEN, rejection(request));
    }

    @Test
    void letsAnAdminThrough() {
        assertTrue(interceptor.preHandle(request(token(SECRET, "ADMIN", 60_000)), new MockHttpServletResponse(), new Object()));
    }

    private HttpStatus rejection(MockHttpServletRequest request) {
        return assertThrows(ApiException.class,
                () -> interceptor.preHandle(request, new MockHttpServletResponse(), new Object())).getStatus();
    }

    private static MockHttpServletRequest request(String token) {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/admin/activity/summary");
        if (token != null) {
            request.addHeader("Authorization", "Bearer " + token);
        }
        return request;
    }

    private static String token(String secret, String role, long expiresInMs) {
        Map<String, Object> claims = new HashMap<>(Map.of("userId", "u1", "email", "u1@example.com"));
        if (role != null) {
            claims.put("role", role);
        }
        Date now = new Date();
        return Jwts.builder()
                .claims(claims)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expiresInMs))
                .signWith(Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }
}
