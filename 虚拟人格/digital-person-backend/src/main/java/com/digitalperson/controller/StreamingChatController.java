package com.digitalperson.controller;

import com.digitalperson.service.StreamingChatService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class StreamingChatController {

    @Autowired
    private StreamingChatService streamingChatService;

    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> streamChat(@RequestBody Map<String, String> request) {
        String userMessage = request.get("message");
        if (userMessage == null || userMessage.trim().isEmpty()) {
            return Flux.just("错误：消息不能为空");
        }

        return streamingChatService.processMessageStream(userMessage)
            .onErrorReturn("抱歉，服务暂时不可用，请稍后再试。");
    }

    @PostMapping("/chat/function")
    public Mono<ResponseEntity<Map<String, Object>>> chatWithFunction(@RequestBody Map<String, String> request) {
        String userMessage = request.get("message");
        if (userMessage == null || userMessage.trim().isEmpty()) {
            return Mono.just(ResponseEntity.badRequest().body(Map.of(
                "error", "Message cannot be empty"
            )));
        }

        return streamingChatService.processMessageWithFunctionCalling(userMessage)
            .map(response -> ResponseEntity.ok(response))
            .onErrorReturn(ResponseEntity.internalServerError().body(Map.of(
                "error", "Internal server error",
                "success", false
            )));
    }

    @GetMapping("/tools")
    public Mono<ResponseEntity<Map<String, Object>>> getAvailableTools() {
        return Mono.fromCallable(() -> {
            try {
                Map<String, Object> response = Map.of(
                    "tools", new Object[]{
                        Map.of(
                            "name", "search_github",
                            "description", "搜索GitHub开源项目",
                            "example", "帮我搜索Vue相关的项目"
                        ),
                        Map.of(
                            "name", "get_weather",
                            "description", "查询城市天气",
                            "example", "北京天气怎么样？"
                        ),
                        Map.of(
                            "name", "get_current_time",
                            "description", "获取当前时间",
                            "example", "现在几点了？"
                        ),
                        Map.of(
                            "name", "calculate",
                            "description", "数学计算",
                            "example", "计算2+3*4"
                        )
                    },
                    "success", true
                );
                return ResponseEntity.ok(response);
            } catch (Exception e) {
                return ResponseEntity.internalServerError().body(Map.of(
                    "error", "获取工具列表失败",
                    "success", false
                ));
            }
        });
    }
}