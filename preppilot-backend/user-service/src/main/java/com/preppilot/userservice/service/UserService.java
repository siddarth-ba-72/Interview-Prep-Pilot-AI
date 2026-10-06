package com.preppilot.userservice.service;

import com.preppilot.userservice.dto.AuthDtos.UpdateProfileRequest;
import com.preppilot.userservice.model.User;
import com.preppilot.userservice.repository.UserRepository;
import org.springframework.cache.annotation.CachePut;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Cacheable(value = "users", key = "#userId")
    public User getUser(String userId) {
        return findUser(userId);
    }

    /** Saves the onboarding questionnaire answers; also used to edit them later. */
    @CachePut(value = "users", key = "#userId")
    public User updateProfile(String userId, UpdateProfileRequest request) {
        User user = findUser(userId);
        user.setPreferredDomain(request.preferredDomain().trim());
        user.setExperienceLevel(request.experienceLevel());
        return userRepository.save(user);
    }

    private User findUser(String userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
    }
}
