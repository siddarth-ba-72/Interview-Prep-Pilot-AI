package com.preppilot.userservice.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final OAuthSuccessHandler oauthSuccessHandler;

    public SecurityConfig(OAuthSuccessHandler oauthSuccessHandler) {
        this.oauthSuccessHandler = oauthSuccessHandler;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                // Sessions are needed only for the OAuth2 state handshake; all other auth
                // is handled by the gateway (JWT validation + X-User-Id injection).
                .authorizeHttpRequests(auth -> auth
                        .anyRequest().permitAll()
                )
                .oauth2Login(oauth2 -> oauth2
                        .successHandler(oauthSuccessHandler)
                );

        return http.build();
    }
}
