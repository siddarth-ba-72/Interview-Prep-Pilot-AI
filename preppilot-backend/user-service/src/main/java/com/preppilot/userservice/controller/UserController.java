package com.preppilot.userservice.controller;

import com.preppilot.userservice.dto.AuthDtos.UserProfile;
import com.preppilot.userservice.model.User;
import com.preppilot.userservice.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    private final UserRepository userRepository;

    public UserController(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @GetMapping("/me")
    public ResponseEntity<UserProfile> getMe(@RequestHeader("X-User-Id") String userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
        return ResponseEntity.ok(new UserProfile(user.getId(), user.getEmail(), user.getDisplayName()));
    }
}
