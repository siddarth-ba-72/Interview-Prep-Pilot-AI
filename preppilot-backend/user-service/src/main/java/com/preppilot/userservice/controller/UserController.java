package com.preppilot.userservice.controller;

import com.preppilot.userservice.dto.AuthDtos.UserProfile;
import com.preppilot.userservice.model.User;
import com.preppilot.userservice.service.UserService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/me")
    public ResponseEntity<UserProfile> getMe(@RequestHeader("X-User-Id") String userId) {
        User user = userService.getUser(userId);
        return ResponseEntity.ok(new UserProfile(user.getId(), user.getEmail(), user.getDisplayName()));
    }
}
