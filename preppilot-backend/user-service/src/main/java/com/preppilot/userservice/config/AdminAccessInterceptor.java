package com.preppilot.userservice.config;

import com.preppilot.userservice.model.Role;
import com.preppilot.userservice.service.JwtService;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.io.IOException;

/**
 * Lets only admins reach /api/v1/admin/**. The role comes from the verified access token on
 * every request, never from a header, because this service has a public URL. It is an MVC
 * interceptor rather than a servlet filter so that it matches paths exactly the way the
 * controllers do: no spelling of the URL reaches an admin controller without passing it.
 */
@Component
public class AdminAccessInterceptor implements HandlerInterceptor {

    private final JwtService jwtService;

    public AdminAccessInterceptor(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws IOException {
        Claims claims = verifiedClaims(request.getHeader(HttpHeaders.AUTHORIZATION));
        if (claims == null || claims.get("userId", String.class) == null) {
            reject(response, HttpServletResponse.SC_UNAUTHORIZED, "UNAUTHORIZED", "Missing or invalid access token");
            return false;
        }
        if (!Role.ADMIN.name().equals(claims.get("role", String.class))) {
            reject(response, HttpServletResponse.SC_FORBIDDEN, "ADMIN_ACCESS_REQUIRED", "Admin access required");
            return false;
        }
        return true;
    }

    private Claims verifiedClaims(String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return null;
        }
        try {
            return jwtService.parseAccessToken(authHeader.substring(7).trim());
        } catch (JwtException | IllegalArgumentException e) {
            return null;
        }
    }

    private void reject(HttpServletResponse response, int status, String code, String message) throws IOException {
        response.setStatus(status);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write(
                "{\"error\":{\"code\":\"" + code + "\",\"message\":\"" + message + "\"}}");
    }
}
