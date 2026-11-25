import type { schemas } from '@/lib/api/client'
import type { TemplateItem } from '@/lib/api/types'
import { counted } from '@/lib/format'

/**
 * An item while it is being edited.
 *
 * `id` is what the server already has, and null for one being written now. The
 * separate `key` is what React lists by: a new item has no id to be keyed on,
 * and keying by position makes the field you are typing in jump when a row
 * above it moves.
 */
export type ItemDraft = { key: string; id: string | null; text: string }

let nextKey = 0
const newKey = () => `item-${(nextKey += 1)}`

export const newItemDraft = (): ItemDraft => ({ key: newKey(), id: null, text: '' })

/** A template as it stands, ready to edit; an empty one starts with a blank row. */
export const draftFromItems = (items: TemplateItem[]): ItemDraft[] =>
  items.length === 0
    ? [newItemDraft()]
    : items.map((item) => ({
        key: `saved-${item.id}`,
        id: item.id,
        text: item.description,
      }))

/** The items worth saving: a row nobody typed in is not an item. */
export const filledItems = (items: ItemDraft[]): ItemDraft[] =>
  items.filter((item) => item.text.trim() !== '')

export const moveItem = (items: ItemDraft[], from: number, to: number): ItemDraft[] => {
  if (to < 0 || to >= items.length) return items
  const moved = [...items]
  const [item] = moved.splice(from, 1)
  if (item === undefined) return items
  moved.splice(to, 0, item)
  return moved
}

/** Whether saving would change anything: the same items, words and order. */
export const isUnchanged = (items: ItemDraft[], saved: TemplateItem[]): boolean => {
  const wanted = filledItems(items)
  return (
    wanted.length === saved.length &&
    wanted.every(
      (item, index) =>
        item.id === saved[index]?.id && item.text.trim() === saved[index]?.description,
    )
  )
}

/** The whole list as the API takes it: kept items by id, new ones without. */
export const toTemplateItems = (items: ItemDraft[]): schemas['TemplateItemWrite'][] =>
  filledItems(items).map((item) => ({
    ...(item.id === null ? {} : { id: item.id }),
    description: item.text.trim(),
  }))

/** What a template's row says under its name. */
export const describeTemplate = (items: TemplateItem[]): string =>
  items.length === 0 ? 'Nothing on it yet' : counted(items.length, 'item', 'items')
