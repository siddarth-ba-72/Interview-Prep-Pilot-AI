package com.preppilot.userservice.service;

import com.preppilot.userservice.dto.FeedbackDtos.AdminFeedback;
import com.preppilot.userservice.dto.FeedbackDtos.AdminFeedbackPage;
import com.preppilot.userservice.dto.FeedbackDtos.FeedbackReceipt;
import com.preppilot.userservice.model.Feedback;
import com.preppilot.userservice.model.User;
import com.preppilot.userservice.repository.FeedbackRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

/** Users send feedback; only admins read it (AdminAccessInterceptor guards the admin endpoint). */
@Service
public class FeedbackService {

    static final int MAX_PAGE_SIZE = 100;

    private final FeedbackRepository feedbackRepository;
    private final UserService userService;

    public FeedbackService(FeedbackRepository feedbackRepository, UserService userService) {
        this.feedbackRepository = feedbackRepository;
        this.userService = userService;
    }

    /** A user may send any number of messages; each is saved with their current name and email. */
    public FeedbackReceipt submit(String userId, String message) {
        User user = userService.getUser(userId);
        Feedback saved = feedbackRepository.save(
                new Feedback(user.getId(), user.getEmail(), user.getDisplayName(), message.trim()));
        return new FeedbackReceipt(saved.getId(), saved.getCreatedAt());
    }

    /** Newest first. */
    public AdminFeedbackPage list(int page, int size) {
        int pageNumber = Math.max(page, 0);
        int pageSize = Math.clamp(size, 1, MAX_PAGE_SIZE);
        Page<Feedback> result = feedbackRepository.findAll(
                PageRequest.of(pageNumber, pageSize, Sort.by(Sort.Order.desc("createdAt"), Sort.Order.desc("id"))));
        return new AdminFeedbackPage(result.map(AdminFeedback::from).getContent(),
                pageNumber, pageSize, result.getTotalElements());
    }
}
