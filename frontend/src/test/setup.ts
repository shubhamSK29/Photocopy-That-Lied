import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock fetch globally since the API service uses it.  `stubGlobal` also works
// in the browser-oriented TypeScript configuration, where Node's `global`
// identifier is intentionally unavailable.
vi.stubGlobal('fetch', vi.fn())

// Mock environment variable
vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
