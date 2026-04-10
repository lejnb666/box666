// Frontend configuration
const config = {
  // API base URLs
  api: {
    baseUrl: process.env.NODE_ENV === 'development'
      ? 'http://localhost:8080'
      : 'https://api.yourdomain.com',

    // Legacy URLs for backward compatibility
    backendUrl: process.env.NODE_ENV === 'development'
      ? 'http://localhost:8080'
      : 'https://api.yourdomain.com',

    pythonRagUrl: process.env.NODE_ENV === 'development'
      ? 'http://localhost:5000'
      : 'https://rag.yourdomain.com',

    pythonAgentUrl: process.env.NODE_ENV === 'development'
      ? 'http://localhost:5002'
      : 'https://agent.yourdomain.com'
  },

  // Feature flags
  features: {
    enableFunctionCalling: true,
    enableStreaming: true,
    enableRagMemory: true,
    enableToolPanel: true
  },

  // UI settings
  ui: {
    typingSpeed: 30,
    maxMessageLength: 2000,
    sessionTimeout: 24 * 60 * 60 * 1000, // 24 hours
    maxSessions: 50
  },

  // Chat settings
  chat: {
    defaultSystemPrompt: '你现在是李四，说话风格幽默风趣，喜欢用网络流行语。请回答用户的问题，保持友好和有趣的对话风格。',
    maxContextMessages: 10,
    streamingEnabled: true
  }
}

export default config