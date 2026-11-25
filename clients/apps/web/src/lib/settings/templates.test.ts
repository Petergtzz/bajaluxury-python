import { describe, expect, it } from 'vitest'

import type { TemplateItem } from '@/lib/api/types'

import {
  describeTemplate,
  draftFromItems,
  isUnchanged,
  moveItem,
  newItemDraft,
  toTemplateItems,
} from './templates'

const saved: TemplateItem[] = [
  { id: 'a', type: 'check_in', description: 'Keys in the lockbox', position: 1 },
  { id: 'b', type: 'check_in', description: 'Pool is clean', position: 2 },
]

describe('template drafts', () => {
  it('start from what is saved, or one blank row', () => {
    expect(draftFromItems(saved).map((item) => [item.id, item.text])).toEqual([
      ['a', 'Keys in the lockbox'],
      ['b', 'Pool is clean'],
    ])
    expect(draftFromItems([]).map((item) => item.text)).toEqual([''])
  })

  it('send kept items by id, new ones without, and leave blank rows out', () => {
    const [keys, pool] = draftFromItems(saved)
    const items = [
      { ...pool!, text: ' Pool and jacuzzi ' },
      { ...newItemDraft(), text: 'Gas' },
      newItemDraft(),
      keys!,
    ]
    expect(toTemplateItems(items)).toEqual([
      { id: 'b', description: 'Pool and jacuzzi' },
      { description: 'Gas' },
      { id: 'a', description: 'Keys in the lockbox' },
    ])
  })

  it('know when nothing changed, a moved item included', () => {
    const items = draftFromItems(saved)
    expect(isUnchanged([...items, newItemDraft()], saved)).toBe(true)
    expect(isUnchanged(moveItem(items, 0, 1), saved)).toBe(false)
    expect(moveItem(items, 0, -1)).toBe(items)
  })

  it('say how long a list is', () => {
    expect(describeTemplate(saved)).toBe('2 items')
    expect(describeTemplate([])).toBe('Nothing on it yet')
  })
})
