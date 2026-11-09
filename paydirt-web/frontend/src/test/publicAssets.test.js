import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('declared public assets', () => {
  it('provides a valid SVG for the favicon declared by the application', () => {
    const html = readFileSync(resolve('index.html'), 'utf8')
    const document = new DOMParser().parseFromString(html, 'text/html')
    const icon = document.querySelector('link[rel="icon"]')
    expect(icon).not.toBeNull()
    expect(icon.type).toBe('image/svg+xml')
    const href = icon.getAttribute('href')
    expect(href).toMatch(/^\/[^/].*\.svg$/)
    const publicRoot = resolve('public')
    const asset = resolve(publicRoot, `.${href}`)
    expect(existsSync(asset), `Declared favicon ${href} must exist in public/`).toBe(true)
    const svg = new DOMParser().parseFromString(readFileSync(asset, 'utf8'), 'image/svg+xml')
    expect(svg.querySelector('parsererror')).toBeNull()
    expect(svg.documentElement.localName).toBe('svg')
    expect(svg.documentElement.namespaceURI).toBe('http://www.w3.org/2000/svg')
  })
})
