package com.streammonitor.common;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;

import javax.validation.ConstraintViolationException;
import java.util.HashMap;
import java.util.Map;

/**
 * 全局异常处理器
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * 处理参数校验异常
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Result<?>> handleMethodArgumentNotValidException(
            MethodArgumentNotValidException ex, WebRequest request) {
        Map<String, String> errors = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach((error) -> {
            String fieldName = ((FieldError) error).getField();
            String errorMessage = error.getDefaultMessage();
            errors.put(fieldName, errorMessage);
        });

        log.warn("参数校验失败: {} - {}", request.getDescription(false), errors);
        return ResponseEntity.badRequest()
                .body(Result.validateFailed("参数校验失败: " + errors));
    }

    /**
     * 处理绑定异常
     */
    @ExceptionHandler(BindException.class)
    public ResponseEntity<Result<?>> handleBindException(
            BindException ex, WebRequest request) {
        Map<String, String> errors = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach((error) -> {
            String fieldName = ((FieldError) error).getField();
            String errorMessage = error.getDefaultMessage();
            errors.put(fieldName, errorMessage);
        });

        log.warn("参数绑定失败: {} - {}", request.getDescription(false), errors);
        return ResponseEntity.badRequest()
                .body(Result.validateFailed("参数绑定失败: " + errors));
    }

    /**
     * 处理约束违反异常
     */
    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<Result<?>> handleConstraintViolationException(
            ConstraintViolationException ex, WebRequest request) {
        log.warn("约束违反异常: {} - {}", request.getDescription(false), ex.getMessage());
        return ResponseEntity.badRequest()
                .body(Result.validateFailed("参数校验失败: " + ex.getMessage()));
    }

    /**
     * 处理业务异常
     */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Result<?>> handleBusinessException(
            BusinessException ex, WebRequest request) {
        log.warn("业务异常: {} - {}", request.getDescription(false), ex.getMessage());
        return ResponseEntity.status(ex.getCode())
                .body(Result.fail(ex.getCode(), ex.getMessage()));
    }

    /**
     * 处理空指针异常
     */
    @ExceptionHandler(NullPointerException.class)
    public ResponseEntity<Result<?>> handleNullPointerException(
            NullPointerException ex, WebRequest request) {
        log.error("空指针异常: {} - ", request.getDescription(false), ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Result.error("系统内部错误，请联系管理员"));
    }

    /**
     * 处理运行时异常
     */
    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Result<?>> handleRuntimeException(
            RuntimeException ex, WebRequest request) {
        log.error("运行时异常: {} - ", request.getDescription(false), ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Result.error("系统内部错误，请稍后重试"));
    }

    /**
     * 处理所有其他异常
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Result<?>> handleException(
            Exception ex, WebRequest request) {
        log.error("未知异常: {} - ", request.getDescription(false), ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Result.error("系统异常，请联系管理员"));
    }
}