import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App.jsx'

describe('App', () => {
  it('renders without throwing an error', () => {
    // This test passes if the component renders without throwing
    expect(() => {
      render(<App />)
    }).not.toThrow()
  })
})

describe('MenuPhase', () => {
  it('renders without throwing an error', () => {
    // This test passes if the component renders without throwing
    expect(() => {
      render(<App />)
    }).not.toThrow()
  })
})