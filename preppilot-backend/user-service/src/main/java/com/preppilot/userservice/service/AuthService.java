package com.preppilot.userservice.service;

import com.preppilot.userservice.dto.AuthDtos.AuthResponse;
import com.preppilot.userservice.dto.AuthDtos.LoginRequest;
import com.preppilot.userservice.dto.AuthDtos.RegisterRequest;
import com.preppilot.userservice.dto.AuthDtos.UserProfile;
import com.preppilot.userservice.model.AuthProvider;
import com.preppilot.userservice.model.RefreshToken;
import com.preppilot.userservice.model.User;
import com.preppilot.userservice.repository.RefreshTokenRepository;
import com.preppilot.userservice.repository.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.UUID;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final JwtService jwtService;
    private final long refreshTokenExpiryDays;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder(12);

    public AuthService(UserRepository userRepository,
                       RefreshTokenRepository refreshTokenRepository,
                       JwtService jwtService,
                       @Value("${jwt.refresh-token-expiry-days}") long refreshTokenExpiryDays) {
        this.userRepository = userRepository;
        this.refreshTokenRepository = refreshTokenRepository;
        this.jwtService = jwtService;
        this.refreshTokenExpiryDays = refreshTokenExpiryDays;
    }

    public UserProfile register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Email already registered");
        }
        User user = userRepository.save(new User(
                request.email(),
                passwordEncoder.encode(request.password()),
                AuthProvider.LOCAL,
                null,
                request.displayName()
        ));
        return toProfile(user);
    }

    public TokenPair login(LoginRequest request) {
        User user = userRepository.findByEmail(request.email())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid credentials"));

        if (user.getPasswordHash() == null || !passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid credentials");
        }

        return issueTokens(user);
    }

    public TokenPair refresh(String rawRefreshToken) {
        String tokenHash = hashToken(rawRefreshToken);
        RefreshToken stored = refreshTokenRepository.findByTokenHash(tokenHash);
        if (stored == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid or expired refresh token");
        }

        if (stored.getExpiresAt().isBefore(Instant.now())) {
            refreshTokenRepository.delete(stored);
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Refresh token expired");
        }

        // Token rotation: delete old before issuing new
        refreshTokenRepository.delete(stored);

        User user = userRepository.findById(stored.getUserId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User not found"));

        return issueTokens(user);
    }

    public void logout(String rawRefreshToken) {
        String tokenHash = hashToken(rawRefreshToken);
        RefreshToken stored = refreshTokenRepository.findByTokenHash(tokenHash);
        if (stored != null) {
            refreshTokenRepository.delete(stored);
        }
    }

    public User findOrCreateGoogleUser(String googleId, String email, String displayName) {
        return userRepository.findByGoogleId(googleId).orElseGet(() ->
                userRepository.findByEmail(email).map(existing -> {
                    existing.setGoogleId(googleId);
                    return userRepository.save(existing);
                }).orElseGet(() -> userRepository.save(
                        new User(email, null, AuthProvider.GOOGLE, googleId, displayName)
                ))
        );
    }

    public TokenPair issueTokens(User user) {
        String userId = user.getId();
        String accessToken = jwtService.generateAccessToken(userId, user.getEmail());

        String rawRefreshToken = UUID.randomUUID().toString();
        String tokenHash = hashToken(rawRefreshToken);

        refreshTokenRepository.save(new RefreshToken(
                userId,
                tokenHash,
                Instant.now().plus(refreshTokenExpiryDays, ChronoUnit.DAYS)
        ));

        return new TokenPair(
                new AuthResponse(accessToken, toProfile(user)),
                rawRefreshToken
        );
    }

    private String hashToken(String token) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(token.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hashBytes);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }

    private UserProfile toProfile(User user) {
        return new UserProfile(user.getId(), user.getEmail(), user.getDisplayName());
    }

    public record TokenPair(AuthResponse authResponse, String rawRefreshToken) {}
}
