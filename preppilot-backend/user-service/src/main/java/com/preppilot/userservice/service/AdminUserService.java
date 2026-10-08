package com.preppilot.userservice.service;

import com.preppilot.userservice.dto.AdminDtos.AdminUser;
import com.preppilot.userservice.dto.AdminDtos.AdminUserPage;
import com.preppilot.userservice.dto.AdminDtos.AdminUserStats;
import com.preppilot.userservice.model.User;
import com.preppilot.userservice.repository.UserRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.regex.Pattern;

/** Read-only user lookups for the admin dashboard. */
@Service
public class AdminUserService {

    static final int MAX_PAGE_SIZE = 100;
    private static final int MAX_SEARCH_LENGTH = 100;

    private final MongoTemplate mongoTemplate;
    private final UserRepository userRepository;

    public AdminUserService(MongoTemplate mongoTemplate, UserRepository userRepository) {
        this.mongoTemplate = mongoTemplate;
        this.userRepository = userRepository;
    }

    /** Newest users first. {@code search} matches part of the email or display name, ignoring case. */
    public AdminUserPage listUsers(String search, int page, int size) {
        int pageNumber = Math.max(page, 0);
        int pageSize = Math.clamp(size, 1, MAX_PAGE_SIZE);

        Query query = new Query();
        if (search != null && !search.isBlank()) {
            String trimmed = search.trim();
            // Quoted, so the search is matched literally rather than run as a regex
            String literal = Pattern.quote(trimmed.substring(0, Math.min(trimmed.length(), MAX_SEARCH_LENGTH)));
            query.addCriteria(new Criteria().orOperator(
                    Criteria.where("email").regex(literal, "i"),
                    Criteria.where("displayName").regex(literal, "i")));
        }
        long total = mongoTemplate.count(query, User.class);

        query.with(PageRequest.of(pageNumber, pageSize, Sort.by(Sort.Order.desc("createdAt"), Sort.Order.desc("id"))));
        List<AdminUser> users = mongoTemplate.find(query, User.class).stream().map(AdminUser::from).toList();
        return new AdminUserPage(users, pageNumber, pageSize, total);
    }

    /** Read straight from the database, not through UserService's cache, so it is never stale. */
    public AdminUser getUser(String userId) {
        return userRepository.findById(userId)
                .map(AdminUser::from)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
    }

    public AdminUserStats stats() {
        return new AdminUserStats(userRepository.count());
    }
}
