import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// jsdom has no layout; input-otp asks what is under a point to spot password
// manager badges, and nothing is.
if (typeof document !== 'undefined') {
  document.elementFromPoint ??= () => null

  // Radix Select and Checkbox measure and capture the pointer; jsdom does neither.
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Element.prototype.hasPointerCapture ??= () => false
  Element.prototype.releasePointerCapture ??= () => {}
  Element.prototype.scrollIntoView ??= () => {}

  // next-themes asks whether the system prefers dark; jsdom has no media queries.
  window.matchMedia ??= (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList
}

afterEach(() => {
  cleanup()
})
