package com.preppilot.userservice.config;

import com.preppilot.userservice.model.User;
import com.preppilot.userservice.service.AuthService;
import com.preppilot.userservice.service.AuthService.TokenPair;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Component
public class OAuthSuccessHandler extends SimpleUrlAuthenticationSuccessHandler {

    private final AuthService authService;
    private final long refreshTokenExpiryDays;
    private final String frontendOrigin;

    public OAuthSuccessHandler(AuthService authService,
                               @Value("${jwt.refresh-token-expiry-days}") long refreshTokenExpiryDays,
                               @Value("${frontend.origin}") String frontendOrigin) {
        this.authService = authService;
        this.refreshTokenExpiryDays = refreshTokenExpiryDays;
        this.frontendOrigin = frontendOrigin;
    }

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
                                        Authentication authentication) throws IOException {
        OAuth2User oauth2User = ((OAuth2AuthenticationToken) authentication).getPrincipal();

        String googleId = oauth2User.getAttribute("sub");
        String email = oauth2User.getAttribute("email");
        String displayName = oauth2User.getAttribute("name");
        if (displayName == null) displayName = email;

        User user = authService.findOrCreateGoogleUser(googleId, email, displayName);
        TokenPair pair = authService.issueTokens(user);

        Cookie cookie = new Cookie("refresh_token", pair.rawRefreshToken());
        cookie.setHttpOnly(true);
        cookie.setSecure(true);
        cookie.setPath("/api/v1/auth/refresh");
        cookie.setMaxAge((int) (refreshTokenExpiryDays * 24 * 60 * 60));
        response.addCookie(cookie);

        // Pass access token to frontend via URL fragment — never stored in URL history
        getRedirectStrategy().sendRedirect(request, response,
                frontendOrigin + "/auth/callback#token=" + pair.authResponse().accessToken());
    }
}
