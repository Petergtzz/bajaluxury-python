'use client'

import { ChevronDown, ChevronUp, Plus, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { PlainInput } from '@/components/dialog-fields'
import { FormDialog } from '@/components/form-dialog'
import { Button } from '@/components/ui/button'
import { useSaveTemplate } from '@/hooks/settings'
import { getErrorMessage } from '@/lib/api/errors'
import type { ChecklistType, TemplateItem } from '@/lib/api/types'
import { TYPE_NAMES } from '@/lib/checklists'
import {
  draftFromItems,
  filledItems,
  type ItemDraft,
  isUnchanged,
  moveItem,
  newItemDraft,
  toTemplateItems,
} from '@/lib/settings/templates'
import { cn } from '@/lib/utils'

/**
 * One type's list, edited whole: reword an item, move it, add one, take one
 * off. Saving sends the list as it now stands. Walks already started keep the
 * wording they were given.
 */
export function TemplateDialog({
  type,
  items: saved,
  open,
  onOpenChange,
}: {
  type: ChecklistType
  items: TemplateItem[]
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const save = useSaveTemplate()
  const [items, setItemsState] = useState<ItemDraft[]>(() => draftFromItems(saved))
  const [error, setError] = useState<string>()
  const busy = save.isPending

  const setItems = (next: ItemDraft[]) => {
    setItemsState(next)
    setError(undefined)
  }

  const editItem = (key: string, changes: Partial<ItemDraft>) =>
    setItems(items.map((item) => (item.key === key ? { ...item, ...changes } : item)))

  const submit = async () => {
    if (filledItems(items).length === 0) {
      setError('A checklist needs at least one item.')
      return
    }
    try {
      if (!isUnchanged(items, saved)) {
        await save.mutateAsync({ type, items: toTemplateItems(items) })
      }
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(`${TYPE_NAMES[type]} saved`)
  }

  return (
    <FormDialog
      title={TYPE_NAMES[type]}
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={() => void submit()}
      submitLabel="Save changes"
      pending={busy}
      error={error}
      className="max-h-[calc(100svh-2rem)] overflow-y-auto"
      contentProps={{
        // Focusing the first item would select all of it.
        onOpenAutoFocus: (event) => event.preventDefault(),
      }}
    >
      <div className="grid gap-2">
        <p className="px-1 text-sm text-muted-foreground">
          Items, in the order they are walked
        </p>
        <ul className="grid gap-2">
          {items.map((item, index) => (
            <ItemRow
              key={item.key}
              item={item}
              index={index}
              count={items.length}
              disabled={busy}
              onChange={(changes) => editItem(item.key, changes)}
              onMove={(to) => setItems(moveItem(items, index, to))}
              onRemove={() => setItems(items.filter((one) => one.key !== item.key))}
            />
          ))}
        </ul>
        <Button
          type="button"
          variant="ghost"
          disabled={busy}
          onClick={() => setItems([...items, newItemDraft()])}
          className="h-10 justify-start gap-2 rounded-xl px-3 text-sm text-muted-foreground"
        >
          <Plus className="size-4" />
          Add item
        </Button>
      </div>
    </FormDialog>
  )
}

function ItemRow({
  item,
  index,
  count,
  disabled,
  onChange,
  onMove,
  onRemove,
}: {
  item: ItemDraft
  index: number
  count: number
  disabled: boolean
  onChange: (changes: Partial<ItemDraft>) => void
  onMove: (to: number) => void
  onRemove: () => void
}) {
  const name = item.text.trim() || `Item ${index + 1}`

  return (
    <li className="flex items-center gap-1 rounded-xl bg-neutral-50 pr-1 pl-4 dark:bg-neutral-800/50">
      <PlainInput
        id={`checklist-item-${item.key}`}
        value={item.text}
        onChange={(value) => onChange({ text: value })}
        placeholder="What to look at"
        disabled={disabled}
      />
      <IconButton
        label={`Move ${name} up`}
        disabled={disabled || index === 0}
        onClick={() => onMove(index - 1)}
      >
        <ChevronUp className="size-4" />
      </IconButton>
      <IconButton
        label={`Move ${name} down`}
        disabled={disabled || index === count - 1}
        onClick={() => onMove(index + 1)}
      >
        <ChevronDown className="size-4" />
      </IconButton>
      <IconButton label={`Remove ${name}`} disabled={disabled} onClick={onRemove}>
        <X className="size-4" />
      </IconButton>
    </li>
  )
}

function IconButton({
  label,
  pressed,
  disabled,
  onClick,
  children,
}: {
  label: string
  pressed?: boolean
  disabled: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={pressed}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'flex size-9 shrink-0 items-center justify-center rounded-full transition-colors',
        'text-muted-foreground hover:bg-neutral-200/70 disabled:opacity-40 dark:hover:bg-neutral-800',
        pressed &&
          'bg-neutral-900 text-white hover:bg-neutral-900 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-100',
      )}
    >
      {children}
    </button>
  )
}
