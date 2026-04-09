package com.streammonitor.utils;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

/**
 * JWT工具类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtUtils {

    @Value("${app.config.jwt.secret}")
    private String secret;

    @Value("${app.config.jwt.expiration}")
    private long expiration;

    @Value("${app.config.jwt.refresh-expiration}")
    private long refreshExpiration;

    /**
     * 生成Token
     */
    public String generateToken(String subject) {
        Map<String, Object> claims = new HashMap<>();
        return createToken(claims, subject);
    }

    /**
     * 生成带有额外信息的Token
     */
    public String generateToken(Map<String, Object> claims, String subject) {
        return createToken(claims, subject);
    }

    /**
     * 创建Token
     */
    private String createToken(Map<String, Object> claims, String subject) {
        return Jwts.builder()
                .setClaims(claims)
                .setSubject(subject)
                .setIssuedAt(new Date(System.currentTimeMillis()))
                .setExpiration(new Date(System.currentTimeMillis() + expiration))
                .signWith(SignatureAlgorithm.HS512, secret)
                .compact();
    }

    /**
     * 从Token中获取用户名
     */
    public String getUsernameFromToken(String token) {
        return getClaimFromToken(token, Claims::getSubject);
    }

    /**
     * 从Token中获取过期时间
     */
    public Date getExpirationDateFromToken(String token) {
        return getClaimFromToken(token, Claims::getExpiration);
    }

    /**
     * 从Token中获取指定声明
     */
    public <T> T getClaimFromToken(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = getAllClaimsFromToken(token);
        return claimsResolver.apply(claims);
    }

    /**
     * 从Token中获取所有声明
     */
    private Claims getAllClaimsFromToken(String token) {
        return Jwts.parser().setSigningKey(secret).parseClaimsJws(token).getBody();
    }

    /**
     * 检查Token是否已过期
     */
    public Boolean isTokenExpired(String token) {
        final Date expiration = getExpirationDateFromToken(token);
        return expiration.before(new Date());
    }

    /**
     * 验证Token
     */
    public Boolean validateToken(String token, String username) {
        final String tokenUsername = getUsernameFromToken(token);
        return (tokenUsername.equals(username) && !isTokenExpired(token));
    }

    /**
     * 刷新Token
     */
    public String refreshToken(String token) {
        final Date createdDate = new Date();
        final Date expirationDate = new Date(createdDate.getTime() + refreshExpiration);

        final Claims claims = getAllClaimsFromToken(token);
        claims.setIssuedAt(createdDate);
        claims.setExpiration(expirationDate);

        return Jwts.builder()
                .setClaims(claims)
                .signWith(SignatureAlgorithm.HS512, secret)
                .compact();
    }

    /**
     * 获取Token过期时间（毫秒）
     */
    public long getExpiration() {
        return expiration;
    }

    /**
     * 获取Refresh Token过期时间（毫秒）
     */
    public long getRefreshExpiration() {
        return refreshExpiration;
    }

    /**
     * 生成Refresh Token
     */
    public String generateRefreshToken(String userId) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("type", "refresh");
        return Jwts.builder()
                .setClaims(claims)
                .setSubject(userId)
                .setIssuedAt(new Date(System.currentTimeMillis()))
                .setExpiration(new Date(System.currentTimeMillis() + refreshExpiration))
                .signWith(SignatureAlgorithm.HS512, secret)
                .compact();
    }

    /**
     * 验证Refresh Token
     */
    public Boolean validateRefreshToken(String token) {
        try {
            Claims claims = getAllClaimsFromToken(token);

            // 检查是否为refresh token
            String type = (String) claims.get("type");
            if (!"refresh".equals(type)) {
                return false;
            }

            // 检查是否过期
            return !isTokenExpired(token);
        } catch (Exception e) {
            log.error("Refresh Token验证失败", e);
            return false;
        }
    }

    /**
     * 从Token中获取用户ID
     */
    public String getUserIdFromToken(String token) {
        return getUsernameFromToken(token);
    }
}