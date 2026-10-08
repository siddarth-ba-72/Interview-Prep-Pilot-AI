package com.preppilot.userservice.controller;

import com.preppilot.userservice.dto.AdminDtos.AdminUser;
import com.preppilot.userservice.dto.AdminDtos.AdminUserPage;
import com.preppilot.userservice.dto.AdminDtos.AdminUserStats;
import com.preppilot.userservice.service.AdminUserService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** Read-only. Only admins get here: AdminAccessInterceptor checks the token's role first. */
@RestController
@RequestMapping("/api/v1/admin/users")
public class AdminUserController {

    private final AdminUserService adminUserService;

    public AdminUserController(AdminUserService adminUserService) {
        this.adminUserService = adminUserService;
    }

    @GetMapping
    public ResponseEntity<AdminUserPage> list(@RequestParam(required = false) String q,
                                              @RequestParam(defaultValue = "0") int page,
                                              @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(adminUserService.listUsers(q, page, size));
    }

    @GetMapping("/stats")
    public ResponseEntity<AdminUserStats> stats() {
        return ResponseEntity.ok(adminUserService.stats());
    }

    @GetMapping("/{userId}")
    public ResponseEntity<AdminUser> get(@PathVariable String userId) {
        return ResponseEntity.ok(adminUserService.getUser(userId));
    }
}
