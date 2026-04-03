package com.digitalperson.service;

import com.digitalperson.config.LlmConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.HashMap;

@Service
public class StreamingChatService {

    private final WebClient webClient;
    private final LlmConfig llmConfig;
    private final ChatService chatService;

    private static final String SYSTEM_PROMPT = "你现在是李四，说话风格幽默风趣，喜欢用网络流行语。请回答用户的问题，保持友好和有趣的对话风格。";

    @Autowired
    public StreamingChatService(LlmConfig llmConfig, ChatService chatService) {
        this.webClient = WebClient.builder().build();
        this.llmConfig = llmConfig;
        this.chatService = chatService;
    }

    public Flux<String> processMessageStream(String userMessage) {
        return Flux.create(sink -> {
            try {
                // 首先调用Python RAG引擎获取增强的提示词
                String enhancedPrompt = chatService.callPythonRAGEngine(userMessage);

                // 调用大模型API（流式）
                callStreamingLLMAPI(userMessage, enhancedPrompt, sink);

            } catch (Exception e) {
                sink.error(e);
            }
        });
    }

    private void callStreamingLLMAPI(String userMessage, String systemPrompt, Flux<String> sink) {
        try {
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("model", llmConfig.getModel());
            requestBody.put("messages", new Object[]{
                Map.of("role", "system", "content", systemPrompt),
                Map.of("role", "user", "content", userMessage)
            });
            requestBody.put("temperature", llmConfig.getTemperature());
            requestBody.put("max_tokens", llmConfig.getMaxTokens());
            requestBody.put("stream", true);  // 启用流式输出

            webClient.post()
                .uri(llmConfig.getApiUrl())
                .header("Authorization", "Bearer " + llmConfig.getApiKey())
                .header("Content-Type", "application/json")
                .header("Accept", "text/event-stream")
                .bodyValue(requestBody)
                .retrieve()
                .bodyToFlux(String.class)
                .subscribe(
                    data -> {
                        try {
                            // 解析SSE格式的数据
                            if (data.startsWith("data: ")) {
                                String jsonData = data.substring(6).trim();
                                if (!"[DONE]".equals(jsonData)) {
                                    // 解析JSON获取内容
                                    String content = parseStreamingResponse(jsonData);
                                    if (content != null && !content.isEmpty()) {
                                        sink.next(content);
                                    }
                                } else {
                                    sink.complete();
                                }
                            }
                        } catch (Exception e) {
                            System.err.println("解析流式响应失败: " + e.getMessage());
                        }
                    },
                    error -> {
                        System.err.println("流式API调用失败: " + error.getMessage());
                        // 降级到非流式调用
                        String fallbackResponse = getFallbackResponse(userMessage);
                        sink.next(fallbackResponse);
                        sink.complete();
                    },
                    sink::complete
                );

        } catch (Exception e) {
            System.err.println("流式调用准备失败: " + e.getMessage());
            String fallbackResponse = getFallbackResponse(userMessage);
            sink.next(fallbackResponse);
            sink.complete();
        }
    }

    private String parseStreamingResponse(String jsonData) {
        try {
            // 简化的JSON解析，实际项目中建议使用Jackson等库
            if (jsonData.contains("\"delta\"")) {
                int contentStart = jsonData.indexOf("\"content\":");
                if (contentStart != -1) {
                    int valueStart = jsonData.indexOf('"', contentStart + 10);
                    int valueEnd = jsonData.indexOf('"', valueStart + 1);
                    if (valueStart != -1 && valueEnd != -1) {
                        return jsonData.substring(valueStart + 1, valueEnd);
                    }
                }
            }
            return "";
        } catch (Exception e) {
            return "";
        }
    }

    private String getFallbackResponse(String userMessage) {
        // 降级回复
        return "你好！我是李四，很高兴和你聊天！";
    }

    public Mono<Map<String, Object>> processMessageWithFunctionCalling(String userMessage) {
        return Mono.fromCallable(() -> {
            try {
                // 调用Function Calling Agent
                Map<String, Object> requestBody = Map.of(
                    "message", userMessage,
                    "system_prompt", SYSTEM_PROMPT
                );

                Map result = webClient.post()
                    .uri("http://localhost:5002/function-call-chat")
                    .header("Content-Type", "application/json")
                    .bodyValue(requestBody)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block();

                Map<String, Object> response = new HashMap<>();
                if (result != null && result.containsKey("response")) {
                    response.put("response", result.get("response"));
                    response.put("tool_used", result.get("tool_used"));
                    response.put("success", result.get("success"));
                } else {
                    response.put("response", "抱歉，我现在无法回答，请稍后再试。");
                    response.put("success", false);
                }

                return response;

            } catch (Exception e) {
                System.err.println("Function Calling处理失败: " + e.getMessage());
                Map<String, Object> errorResponse = new HashMap<>();
                errorResponse.put("response", "服务暂时不可用，请稍后再试。");
                errorResponse.put("success", false);
                return errorResponse;
            }
        });
    }
}