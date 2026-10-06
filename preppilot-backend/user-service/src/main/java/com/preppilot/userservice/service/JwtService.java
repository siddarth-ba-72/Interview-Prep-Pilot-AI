package com.preppilot.userservice.service;

import com.preppilot.userservice.model.User;
import io.jsonwebtoken.JwtBuilder;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Service
public class JwtService {

    private final SecretKey signingKey;
    private final long accessTokenExpiryMs;

    public JwtService(
            @Value("${jwt.secret}") String jwtSecret,
            @Value("${jwt.access-token-expiry-ms}") long accessTokenExpiryMs) {
        this.signingKey = Keys.hmacShaKeyFor(jwtSecret.getBytes(StandardCharsets.UTF_8));
        this.accessTokenExpiryMs = accessTokenExpiryMs;
    }

    public String generateAccessToken(User user) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + accessTokenExpiryMs);
        JwtBuilder builder = Jwts.builder()
                .claim("userId", user.getId())
                .claim("email", user.getEmail());
        // The gateway forwards this as X-User-Experience; absent until onboarding is done
        if (user.getExperienceLevel() != null) {
            builder.claim("experienceLevel", user.getExperienceLevel().name());
        }
        return builder
                .issuedAt(now)
                .expiration(expiry)
                .signWith(signingKey)
                .compact();
    }
}
