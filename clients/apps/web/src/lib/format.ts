/**
 * Money and dates, written the same way on every page.
 *
 * The API sends amounts as decimal numbers in the company's currency
 * (1250.5 is MX$1,250.50), and dates as `YYYY-MM-DD`.
 */

export function formatMoney(amount: number, currency: string): string {
  // English as written in Canada: the same digits as the US, but dollars are
  // "US$", so they can't be mistaken for pesos next to an "MX$".
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

/** "$1,250.50": money with the sign written by hand, where the currency is on screen. */
export function formatAmount(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

const parts = (value: string): [number, number, number] | null => {
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return year && month && day ? [year, month, day] : null
}

/**
 * "4 Mar 2026". Read by hand: `new Date('2026-03-04')` is UTC midnight, which
 * is the day before anywhere west of Greenwich.
 */
export function formatDate(value: string): string {
  const date = parts(value)
  if (!date) return value
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(date[0], date[1] - 1, date[2]))
}

/**
 * The day a moment fell on where the company is, as formatDate says it. A
 * timestamp's own date is UTC's, which is tomorrow by the evening in Los Cabos.
 */
export const formatMomentDay = (moment: string, timezone: string): string =>
  formatDate(todayIn(timezone, new Date(moment)))

/** "12 February" over its day's rows, with the year only when it isn't this one. */
export function formatDayHeading(value: string, today: string): string {
  const date = parts(value)
  if (!date) return value
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'long',
    ...(String(date[0]) !== today.slice(0, 4) && { year: 'numeric' }),
  }).format(new Date(date[0], date[1] - 1, date[2]))
}

/** Today as `YYYY-MM-DD` where the company is, not where the browser is. */
export function todayIn(timezone: string, now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now)
}

/** Neighbours that share a key, in the order they came: days in a sorted list. */
export const groupConsecutive = <Item, Key>(
  items: Item[],
  keyOf: (item: Item) => Key,
): { key: Key; items: Item[] }[] => {
  const groups: { key: Key; items: Item[] }[] = []
  for (const item of items) {
    const last = groups.at(-1)
    const key = keyOf(item)
    if (last && last.key === key) last.items.push(item)
    else groups.push({ key, items: [item] })
  }
  return groups
}

/** Stored lowercase, shown like a sentence: "credit card" is "Credit card". */
export const sentence = (text: string | null | undefined): string =>
  text ? text.charAt(0).toUpperCase() + text.slice(1) : ''

/** "1 property", "5 properties". */
export const counted = (count: number, one: string, many: string): string =>
  `${count} ${count === 1 ? one : many}`

/** "1–31 Jul 2026", "28 Jun – 3 Jul 2026", "1 Dec 2025 – 31 Jan 2026": two days as one span. */
export function formatRange(from: string, to: string): string {
  const a = parts(from)
  const b = parts(to)
  if (!a || !b) return `${from} – ${to}`
  const [start, end] = [new Date(a[0], a[1] - 1, a[2]), new Date(b[0], b[1] - 1, b[2])]
  const day = new Intl.DateTimeFormat('en-GB', { day: 'numeric' })
  const dayMonth = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' })
  const full = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  if (a[0] !== b[0]) return `${full.format(start)} – ${full.format(end)}`
  if (a[1] !== b[1]) return `${dayMonth.format(start)} – ${full.format(end)}`
  if (a[2] === b[2]) return full.format(end)
  return `${day.format(start)}–${full.format(end)}`
}
