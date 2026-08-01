package com.preppilot.userservice.controller;

import com.preppilot.userservice.dto.AuthDtos.AuthResponse;
import com.preppilot.userservice.dto.AuthDtos.LoginRequest;
import com.preppilot.userservice.dto.AuthDtos.RegisterRequest;
import com.preppilot.userservice.dto.AuthDtos.UserProfile;
import com.preppilot.userservice.service.AuthService;
import com.preppilot.userservice.service.AuthService.TokenPair;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final long refreshTokenExpiryDays;

    public AuthController(AuthService authService,
                          @Value("${jwt.refresh-token-expiry-days}") long refreshTokenExpiryDays) {
        this.authService = authService;
        this.refreshTokenExpiryDays = refreshTokenExpiryDays;
    }

    @PostMapping("/register")
    public ResponseEntity<UserProfile> register(@Valid @RequestBody RegisterRequest request) {
        UserProfile profile = authService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(profile);
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody LoginRequest request,
                                              HttpServletResponse response) {
        TokenPair pair = authService.login(request);
        setRefreshTokenCookie(response, pair.rawRefreshToken());
        return ResponseEntity.ok(pair.authResponse());
    }

    @PostMapping("/refresh")
    public ResponseEntity<AuthResponse> refresh(HttpServletRequest request,
                                                HttpServletResponse response) {
        String rawRefreshToken = extractRefreshTokenCookie(request);
        if (rawRefreshToken == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        TokenPair pair = authService.refresh(rawRefreshToken);
        setRefreshTokenCookie(response, pair.rawRefreshToken());
        return ResponseEntity.ok(pair.authResponse());
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(HttpServletRequest request, HttpServletResponse response) {
        String rawRefreshToken = extractRefreshTokenCookie(request);
        if (rawRefreshToken != null) {
            authService.logout(rawRefreshToken);
        }
        clearRefreshTokenCookie(response);
        return ResponseEntity.noContent().build();
    }

    private void setRefreshTokenCookie(HttpServletResponse response, String token) {
        Cookie cookie = new Cookie("refresh_token", token);
        cookie.setHttpOnly(true);
        cookie.setSecure(true);
        cookie.setPath("/api/v1/auth/refresh");
        cookie.setMaxAge((int) (refreshTokenExpiryDays * 24 * 60 * 60));
        response.addCookie(cookie);
    }

    private void clearRefreshTokenCookie(HttpServletResponse response) {
        Cookie cookie = new Cookie("refresh_token", "");
        cookie.setHttpOnly(true);
        cookie.setSecure(true);
        cookie.setPath("/api/v1/auth/refresh");
        cookie.setMaxAge(0);
        response.addCookie(cookie);
    }

    private String extractRefreshTokenCookie(HttpServletRequest request) {
        if (request.getCookies() == null) return null;
        return Arrays.stream(request.getCookies())
                .filter(c -> "refresh_token".equals(c.getName()))
                .map(Cookie::getValue)
                .findFirst()
                .orElse(null);
    }
}
