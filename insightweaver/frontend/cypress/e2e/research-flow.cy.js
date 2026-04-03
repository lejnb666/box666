describe('Research Flow E2E Tests', () => {
  beforeEach(() => {
    cy.visit('/')
    cy.login() // Custom command for authentication
  })

  describe('Research Task Creation', () => {
    it('should create a new research task successfully', () => {
      cy.get('[data-cy="new-research-button"]').click()

      // Fill in research form
      cy.get('[data-cy="research-title"]').type('Test Research Topic')
      cy.get('[data-cy="research-description"]').type('This is a test research description')

      // Select research options
      cy.get('[data-cy="output-format"]').select('MARKDOWN')
      cy.get('[data-cy="tone-style"]').select('FORMAL')

      // Submit form
      cy.get('[data-cy="create-research-submit"]').click()

      // Verify task creation
      cy.get('[data-cy="task-list"]').should('contain', 'Test Research Topic')
      cy.get('[data-cy="task-status"]').should('contain', 'PLANNING')
    })

    it('should validate required fields', () => {
      cy.get('[data-cy="new-research-button"]').click()
      cy.get('[data-cy="create-research-submit"]').click()

      // Check validation messages
      cy.get('[data-cy="title-error"]').should('be.visible')
      cy.get('[data-cy="title-error"]').should('contain', 'Title is required')
    })

    it('should handle long titles gracefully', () => {
      cy.get('[data-cy="new-research-button"]').click()
      const longTitle = 'A'.repeat(600)

      cy.get('[data-cy="research-title"]').type(longTitle)
      cy.get('[data-cy="create-research-submit"]').click()

      cy.get('[data-cy="title-length-error"]').should('be.visible')
    })
  })

  describe('Real-time Progress Monitoring', () => {
    it('should display real-time agent updates', () => {
      // Create a task
      cy.createResearchTask({
        title: 'Real-time Test',
        description: 'Testing real-time updates'
      })

      // Wait for SSE connection
      cy.get('[data-cy="sse-status"]', { timeout: 10000 })
        .should('contain', 'Connected')

      // Monitor agent status updates
      cy.get('[data-cy="agent-status-planning"]')
        .should('contain', 'executing')

      // Check progress updates
      cy.get('[data-cy="progress-bar"]', { timeout: 30000 })
        .should('have.attr', 'value')
        .and('be.greaterThan', 0)
    })

    it('should handle SSE disconnection gracefully', () => {
      cy.createResearchTask({
        title: 'Connection Test',
        description: 'Testing connection resilience'
      })

      // Simulate network disconnection
      cy.window().then((win) => {
        win.dispatchEvent(new Event('offline'))
      })

      // Check disconnection handling
      cy.get('[data-cy="connection-status"]')
        .should('contain', 'Reconnecting')

      // Simulate reconnection
      cy.window().then((win) => {
        win.dispatchEvent(new Event('online'))
      })

      cy.get('[data-cy="connection-status"]')
        .should('contain', 'Connected')
    })
  })

  describe('Task Management', () => {
    beforeEach(() => {
      cy.createResearchTask({
        title: 'Management Test',
        description: 'Testing task management'
      })
    })

    it('should allow cancelling active tasks', () => {
      cy.get('[data-cy="task-action-menu"]').first().click()
      cy.get('[data-cy="cancel-task"]').click()

      // Confirm cancellation
      cy.get('[data-cy="confirm-cancel"]').click()

      // Verify task status
      cy.get('[data-cy="task-status"]').first()
        .should('contain', 'CANCELLED')
    })

    it('should display task history correctly', () => {
      cy.get('[data-cy="view-history"]').first().click()

      cy.get('[data-cy="history-timeline"]').should('be.visible')
      cy.get('[data-cy="history-step"]').should('have.length.greaterThan', 0)
    })

    it('should allow downloading completed reports', () => {
      // Wait for task completion (mock this in real scenario)
      cy.wait(5000)

      cy.get('[data-cy="download-report"]').first().click()

      // Check if file was downloaded
      cy.readFile('cypress/downloads/research-report-*.md')
        .should('exist')
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully', () => {
      // Mock API error
      cy.intercept('POST', '/api/v1/research', {
        statusCode: 500,
        body: { message: 'Server error' }
      }).as('createTaskError')

      cy.get('[data-cy="new-research-button"]').click()
      cy.get('[data-cy="research-title"]').type('Error Test')
      cy.get('[data-cy="create-research-submit"]').click()

      // Check error notification
      cy.get('[data-cy="error-notification"]')
        .should('be.visible')
        .and('contain', 'Failed to create research task')
    })

    it('should handle network timeouts', () => {
      cy.intercept('POST', '/api/v1/research', {
        delay: 30000,
        forceNetworkError: true
      }).as('networkTimeout')

      cy.get('[data-cy="new-research-button"]').click()
      cy.get('[data-cy="research-title"]').type('Timeout Test')
      cy.get('[data-cy="create-research-submit"]').click()

      cy.get('[data-cy="timeout-notification"]')
        .should('be.visible')
    })
  })

  describe('Performance Testing', () => {
    it('should load dashboard within acceptable time', () => {
      cy.visit('/dashboard')

      // Check if main content loads within 3 seconds
      cy.get('[data-cy="dashboard-content"]', { timeout: 3000 })
        .should('be.visible')
    })

    it('should handle multiple concurrent tasks', () => {
      // Create multiple tasks
      for (let i = 0; i < 5; i++) {
        cy.createResearchTask({
          title: `Concurrent Task ${i}`,
          description: `Description for task ${i}`
        })
      }

      // Check if all tasks are displayed
      cy.get('[data-cy="task-item"]').should('have.length', 5)

      // Check performance metrics
      cy.window().then((win) => {
        const perf = win.performance.getEntriesByType('measure')
        expect(perf.length).to.be.greaterThan(0)
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label]').should('have.length.greaterThan', 0)
      cy.get('[role]').should('have.length.greaterThan', 0)
    })

    it('should be keyboard navigable', () => {
      cy.get('[data-cy="new-research-button"]').focus().type('{enter}')
      cy.get('[data-cy="research-title"]').should('be.focused')
    })
  })
})

// Custom commands
declare global {
  namespace Cypress {
    interface Chainable {
      createResearchTask(task: { title: string; description: string }): Chainable
      login(): Chainable
    }
  }
}