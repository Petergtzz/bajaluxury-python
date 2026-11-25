import type { Member, RecipientKind, Report, SentStatement } from '@/lib/api/types'
import { counted } from '@/lib/format'

/** What a member is called in a list of recipients: their name, or their address. */
export const recipientName = (recipient: { name: string | null; email: string }) =>
  recipient.name ?? recipient.email

/**
 * Who a report goes to, in a line: "Monthly to Ana Ruiz, cc Luis Mena".
 *
 * The people it is addressed to are named; everyone in copy is counted after
 * them, because a row has one line and the addressees are the answer.
 */
const others = (count: number) => counted(count, 'other', 'others')

export const describeRecipients = (report: Report): string => {
  const named = (kind: RecipientKind) =>
    report.recipients.filter((recipient) => recipient.kind === kind).map(recipientName)
  const [first, second, ...rest] = named('to')
  if (!first) {
    return 'Not sending'
  }
  const to = !second
    ? first
    : rest.length === 0
      ? `${first} and ${second}`
      : `${first} and ${others(rest.length + 1)}`
  const copies = named('cc')
  const cc =
    copies.length === 0
      ? ''
      : copies.length === 1
        ? `, cc ${copies[0]}`
        : `, cc ${copies[0]} and ${others(copies.length - 1)}`
  return `Monthly to ${to}${cc}`
}

/**
 * Who may receive a property's report: everyone who can see that property.
 *
 * Owners and managers see every property; a homeowner sees the ones assigned to
 * them. A homeowner whose properties haven't loaded yet is left out rather than
 * offered and then refused by the server.
 *
 * The property's own people come first, because they are who it is addressed
 * to and a list reads top down.
 */
export const eligibleRecipients = (
  members: Member[],
  homeownerProperties: Record<string, string[] | undefined>,
  propertyId: string,
): Member[] => {
  const eligible = members.filter((member) =>
    isHomeowner(member)
      ? homeownerProperties[member.user_id]?.includes(propertyId) === true
      : true,
  )
  return [
    ...eligible.filter(isHomeowner),
    ...eligible.filter((member) => !isHomeowner(member)),
  ]
}

/** The 28th is the last day every month has, February included. */
export const SEND_DAYS = Array.from({ length: 28 }, (_, index) => index + 1)

/** A day of the month as people say it: 1st, 2nd, 3rd, 21st. */
export const ordinal = (day: number): string => {
  const teen = day % 100 >= 11 && day % 100 <= 13
  const suffix = teen ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' }[day % 10] ?? 'th')
  return `${day}${suffix}`
}

/** When a report goes out: "on the 5th". */
export const describeSchedule = (report: Report): string =>
  `on the ${ordinal(report.send_day)}`

/** The people a document is for. Everyone else works here. */
export const isHomeowner = (member: Member) => member.role === 'homeowner'

/**
 * How the chosen people are addressed: owners receive it, the rest are copied.
 *
 * Nobody picks between To and Cc - the role already says which one somebody is.
 * When no owner is chosen, the people who are become the addressees: an email
 * needs someone on its To line, and a manager who ticks only their own team
 * means exactly that.
 */
export const addressing = (chosen: Member[]): Record<string, RecipientKind> => {
  const owned = chosen.some(isHomeowner)
  return Object.fromEntries(
    chosen.map((member) => [member.user_id, !owned || isHomeowner(member) ? 'to' : 'cc']),
  )
}

/** The month a manual send covers, as a sentence: "September is on its way to Ana." */
export const describeSend = (month: string, recipientCount: number): string => {
  const [year, index] = month.slice(0, 10).split('-').map(Number)
  const name = new Intl.DateTimeFormat('en-GB', {
    month: 'long',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year ?? 1970, (index ?? 1) - 1, 1)))
  const people = counted(recipientCount, 'person', 'people')
  return `${name} so far is on its way to ${people}`
}

/** "August 2026", from the first day of a month. */
export const monthName = (month: string): string => {
  const [year, index] = month.slice(0, 10).split('-').map(Number)
  return new Intl.DateTimeFormat('en-GB', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year ?? 1970, (index ?? 1) - 1, 1)))
}

/** Who a sent statement went to: "to Ana Ruiz, cc Luis Mena". */
export const describeSent = (send: SentStatement): string => {
  if (send.to.length === 0) {
    return send.error ?? 'Not sent'
  }
  const to = `to ${send.to.join(', ')}`
  return send.cc.length === 0 ? to : `${to}, cc ${send.cc.join(', ')}`
}

/**
 * The months a statement can be sent for: the last complete one, back a year.
 *
 * Counted in the company's own clock rather than the reader's, so a
 * manager in Madrid and one in Tijuana are offered the same list.
 */
export const sendableMonths = (timezone: string, count = 12): string[] => {
  const here = new Date(new Date().toLocaleString('en-US', { timeZone: timezone }))
  const months: string[] = []
  for (let back = 1; back <= count; back += 1) {
    const month = new Date(Date.UTC(here.getFullYear(), here.getMonth() - back, 1))
    months.push(month.toISOString().slice(0, 10))
  }
  return months
}
