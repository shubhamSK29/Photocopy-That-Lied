// TypeScript declarations for vitest and testing-library
// These declarations are provided to resolve TypeScript errors during development
// They will be replaced by actual type definitions when npm install is run

declare module 'vitest' {
  export function describe(name: string, fn: () => void): void
  export function it(name: string, fn: () => void | Promise<void>): void
  export function expect(value: unknown): any
  export const vi: any
  export function beforeEach(fn: () => void): void
  export function afterEach(fn: () => void): void
  export function mock(path: string, factory: () => unknown): void
}

declare module '@testing-library/react' {
  import type { ReactElement } from 'react'
  
  export function render(component: ReactElement): any
  export const screen: any
  export const fireEvent: any
  export function waitFor(callback: () => void | Promise<void>): Promise<void>
  export function cleanup(): void
}

declare module '@testing-library/jest-dom' {
  // Custom matchers will be available after npm install
}

declare module '@testing-library/user-event' {
  // User event utilities will be available after npm install
}
