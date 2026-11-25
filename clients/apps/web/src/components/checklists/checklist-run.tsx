'use client'

import { Check, MessageSquarePlus, MessageSquareText } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { PageHeader } from '@/components/page-header'
import { RowMenu } from '@/components/row-menu'
import { usePermissions } from '@/components/session-context'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useChecklist, useDeleteChecklist, useSetChecklistItem } from '@/hooks/checklists'
import { useProperties } from '@/hooks/ledger'
import { getErrorMessage } from '@/lib/api/errors'
import type { ChecklistItem } from '@/lib/api/types'
import { describeProgress, TYPE_NAMES } from '@/lib/checklists'
import { cn } from '@/lib/utils'

import { FinishChecklistDialog } from './finish-checklist-dialog'
import { NoteDialog } from './note-dialog'

/**
 * One walk, as a page rather than a dialog.
 *
 * Somebody is holding this in one hand while they look at a water tank, so a
 * row is a big target and the whole row is the tick. Nothing here asks twice.
 */
export function ChecklistRun({ checklistId }: { checklistId: string }) {
  const router = useRouter()
  const checklist = useChecklist(checklistId)
  const properties = useProperties()
  const setItem = useSetChecklistItem(checklistId)
  const remove = useDeleteChecklist()
  const { manages } = usePermissions()
  const [confirming, setConfirming] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [noting, setNoting] = useState<ChecklistItem | null>(null)

  if (checklist.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="size-6" />
      </div>
    )
  }
  if (checklist.isError || !checklist.data) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        This checklist isn’t here.
      </p>
    )
  }

  const walk = checklist.data
  const name =
    properties.data?.find((one) => one.id === walk.property_id)?.name ??
    TYPE_NAMES[walk.type]
  const finished = walk.completed_at !== null
  // A homeowner reads a walk; they never tick, finish or drop one.
  const readOnly = finished || !manages
  const missed = walk.items.filter((item) => !item.is_checked)

  const tick = async (item: ChecklistItem) => {
    try {
      await setItem.mutateAsync({
        itemId: item.id,
        body: { is_checked: !item.is_checked },
      })
    } catch (error) {
      toast.error(getErrorMessage(error))
    }
  }

  const drop = async () => {
    try {
      await remove.mutateAsync(checklistId)
    } catch (error) {
      toast.error(getErrorMessage(error))
      return
    }
    setConfirming(false)
    router.push('/checklists')
  }

  return (
    <>
      <PageHeader
        title={name}
        actions={
          manages && !finished ? (
            <RowMenu
              label="More for this checklist"
              items={[
                {
                  label: 'Delete checklist',
                  destructive: true,
                  onSelect: () => setConfirming(true),
                },
              ]}
            />
          ) : undefined
        }
      />

      <p className="-mt-6 text-[15px] text-muted-foreground">
        {TYPE_NAMES[walk.type]} · {describeProgress(walk)}
        {finished ? ' · finished' : ''}
      </p>

      <ul className="flex flex-col gap-2">
        {walk.items.map((item) => (
          <ItemRow
            key={item.id}
            item={item}
            locked={readOnly}
            disabled={readOnly || setItem.isPending}
            onToggle={() => void tick(item)}
            onNote={() => setNoting(item)}
          />
        ))}
      </ul>

      {!readOnly && (
        <div className="flex flex-col gap-3">
          {missed.length > 0 && (
            <p className="text-center text-sm text-muted-foreground">
              {missed.length === 1
                ? '1 item isn’t ticked. Finishing is fine - the report will say so.'
                : `${missed.length} items aren’t ticked. Finishing is fine - the report will say so.`}
            </p>
          )}
          <Button
            onClick={() => setFinishing(true)}
            className="h-12 w-full rounded-full text-base font-semibold"
          >
            Finish checklist
          </Button>
        </div>
      )}

      {noting && (
        <NoteDialog
          key={noting.id}
          checklistId={checklistId}
          item={noting}
          open
          onOpenChange={(open) => !open && setNoting(null)}
        />
      )}

      {finishing && (
        <FinishChecklistDialog
          checklist={walk}
          propertyName={name}
          open
          onOpenChange={setFinishing}
        />
      )}

      <ConfirmDialog
        title="Delete checklist"
        action="Delete checklist"
        open={confirming}
        onOpenChange={setConfirming}
        onConfirm={() => void drop()}
        pending={remove.isPending}
      >
        This walk and everything ticked on it will be dropped. The property can be walked
        again from the start.
      </ConfirmDialog>
    </>
  )
}

function ItemRow({
  item,
  locked,
  disabled,
  onToggle,
  onNote,
}: {
  item: ChecklistItem
  locked: boolean
  disabled: boolean
  onToggle: () => void
  onNote: () => void
}) {
  return (
    <li className="flex items-center gap-1 rounded-2xl bg-neutral-50 pr-3 dark:bg-neutral-800/50">
      <button
        type="button"
        onClick={onToggle}
        disabled={disabled}
        aria-pressed={item.is_checked}
        className="flex min-w-0 flex-1 items-center gap-4 rounded-2xl px-4 py-4 text-left transition-colors hover:bg-neutral-100 disabled:hover:bg-transparent dark:hover:bg-neutral-800/70 dark:disabled:hover:bg-transparent"
      >
        <span
          className={cn(
            'flex size-7 shrink-0 items-center justify-center rounded-full border-2 transition-colors',
            item.is_checked
              ? 'border-emerald-600 bg-emerald-600 text-white dark:border-emerald-500 dark:bg-emerald-500'
              : 'border-neutral-300 dark:border-neutral-600',
          )}
        >
          {item.is_checked && <Check className="size-4" aria-hidden />}
        </span>
        <span className="min-w-0 flex-1">
          <span
            className={cn(
              'block text-base',
              item.is_checked
                ? 'text-muted-foreground line-through'
                : 'text-neutral-900 dark:text-neutral-100',
            )}
          >
            {item.description}
          </span>
          {item.note && (
            <span className="mt-0.5 block text-sm text-muted-foreground">
              {item.note}
            </span>
          )}
        </span>
      </button>
      {/* A note button nobody can use is just clutter: a reader sees the note itself. */}
      {!locked && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-10 shrink-0 rounded-full text-muted-foreground"
          aria-label={
            item.note
              ? `Edit note on ${item.description}`
              : `Add a note to ${item.description}`
          }
          onClick={onNote}
        >
          {item.note ? (
            <MessageSquareText className="size-5 text-foreground" />
          ) : (
            <MessageSquarePlus className="size-5" />
          )}
        </Button>
      )}
    </li>
  )
}
