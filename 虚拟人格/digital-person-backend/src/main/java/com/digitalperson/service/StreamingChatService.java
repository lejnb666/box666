package com.digitalperson.service;

import com.digitalperson.config.LlmConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Map;
import java.util.HashMap;

@Service
public class StreamingChatService {

    private final WebClient webClient;
    private final LlmConfig llmConfig;
    private final ChatService chatService;

    @Value("${python.agent.url:http://localhost:5002}")
    private String pythonAgentUrl;

    @Value("${python.rag.url:http://localhost:5000}")
    private String pythonRagUrl;

    private static final String SYSTEM_PROMPT = "你现在是李四，说话风格幽默风趣，喜欢用网络流行语。请回答用户的问题，保持友好和有趣的对话风格。";

    @Autowired
    public StreamingChatService(LlmConfig llmConfig, ChatService chatService) {
        this.webClient = WebClient.builder().build();
        this.llmConfig = llmConfig;
        this.chatService = chatService;
    }

    public Flux<String> processMessageStream(String userMessage) {
        // 使用纯响应式链式调用，避免手动管理 sink
        return Mono.fromCallable(() -> chatService.callPythonRAGEngine(userMessage))
            .flatMapMany(enhancedPrompt -> {
                Map<String, Object> requestBody = new HashMap<>();
                requestBody.put("model", llmConfig.getModel());
                requestBody.put("messages", new Object[]{
                    Map.of("role", "system", "content", enhancedPrompt),
                    Map.of("role", "user", "content", userMessage)
                });
                requestBody.put("temperature", llmConfig.getTemperature());
                requestBody.put("max_tokens", llmConfig.getMaxTokens());
                requestBody.put("stream", true);

                return webClient.post()
                    .uri(llmConfig.getApiUrl())
                    .header("Authorization", "Bearer " + llmConfig.getApiKey())
                    .header("Content-Type", "application/json")
                    .header("Accept", "text/event-stream")
                    .bodyValue(requestBody)
                    .retrieve()
                    .bodyToFlux(String.class)
                    .filter(data -> data.startsWith("data: ") && !"[DONE]".equals(data.substring(6).trim()))
                    .map(data -> parseStreamingResponse(data.substring(6).trim()))
                    .filter(content -> content != null && !content.isEmpty())
                    .onErrorResume(e -> {
                        System.err.println("流式API调用失败: " + e.getMessage());
                        return Flux.just(getFallbackResponse(userMessage));
                    });
            });
    }


    private String parseStreamingResponse(String jsonData) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(jsonData);

            // Parse OpenAI streaming format
            if (root.has("choices")) {
                JsonNode choices = root.get("choices");
                if (choices.isArray() && choices.size() > 0) {
                    JsonNode firstChoice = choices.get(0);

                    // Check for delta (streaming) or message (completion)
                    JsonNode delta = firstChoice.get("delta");
                    if (delta != null && delta.has("content")) {
                        JsonNode contentNode = delta.get("content");
                        if (contentNode != null && !contentNode.isNull()) {
                            return contentNode.asText();
                        }
                    }

                    // Fallback to message for non-streaming responses
                    JsonNode message = firstChoice.get("message");
                    if (message != null && message.has("content")) {
                        JsonNode contentNode = message.get("content");
                        if (contentNode != null && !contentNode.isNull()) {
                            return contentNode.asText();
                        }
                    }
                }
            }

            return "";
        } catch (Exception e) {
            System.err.println("JSON解析错误: " + e.getMessage());
            // Fallback to simple string extraction for malformed JSON
            try {
                if (jsonData.contains("\"content\":")) {
                    int start = jsonData.indexOf("\"content\":") + 10;
                    int quoteStart = jsonData.indexOf('"', start);
                    if (quoteStart != -1) {
                        int quoteEnd = jsonData.indexOf('"', quoteStart + 1);
                        if (quoteEnd != -1) {
                            return jsonData.substring(quoteStart + 1, quoteEnd);
                        }
                    }
                }
            } catch (Exception fallback) {
                System.err.println("Fallback解析也失败: " + fallback.getMessage());
            }
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
                // 首先调用Python RAG引擎获取增强的提示词
                String enhancedPrompt = chatService.callPythonRAGEngine(userMessage);

                // 调用Function Calling Agent with RAG-enhanced prompt
                Map<String, Object> requestBody = Map.of(
                    "message", userMessage,
                    "system_prompt", enhancedPrompt  // Use RAG-enhanced prompt instead of default
                );

                Map result = webClient.post()
                    .uri(pythonAgentUrl + "/function-call-chat")
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
                    response.put("has_rag_context", true);  // Indicate RAG was used
                } else {
                    response.put("response", "抱歉，我现在无法回答，请稍后再试。");
                    response.put("success", false);
                    response.put("has_rag_context", false);
                }

                return response;

            } catch (Exception e) {
                System.err.println("Function Calling处理失败: " + e.getMessage());
                Map<String, Object> errorResponse = new HashMap<>();
                errorResponse.put("response", "服务暂时不可用，请稍后再试。");
                errorResponse.put("success", false);
                errorResponse.put("has_rag_context", false);
                return errorResponse;
            }
        });
    }
}