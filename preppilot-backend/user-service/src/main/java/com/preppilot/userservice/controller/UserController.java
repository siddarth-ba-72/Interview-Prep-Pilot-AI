package com.preppilot.userservice.controller;

import com.preppilot.userservice.dto.AuthDtos.AuthResponse;
import com.preppilot.userservice.dto.AuthDtos.UpdateProfileRequest;
import com.preppilot.userservice.dto.AuthDtos.UserProfile;
import com.preppilot.userservice.model.User;
import com.preppilot.userservice.service.AuthService;
import com.preppilot.userservice.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    private final UserService userService;
    private final AuthService authService;

    public UserController(UserService userService, AuthService authService) {
        this.userService = userService;
        this.authService = authService;
    }

    @GetMapping("/me")
    public ResponseEntity<UserProfile> getMe(@RequestHeader("X-User-Id") String userId) {
        User user = userService.getUser(userId);
        return ResponseEntity.ok(UserProfile.from(user));
    }

    /** Returns a new access token too: the experience level is a token claim, so the old
     * token would keep serving the previous level until it expired. */
    @PutMapping("/me/profile")
    public ResponseEntity<AuthResponse> updateProfile(@RequestHeader("X-User-Id") String userId,
                                                      @Valid @RequestBody UpdateProfileRequest request) {
        User user = userService.updateProfile(userId, request);
        return ResponseEntity.ok(authService.reissueAccessToken(user));
    }
}
