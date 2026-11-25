import { describe, expect, it } from 'vitest'

import type { Member, Report } from '@/lib/api/types'

import {
  describeRecipients,
  describeSchedule,
  describeSend,
  eligibleRecipients,
  ordinal,
} from './reports'

const report = (
  recipients: Array<{ name: string | null; email: string; kind?: 'to' | 'cc' }>,
): Report => ({
  property_id: 'p1',
  property_name: 'Colinas 21',
  recipients: recipients.map(({ kind = 'to', ...recipient }, index) => ({
    user_id: `u${index}`,
    kind,
    ...recipient,
  })),
  last_sent_at: null,
  send_day: 1,
})

const member = (id: string, role: Member['role']): Member => ({
  id,
  user_id: id,
  email: `${id}@example.com`,
  name: null,
  role,
  property_ids: [],
})

describe('describeRecipients', () => {
  it('names the addressees, then counts who is in copy', () => {
    expect(
      describeRecipients(
        report([
          { name: 'Ana', email: 'a@x.com' },
          { name: 'Luis', email: 'l@x.com', kind: 'cc' },
        ]),
      ),
    ).toBe('Monthly to Ana, cc Luis')
    expect(
      describeRecipients(
        report([
          { name: 'Ana', email: 'a@x.com' },
          { name: 'Luis', email: 'l@x.com', kind: 'cc' },
          { name: 'Rosa', email: 'r@x.com', kind: 'cc' },
        ]),
      ),
    ).toBe('Monthly to Ana, cc Luis and 1 other')
    // Nobody is addressed, so nothing is being sent.
    expect(
      describeRecipients(report([{ name: 'Luis', email: 'l@x.com', kind: 'cc' }])),
    ).toBe('Not sending')
  })

  it('names one or two people, and counts the rest', () => {
    expect(describeRecipients(report([]))).toBe('Not sending')
    expect(describeRecipients(report([{ name: 'Ana', email: 'a@x.com' }]))).toBe(
      'Monthly to Ana',
    )
    expect(
      describeRecipients(
        report([
          { name: 'Ana', email: 'a@x.com' },
          { name: 'Carlos', email: 'c@x.com' },
        ]),
      ),
    ).toBe('Monthly to Ana and Carlos')
    expect(
      describeRecipients(
        report([
          { name: 'Ana', email: 'a@x.com' },
          { name: 'Carlos', email: 'c@x.com' },
          { name: null, email: 'd@x.com' },
        ]),
      ),
    ).toBe('Monthly to Ana and 2 others')
  })

  it('falls back to the address of someone with no name', () => {
    expect(describeRecipients(report([{ name: null, email: 'ana@example.com' }]))).toBe(
      'Monthly to ana@example.com',
    )
  })
})

describe('eligibleRecipients', () => {
  const members = [
    member('owner', 'owner'),
    member('manager', 'manager'),
    member('assigned', 'homeowner'),
    member('elsewhere', 'homeowner'),
    member('unloaded', 'homeowner'),
  ]

  it('offers everyone who can see the property', () => {
    const offered = eligibleRecipients(
      members,
      { assigned: ['p1', 'p2'], elsewhere: ['p2'], unloaded: undefined },
      'p1',
    )

    // The property's own homeowner leads: they are who it is addressed to.
    expect(offered.map((each) => each.user_id)).toEqual(['assigned', 'owner', 'manager'])
  })
})

describe('describeSend', () => {
  it('says the month and how many people it went to', () => {
    expect(describeSend('2026-09-01', 1)).toBe(
      'September so far is on its way to 1 person',
    )
    expect(describeSend('2026-12-01', 3)).toBe(
      'December so far is on its way to 3 people',
    )
  })
})

describe('the send day', () => {
  it('reads it the way people say it', () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 28].map(ordinal)).toEqual([
      '1st',
      '2nd',
      '3rd',
      '4th',
      '11th',
      '12th',
      '13th',
      '21st',
      '22nd',
      '23rd',
      '28th',
    ])
  })

  it('says when a report goes out', () => {
    const monthly = report([{ name: 'Ana', email: 'a@x.com' }])
    expect(describeSchedule({ ...monthly, send_day: 5 })).toBe('on the 5th')
  })
})
