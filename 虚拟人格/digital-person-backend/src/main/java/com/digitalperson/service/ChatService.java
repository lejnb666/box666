package com.digitalperson.service;

import com.digitalperson.entity.ChatMessage;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class ChatService {

    private final WebClient webClient;
    private static final String SYSTEM_PROMPT = "你现在是李四，说话风格幽默风趣，喜欢用网络流行语。请回答用户的问题，保持友好和有趣的对话风格。";

    @Value("${python.rag.url:http://localhost:5000}")
    private String pythonRagUrl;

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

    public String processMessage(String userMessage, List<ChatMessage> contextMessages) {
        try {
            // 首先调用Python RAG引擎获取增强的提示词
            String enhancedPrompt = callPythonRAGEngine(userMessage);

            // 调用大模型API with context
            return callLLMAPIWithContext(userMessage, enhancedPrompt, contextMessages);

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
                .uri(pythonRagUrl + "/rag-query")
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
                .uri(llmConfig.getApiUrl())
                .header("Authorization", "Bearer " + llmConfig.getApiKey())
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

    private String callLLMAPIWithContext(String userMessage, String systemPrompt, List<ChatMessage> contextMessages) {
        try {
            // Build messages array with context
            Object[] messages = new Object[contextMessages.size() + 2];
            int index = 0;

            // Add system prompt
            messages[index++] = Map.of("role", "system", "content", systemPrompt);

            // Add context messages (most recent first)
            List<ChatMessage> recentMessages = contextMessages.stream()
                    .limit(10) // Limit to last 10 messages for context
                    .collect(Collectors.toList());

            for (ChatMessage msg : recentMessages) {
                String role = msg.getSenderType() == ChatMessage.SenderType.USER ? "user" : "assistant";
                messages[index++] = Map.of("role", role, "content", msg.getContent());
            }

            // Add current user message
            messages[index] = Map.of("role", "user", "content", userMessage);

            Map<String, Object> requestBody = Map.of(
                "model", llmConfig.getModel(),
                "messages", messages,
                "temperature", llmConfig.getTemperature(),
                "max_tokens", llmConfig.getMaxTokens()
            );

            Mono<Map> response = webClient.post()
                .uri(llmConfig.getApiUrl())
                .header("Authorization", "Bearer " + llmConfig.getApiKey())
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