// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

// Custom command for login
Cypress.Commands.add('login', (username = 'test@example.com', password = 'password') => {
  cy.session([username, password], () => {
    cy.visit('/login')
    cy.get('[data-cy="login-email"]').type(username)
    cy.get('[data-cy="login-password"]').type(password)
    cy.get('[data-cy="login-submit"]').click()
    cy.url().should('include', '/dashboard')
  })
})

// Custom command for creating research tasks
Cypress.Commands.add('createResearchTask', (task) => {
  cy.get('[data-cy="new-research-button"]').click()
  cy.get('[data-cy="research-title"]').type(task.title)
  cy.get('[data-cy="research-description"]').type(task.description)
  cy.get('[data-cy="create-research-submit"]').click()
})

// Custom command for API mocking
Cypress.Commands.add('mockApiResponse', (method, url, response) => {
  cy.intercept(method, url, response).as(`api_${method}_${url}`)
})

// Custom command for SSE simulation
Cypress.Commands.add('simulateSSEEvent', (eventName, data) => {
  cy.window().then((win) => {
    const event = new MessageEvent('message', {
      data: JSON.stringify({ event: eventName, data })
    })
    win.dispatchEvent(event)
  })
})

// Custom command for performance measurement
Cypress.Commands.add('measurePerformance', (label, fn) => {
  cy.window().then((win) => {
    win.performance.mark(`${label}-start`)
    fn()
    win.performance.mark(`${label}-end`)
    win.performance.measure(label, `${label}-start`, `${label}-end`)
  })
})

// Custom command for accessibility testing
Cypress.Commands.add('checkAccessibility', () => {
  // Check for required accessibility attributes
  cy.get('button').each(($el) => {
    if ($el.text().trim() && !$el.attr('aria-label')) {
      cy.wrap($el).should('have.attr', 'aria-label')
    }
  })

  // Check for proper heading structure
  cy.get('h1, h2, h3, h4, h5, h6').then(($headings) => {
    const levels = $headings.map((i, el) => parseInt(el.tagName.charAt(1))).get()
    expect(levels).to.have.length.greaterThan(0)
  })
})

// Custom command for responsive testing
Cypress.Commands.add('testResponsive', (breakpoints) => {
  breakpoints.forEach(({ width, height, name }) => {
    cy.viewport(width, height)
    cy.document().then((doc) => {
      cy.log(`Testing ${name} viewport: ${width}x${height}`)
    })
  })
})

// Custom command for error boundary testing
Cypress.Commands.add('testErrorBoundary', (errorTrigger) => {
  cy.get(errorTrigger).click()
  cy.get('[data-cy="error-boundary"]').should('be.visible')
  cy.get('[data-cy="error-message"]').should('contain', 'Something went wrong')
})

// Custom command for file upload testing
Cypress.Commands.add('uploadFile', (fileName, fileType = '') => {
  cy.fixture(fileName).then((fileContent) => {
    cy.get('[data-cy="file-upload"]').upload({
      fileContent: fileContent.toString(),
      fileName,
      mimeType: fileType
    })
  })
})

// Custom command for drag and drop testing
Cypress.Commands.add('dragAndDrop', (subject, target) => {
  cy.get(subject).trigger('dragstart')
  cy.get(target).trigger('drop')
})

// Custom command for keyboard navigation testing
Cypress.Commands.add('keyboardNavigate', (keys) => {
  keys.forEach((key) => {
    cy.get('body').type(`{${key}}`)
  })
})

// Custom command for local storage testing
Cypress.Commands.add('clearLocalStorage', () => {
  cy.clearLocalStorage()
})

// Custom command for network condition testing
Cypress.Commands.add('setNetworkConditions', (conditions) => {
  cy.window().then((win) => {
    if (win.navigator.connection) {
      Object.assign(win.navigator.connection, conditions)
    }
  })
})

// Custom command for memory usage testing
Cypress.Commands.add('checkMemoryUsage', () => {
  cy.window().then((win) => {
    if (win.performance.memory) {
      const memory = win.performance.memory
      expect(memory.usedJSHeapSize).to.be.lessThan(memory.totalJSHeapSize)
    }
  })
})