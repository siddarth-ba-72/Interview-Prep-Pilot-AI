package com.preppilot.topicservice.config;

import com.preppilot.topicservice.exception.ApiException;
import com.preppilot.topicservice.exception.ErrorCode;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;

/**
 * Lets only admins reach /api/v1/admin/**. The role comes from the verified access token on
 * every request, never from a header, because this service has a public URL. It is an MVC
 * interceptor rather than part of JwtAuthFilter so that it matches paths exactly the way the
 * controllers do: no spelling of the URL reaches an admin controller without passing it.
 */
@Component
public class AdminAccessInterceptor implements HandlerInterceptor {

    private static final String ADMIN_ROLE = "ADMIN";

    private final SecretKey signingKey;

    public AdminAccessInterceptor(@Value("${jwt.secret}") String jwtSecret) {
        this.signingKey = Keys.hmacShaKeyFor(jwtSecret.getBytes(StandardCharsets.UTF_8));
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        Claims claims = verifiedClaims(request.getHeader(HttpHeaders.AUTHORIZATION));
        if (claims == null || claims.get("userId", String.class) == null) {
            throw new ApiException(ErrorCode.USER_UNAUTHORIZED, "Missing or invalid access token");
        }
        if (!ADMIN_ROLE.equals(claims.get("role", String.class))) {
            throw new ApiException(ErrorCode.ADMIN_ACCESS_REQUIRED);
        }
        return true;
    }

    private Claims verifiedClaims(String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return null;
        }
        try {
            return Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(authHeader.substring(7).trim())
                    .getPayload();
        } catch (JwtException | IllegalArgumentException e) {
            return null;
        }
    }
}
