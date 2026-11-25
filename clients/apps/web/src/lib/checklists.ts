import type { Checklist, ChecklistType } from '@/lib/api/types'
import { groupConsecutive, todayIn } from '@/lib/format'

/** The three lists a property is walked with, in the order a stay runs. */
export const CHECKLIST_TYPES: readonly ChecklistType[] = [
  'check_in',
  'check_out',
  'weekly',
]

export const TYPE_NAMES: Record<ChecklistType, string> = {
  check_in: 'Check-in',
  check_out: 'Check-out',
  weekly: 'Weekly',
}

export type Day = { date: string; checklists: Checklist[] }

/**
 * Walks under way, and the rest gathered into the day they were finished.
 *
 * The day is the company's, so a walk finished late in Los Cabos doesn't land on
 * tomorrow for a reader in Madrid.
 */
export const splitByDay = (
  checklists: Checklist[],
  timezone: string,
): { open: Checklist[]; days: Day[] } => ({
  open: checklists.filter((one) => one.completed_at === null),
  days: groupConsecutive(
    checklists.filter((one) => one.completed_at !== null),
    (one) => todayIn(timezone, new Date(one.completed_at ?? one.created_at)),
  ).map(({ key, items }) => ({ date: key, checklists: items })),
})

/** "6 of 8" - the number a row exists to show. */
export const describeProgress = (checklist: Checklist): string =>
  `${checklist.items.filter((item) => item.is_checked).length} of ${checklist.items.length}`

/** Who a finished walk went to, in the row's quiet line. */
export const describeChecklist = (checklist: Checklist): string => {
  const kind = TYPE_NAMES[checklist.type]
  if (checklist.completed_at === null) return kind
  const [first, ...rest] = checklist.emailed_to
  if (!first) return kind
  return `${kind} · sent to ${first}${rest.length > 0 ? ` and ${rest.length} more` : ''}`
}
