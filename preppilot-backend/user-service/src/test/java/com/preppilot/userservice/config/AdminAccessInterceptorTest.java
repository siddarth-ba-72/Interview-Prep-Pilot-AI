package com.preppilot.userservice.config;

import com.preppilot.userservice.service.JwtService;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AdminAccessInterceptorTest {

    private static final String SECRET = "test-secret-that-is-at-least-32-bytes-long!!";

    private final AdminAccessInterceptor interceptor = new AdminAccessInterceptor(new JwtService(SECRET, 1_800_000));

    @Test
    void rejectsARequestWithoutAToken() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertFalse(interceptor.preHandle(request(null), response, new Object()));
        assertEquals(401, response.getStatus());
    }

    @Test
    void rejectsAnExpiredAdminToken() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertFalse(interceptor.preHandle(request(token(SECRET, "ADMIN", -60_000)), response, new Object()));
        assertEquals(401, response.getStatus());
    }

    @Test
    void rejectsAnAdminTokenSignedWithAnotherKey() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();
        String forged = token("another-secret-that-is-at-least-32-bytes-long", "ADMIN", 60_000);

        assertFalse(interceptor.preHandle(request(forged), response, new Object()));
        assertEquals(401, response.getStatus());
    }

    @Test
    void rejectsARegularUser() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertFalse(interceptor.preHandle(request(token(SECRET, "USER", 60_000)), response, new Object()));
        assertEquals(403, response.getStatus());
    }

    @Test
    void rejectsATokenIssuedBeforeRolesExisted() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertFalse(interceptor.preHandle(request(token(SECRET, null, 60_000)), response, new Object()));
        assertEquals(403, response.getStatus());
    }

    @Test
    void ignoresARoleHeaderTheCallerSent() throws Exception {
        MockHttpServletRequest request = request(token(SECRET, "USER", 60_000));
        request.addHeader("X-User-Role", "ADMIN");
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertFalse(interceptor.preHandle(request, response, new Object()));
        assertEquals(403, response.getStatus());
    }

    @Test
    void letsAnAdminThrough() throws Exception {
        assertTrue(interceptor.preHandle(request(token(SECRET, "ADMIN", 60_000)), new MockHttpServletResponse(), new Object()));
    }

    private static MockHttpServletRequest request(String token) {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/admin/users");
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
