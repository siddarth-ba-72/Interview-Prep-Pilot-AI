package com.preppilot.userservice.repository;

import com.preppilot.userservice.model.RefreshToken;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface RefreshTokenRepository extends MongoRepository<RefreshToken, String> {
    RefreshToken findByTokenHash(String tokenHash);
    void deleteAllByUserId(String userId);
}
