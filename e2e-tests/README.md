# E2E Tests for AI Money

Browser-based functional tests using Playwright for the AI Money application.

## Setup

Install dependencies:

```bash
npm install
```

## Running Tests

### Headless Mode (Default)

Run all tests in headless mode:

```bash
npm test
```

### Headed Mode (Visual)

Run tests with browser visible:

```bash
npm run test:headed
```

### Interactive UI Mode

Run tests with Playwright's interactive UI:

```bash
npm run test:ui
```

### Debug Mode

Run tests in debug mode with step-through execution:

```bash
npm run test:debug
```

## View Test Results

After running tests, view the HTML report:

```bash
npm run report
```

## Test Coverage

The networth feature has 4 critical E2E tests covering complete user journeys.

## Test Structure

```
e2e-tests/
├── tests/
│   └── networth.spec.ts       # Net worth feature tests
├── playwright.config.ts        # Playwright configuration
├── package.json                # Dependencies and scripts
└── tsconfig.json               # TypeScript configuration
```

## Configuration

The tests are configured to:
- Run against `http://localhost:3000` (frontend)
- Use Chromium browser
- Take screenshots on failure
- Generate HTML reports
- Automatically start the frontend dev server if not running

## Prerequisites

Before running tests, ensure:
1. Backend is running on `http://localhost:8000`
2. Frontend dev server will be started automatically by Playwright if not already running
3. PostgreSQL database is running and configured

## CI/CD Integration

Tests are configured for CI environments:
- Retries: 2 attempts in CI, 0 in local development
- Workers: 1 in CI, parallel in local development
- Screenshots: Only on failure
- Traces: On first retry
