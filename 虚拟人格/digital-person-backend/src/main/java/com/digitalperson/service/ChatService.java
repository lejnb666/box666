package com.digitalperson.service;

import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Arrays;

@Service
public class ChatService {

    private final WebClient webClient;
    private static final String SYSTEM_PROMPT = "你现在是李四，说话风格幽默风趣，喜欢用网络流行语。请回答用户的问题，保持友好和有趣的对话风格。";
    private static final String PYTHON_RAG_URL = "http://localhost:5000/rag-query";

    private final LlmConfig llmConfig;

    public ChatService(LlmConfig llmConfig) {
        this.webClient = WebClient.builder().build();
        this.llmConfig = llmConfig;
    }

    public String processMessage(String userMessage) {
        try {
            // 首先调用Python RAG引擎获取增强的提示词
            String enhancedPrompt = callPythonRAGEngine(userMessage);

            // 调用大模型API
            return callLLMAPI(userMessage, enhancedPrompt);

        } catch (Exception e) {
            System.err.println("处理消息时出错: " + e.getMessage());
            return "你好！我是李四，很高兴和你聊天！有什么我可以帮助你的吗？";
        }
    }

    // 供StreamingChatService调用的方法
    public String callPythonRAGEngine(String userMessage) {
        return callPythonRAGEngineInternal(userMessage);
    }

    private String callPythonRAGEngineInternal(String userMessage) {
        try {
            Map<String, Object> requestBody = Map.of(
                "query", userMessage,
                "target_persona", "李四"
            );

            Mono<Map> response = webClient.post()
                .uri(PYTHON_RAG_URL)
                .header("Content-Type", "application/json")
                .bodyValue(requestBody)
                .retrieve()
                .bodyToMono(Map.class);

            Map result = response.block();
            if (result != null && result.containsKey("enhanced_prompt")) {
                return (String) result.get("enhanced_prompt");
            }

            return SYSTEM_PROMPT;

        } catch (Exception e) {
            System.err.println("调用RAG引擎失败: " + e.getMessage());
            return SYSTEM_PROMPT;
        }
    }

    private String callLLMAPI(String userMessage, String systemPrompt) {
        try {
            Map<String, Object> requestBody = Map.of(
                "model", llmConfig.getModel(),
                "messages", new Object[]{
                    Map.of("role", "system", "content", systemPrompt),
                    Map.of("role", "user", "content", userMessage)
                },
                "temperature", llmConfig.getTemperature(),
                "max_tokens", llmConfig.getMaxTokens()
            );

            Mono<Map> response = webClient.post()
                .uri(apiUrl)
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type", "application/json")
                .bodyValue(requestBody)
                .retrieve()
                .bodyToMono(Map.class);

            Map result = response.block();
            if (result != null && result.containsKey("choices")) {
                Object[] choices = (Object[]) result.get("choices");
                if (choices.length > 0) {
                    Map choice = (Map) choices[0];
                    Map message = (Map) choice.get("message");
                    return (String) message.get("content");
                }
            }

            return "抱歉，我现在无法回答，请稍后再试。";

        } catch (Exception e) {
            System.err.println("API调用失败: " + e.getMessage());
            return "你好！我是李四，很高兴和你聊天！有什么我可以帮助你的吗？";
        }
    }
}