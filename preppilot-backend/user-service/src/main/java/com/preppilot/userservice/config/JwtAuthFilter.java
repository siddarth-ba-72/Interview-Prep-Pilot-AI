package com.preppilot.userservice.config;

import com.preppilot.userservice.service.JwtService;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;
import java.util.Enumeration;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * Validates the caller's access token on /api/v1/users/**, the same way the gateway does.
 * This service has a public URL, so the gateway's check alone is not enough: without this
 * anyone could call it directly with a made-up X-User-Id. The auth and OAuth endpoints stay
 * open because they are how a caller gets a token in the first place.
 *
 * The identity headers controllers read (X-User-Id, X-User-Email, X-User-Experience) are
 * replaced with the token's claims, so whatever the caller sent in them is ignored.
 */
@Component
public class JwtAuthFilter extends OncePerRequestFilter {

    private static final String PROTECTED_PREFIX = "/api/v1/users/";

    private final JwtService jwtService;

    public JwtAuthFilter(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return !(path.startsWith(PROTECTED_PREFIX) || path.equals("/api/v1/users"));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String authHeader = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            unauthorized(response);
            return;
        }

        Claims claims;
        try {
            claims = jwtService.parseAccessToken(authHeader.substring(7).trim());
        } catch (JwtException | IllegalArgumentException e) {
            unauthorized(response);
            return;
        }

        String userId = claims.get("userId", String.class);
        if (userId == null) {
            unauthorized(response);
            return;
        }

        Map<String, String> identity = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
        identity.put("X-User-Id", userId);
        String email = claims.get("email", String.class);
        identity.put("X-User-Email", email != null ? email : "");
        // Absent for users who have not finished onboarding; a null value removes the header
        identity.put("X-User-Experience", claims.get("experienceLevel", String.class));

        chain.doFilter(new IdentityHeadersRequest(request, identity), response);
    }

    private void unauthorized(HttpServletResponse response) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write(
                "{\"error\":{\"code\":\"UNAUTHORIZED\",\"message\":\"Missing or invalid access token\"}}");
    }

    /** Serves the identity headers from the verified token instead of from the raw request. */
    private static class IdentityHeadersRequest extends HttpServletRequestWrapper {

        private final Map<String, String> identity;

        IdentityHeadersRequest(HttpServletRequest request, Map<String, String> identity) {
            super(request);
            this.identity = identity;
        }

        @Override
        public String getHeader(String name) {
            return identity.containsKey(name) ? identity.get(name) : super.getHeader(name);
        }

        @Override
        public Enumeration<String> getHeaders(String name) {
            if (!identity.containsKey(name)) {
                return super.getHeaders(name);
            }
            String value = identity.get(name);
            return value == null ? Collections.emptyEnumeration() : Collections.enumeration(Set.of(value));
        }

        @Override
        public Enumeration<String> getHeaderNames() {
            Set<String> names = new LinkedHashSet<>();
            for (Enumeration<String> e = super.getHeaderNames(); e.hasMoreElements(); ) {
                String name = e.nextElement();
                if (!identity.containsKey(name)) {
                    names.add(name);
                }
            }
            identity.forEach((name, value) -> {
                if (value != null) {
                    names.add(name);
                }
            });
            return Collections.enumeration(names);
        }
    }
}
