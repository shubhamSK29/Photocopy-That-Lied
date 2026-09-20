# Frontend Testing Guide

## Prerequisites

- Node.js 20+ 
- npm or pnpm package manager

## Setup

### Install Dependencies

```bash
cd frontend
npm install
```

This will install the testing dependencies:
- `vitest` - Test runner
- `@testing-library/react` - React testing utilities
- `@testing-library/jest-dom` - Custom Jest matchers
- `@testing-library/user-event` - User interaction simulation
- `jsdom` - DOM implementation for Node.js

**Note**: TypeScript may show "Cannot find module" errors for vitest and testing-library packages until `npm install` is run. These errors are expected in development environments where dependencies haven't been installed yet.

## Running Tests

### Run all tests
```bash
npm test
```

### Run tests in watch mode
```bash
npm test -- --watch
```

### Run tests with UI
```bash
npm run test:ui
```

### Run tests with coverage
```bash
npm run test:coverage
```

## Test Structure

### Test Files
- `src/pages/Upload.test.tsx` - Upload component tests
- `src/pages/Processing.test.tsx` - Processing component tests  
- `src/pages/Results.test.tsx` - Results component tests

### Test Configuration
- `vitest.config.ts` - Vitest configuration
- `src/test/setup.ts` - Test setup and mocks

## Test Coverage

### Upload Component Tests
- Renders upload interface correctly
- Handles file selection via click
- Handles drag and drop
- Shows loading state during upload
- Displays error on upload failure
- Displays configuration information
- Validates file types

### Processing Component Tests
- Renders processing interface correctly
- Shows all processing steps
- Navigates to results when analysis completes
- Handles missing analysis ID gracefully

### Results Component Tests
- Renders results interface correctly
- Displays manipulation evidence score
- Displays data coverage score
- Shows demo fallback mode when active
- Displays detector cards
- Expands detector details on click
- Displays heatmap view controls
- Switches heatmap views
- Displays provenance information
- Displays warnings and limitations
- Navigates to new analysis on button click
- Handles missing analysis ID gracefully
- Displays disclaimer

## Important Notes

### Demo Fallback Verification
The Results component tests specifically verify that "Demo Fallback" appears only when fallback mode is active, ensuring proper labelling of the demo mode.

### API Mocking
All API calls are mocked in `src/test/setup.ts` to avoid dependencies on the backend during testing. The mocks provide realistic responses that match the expected API structure.

### Component Testing Philosophy
- Tests focus on user interactions and UI behavior
- Tests verify proper error handling and loading states
- Tests ensure proper navigation between components
- Tests validate that demo fallback is clearly labelled

## CI/CD Integration

The frontend tests are integrated into the GitHub Actions workflow (`.github/workflows/ci.yml`) and will run automatically on:
- Push to main/develop branches
- Pull requests to main/develop branches

## Troubleshooting

### If tests fail due to missing dependencies:
```bash
npm install
```

### If tests fail due to environment issues:
Make sure Node.js 20+ is installed:
```bash
node --version
```

### If you want to run tests without the backend:
The tests are designed to run independently with mocked API responses, so the backend doesn't need to be running.
