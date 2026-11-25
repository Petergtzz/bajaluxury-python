import type { Currency } from '@/lib/api/types'

/** How amounts are shown: in which currency, and the rate to get there. */
export type Display = {
  /** What the books are kept in, and what the API sends. */
  company: Currency
  /** What the reader chose to read them in. */
  shown: Currency
  /** The company's currency per US dollar. */
  usdRate: number
}

/**
 * An amount from the books in the reader's currency, to the cent, rounded half
 * up as the server converts statements. Only for showing: nothing converted
 * is ever sent back.
 */
export function toShown(amount: number, { company, shown, usdRate }: Display): number {
  if (shown === company || !(usdRate > 0)) return amount
  const converted = shown === 'USD' ? amount / usdRate : amount * usdRate
  // Rounded on the magnitude, so a refund rounds like the charge it undoes.
  return (Math.sign(converted) * Math.round(Math.abs(converted) * 100 + 1e-9)) / 100
}
