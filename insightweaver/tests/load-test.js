import { check, group, sleep } from 'k6'
import http from 'k6/http'
import { Trend, Rate, Counter } from 'k6/metrics'

// Custom metrics
const responseTimeTrend = new Trend('response_time')
const successRate = new Rate('success_rate')
const requestCount = new Counter('request_count')

// Test configuration
export const options = {
  // Test scenarios
  scenarios: {
    // Steady state test
    steady_state: {
      executor: 'constant-vus',
      vus: 50,
      duration: '5m',
      env: 'STEADY_STATE=true'
    },
    // Spike test
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 100 },
        { duration: '2m', target: 100 },
        { duration: '1m', target: 0 }
      ],
      env: 'SPIKE_TEST=true'
    },
    // Stress test
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },
        { duration: '5m', target: 100 },
        { duration: '3m', target: 150 },
        { duration: '2m', target: 0 }
      ],
      env: 'STRESS_TEST=true'
    }
  },

  // Thresholds
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.95']
  },

  // Global settings
  vus: 10,
  duration: '30s',
  maxRedirects: 10,
  userAgent: 'InsightWeaver-LoadTest/1.0',
  insecureSkipTLSVerify: true,
  noConnectionReuse: false
}

// Test data
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080/api/v1'
const FRONTEND_URL = __ENV.FRONTEND_URL || 'http://localhost:3000'

// Authentication token (would be obtained via login in real scenario)
const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'test-token'

// Request headers
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${AUTH_TOKEN}`,
  'User-Agent': 'InsightWeaver-LoadTest/1.0'
}

// Test functions
function createResearchTask(title, description) {
  const payload = JSON.stringify({
    title,
    description,
    outputFormat: 'MARKDOWN',
    toneStyle: 'FORMAL',
    maxSources: 10,
    deadlineMinutes: 30
  })

  const response = http.post(`${BASE_URL}/research`, payload, { headers })

  check(response, {
    'create task status is 200': (r) => r.status === 200,
    'create task has task ID': (r) => r.json('id') !== undefined,
    'create task has status': (r) => r.json('status') !== undefined
  })

  successRate.add(response.status === 200)
  responseTimeTrend.add(response.timings.duration)
  requestCount.add(1)

  return response.json('id')
}

function getTaskStatus(taskId) {
  const response = http.get(`${BASE_URL}/research/${taskId}`, { headers })

  check(response, {
    'get task status is 200': (r) => r.status === 200,
    'get task has status': (r) => r.json('status') !== undefined
  })

  return response.json()
}

function getTaskHistory() {
  const response = http.get(`${BASE_URL}/research`, { headers })

  check(response, {
    'get history status is 200': (r) => r.status === 200,
    'get history returns array': (r) => Array.isArray(r.json())
  })

  return response.json()
}

function cancelTask(taskId) {
  const response = http.post(`${BASE_URL}/research/${taskId}/cancel`, {}, { headers })

  check(response, {
    'cancel task status is 200': (r) => r.status === 200
  })

  return response.json()
}

// Frontend performance tests
function testFrontendLoad() {
  const response = http.get(FRONTEND_URL)

  check(response, {
    'frontend loads successfully': (r) => r.status === 200,
    'frontend has HTML content': (r) => r.body.includes('<!DOCTYPE html>'),
    'frontend loads within time limit': (r) => r.timings.duration < 3000
  })

  return response
}

function testFrontendAssets() {
  // Test CSS loading
  const cssResponse = http.get(`${FRONTEND_URL}/assets/index.css`)
  check(cssResponse, {
    'CSS loads successfully': (r) => r.status === 200
  })

  // Test JS loading
  const jsResponse = http.get(`${FRONTEND_URL}/assets/index.js`)
  check(jsResponse, {
    'JS loads successfully': (r) => r.status === 200
  })
}

// AI Engine performance tests
function testAIEngineHealth() {
  const response = http.get(`${__ENV.AI_ENGINE_URL || 'http://localhost:8000'}/status`)

  check(response, {
    'AI engine health check passes': (r) => r.status === 200,
    'AI engine reports healthy status': (r) => r.json('system.status') === 'healthy'
  })

  return response.json()
}

// Main test function
export default function () {
  group('Frontend Performance', () => {
    testFrontendLoad()
    testFrontendAssets()
  })

  group('Backend API Performance', () => {
    // Test task creation
    const taskId = createResearchTask(
      `Load Test Task ${__VU}_${__ITER}`,
      'This is a load test task for performance evaluation'
    )

    // Test task status polling
    if (taskId) {
      sleep(1) // Wait for task processing

      for (let i = 0; i < 5; i++) {
        getTaskStatus(taskId)
        sleep(2)
      }

      // Test task cancellation
      cancelTask(taskId)
    }

    // Test history retrieval
    getTaskHistory()
  })

  group('AI Engine Performance', () => {
    testAIEngineHealth()
  })

  group('Concurrent Operations', () => {
    // Simulate multiple concurrent users
    const concurrentTasks = []

    for (let i = 0; i < 3; i++) {
      const taskId = createResearchTask(
        `Concurrent Task ${i}_${__VU}_${__ITER}`,
        `Concurrent task description ${i}`
      )

      if (taskId) {
        concurrentTasks.push(taskId)
      }
    }

    // Monitor all concurrent tasks
    concurrentTasks.forEach((taskId, index) => {
      sleep(index * 0.5) // Stagger the requests
      getTaskStatus(taskId)
    })
  })

  // Simulate user think time
  sleep(Math.random() * 3 + 1)
}

// Setup function - runs once before all VUs
export function setup() {
  console.log('Setting up load test...')
  console.log(`Base URL: ${BASE_URL}`)
  console.log(`Frontend URL: ${FRONTEND_URL}`)

  // Health check
  const healthResponse = http.get(`${BASE_URL}/actuator/health`)
  if (healthResponse.status !== 200) {
    throw new Error(`Backend health check failed: ${healthResponse.status}`)
  }

  console.log('Load test setup completed successfully')
  return { startTime: new Date().toISOString() }
}

// Teardown function - runs once after all VUs
export function teardown(data) {
  console.log('Load test teardown...')
  console.log(`Test duration: ${new Date() - new Date(data.startTime)}ms`)

  // Generate summary report
  const summary = {
    testDuration: new Date() - new Date(data.startTime),
    baseUrl: BASE_URL,
    scenarios: options.scenarios,
    thresholds: options.thresholds
  }

  console.log('Load test completed:', JSON.stringify(summary, null, 2))
}