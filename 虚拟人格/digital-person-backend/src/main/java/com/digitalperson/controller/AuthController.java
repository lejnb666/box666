package com.digitalperson.controller;

import com.digitalperson.dto.AuthRequest;
import com.digitalperson.dto.AuthResponse;
import com.digitalperson.service.AuthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = "*")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(@RequestBody AuthRequest authRequest) {
        if (authRequest.getUsername() == null || authRequest.getUsername().trim().isEmpty()) {
            return ResponseEntity.badRequest().body(new AuthResponse(null, null, null, "Username is required"));
        }
        if (authRequest.getPassword() == null || authRequest.getPassword().length() < 6) {
            return ResponseEntity.badRequest().body(new AuthResponse(null, authRequest.getUsername(), null, "Password must be at least 6 characters"));
        }

        AuthResponse response = authService.register(authRequest);
        if (response.getToken() != null) {
            return ResponseEntity.ok(response);
        } else {
            return ResponseEntity.badRequest().body(response);
        }
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@RequestBody AuthRequest authRequest) {
        if (authRequest.getUsername() == null || authRequest.getPassword() == null) {
            return ResponseEntity.badRequest().body(new AuthResponse(null, null, null, "Username and password are required"));
        }

        AuthResponse response = authService.login(authRequest);
        if (response.getToken() != null) {
            return ResponseEntity.ok(response);
        } else {
            return ResponseEntity.badRequest().body(response);
        }
    }
}