import { describe, expect, it } from 'vitest'

import type { Checklist } from '@/lib/api/types'

import { describeChecklist, describeProgress, splitByDay } from './checklists'

const item = (is_checked: boolean, id = String(Math.random())) => ({
  id,
  description: 'Water tank',
  position: 1,
  is_checked,
  note: null,
  checked_at: null,
})

const checklist = (patch: Partial<Checklist> = {}): Checklist => ({
  id: 'c1',
  property_id: 'p1',
  type: 'check_in',
  created_by_id: null,
  created_at: '2026-11-20T15:00:00Z',
  completed_at: null,
  emailed_to: [],
  emailed_cc: [],
  items: [item(true), item(false), item(true)],
  ...patch,
})

describe('checklists', () => {
  it('counts what is ticked', () => {
    expect(describeProgress(checklist())).toBe('2 of 3')
  })

  it('pins walks under way and gathers the rest by the company’s day', () => {
    const open = checklist({ id: 'open' })
    // 03:00 UTC is still the evening before in Los Cabos.
    const late = checklist({ id: 'late', completed_at: '2026-11-21T03:00:00Z' })
    const morning = checklist({ id: 'morning', completed_at: '2026-11-20T16:00:00Z' })
    const earlier = checklist({ id: 'earlier', completed_at: '2026-11-19T16:00:00Z' })

    const { open: pinned, days } = splitByDay(
      [open, late, morning, earlier],
      'America/Mazatlan',
    )

    expect(pinned.map((one) => one.id)).toEqual(['open'])
    expect(days.map((day) => [day.date, day.checklists.map((one) => one.id)])).toEqual([
      ['2026-11-20', ['late', 'morning']],
      ['2026-11-19', ['earlier']],
    ])
  })

  it('says what a walk was and who heard about it', () => {
    expect(describeChecklist(checklist())).toBe('Check-in')
    expect(
      describeChecklist(
        checklist({
          type: 'weekly',
          completed_at: '2026-11-20T16:00:00Z',
          emailed_to: ['ana@example.com', 'luis@example.com'],
        }),
      ),
    ).toBe('Weekly · sent to ana@example.com and 1 more')
  })
})
