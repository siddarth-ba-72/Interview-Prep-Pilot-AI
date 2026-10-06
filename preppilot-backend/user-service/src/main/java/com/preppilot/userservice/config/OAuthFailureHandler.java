package com.preppilot.userservice.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationFailureHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@Component
public class OAuthFailureHandler extends SimpleUrlAuthenticationFailureHandler {

    private static final Logger log = LoggerFactory.getLogger(OAuthFailureHandler.class);

    private final String frontendOrigin;

    public OAuthFailureHandler(@Value("${frontend.origin}") String frontendOrigin) {
        this.frontendOrigin = frontendOrigin;
    }

    @Override
    public void onAuthenticationFailure(HttpServletRequest request, HttpServletResponse response,
                                        AuthenticationException exception) throws IOException {
        log.warn("Google OAuth login failed: {}", exception.getMessage(), exception);

        // Without this, Spring falls back to its built-in /login?error page on the user-service
        // host, which only says "Invalid credentials". Send the user back to the SPA instead.
        String code = exception instanceof OAuth2AuthenticationException oauth
                ? oauth.getError().getErrorCode()
                : "authentication_failed";
        getRedirectStrategy().sendRedirect(request, response,
                frontendOrigin + "/login?oauth_error=" + URLEncoder.encode(code, StandardCharsets.UTF_8));
    }
}
