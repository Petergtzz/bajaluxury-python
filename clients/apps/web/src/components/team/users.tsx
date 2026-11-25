'use client'

import { Plus } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { toast } from 'sonner'

import { UserAvatar } from '@/components/account-button'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { DialogActions, TextAction } from '@/components/dialog-actions'
import {
  FieldRow,
  FieldRows,
  Panel,
  PlainInput,
  RowSelect,
  SelectItem,
} from '@/components/dialog-fields'
import { InputError } from '@/components/input-error'
import { ListHeading } from '@/components/list-heading'
import { ListRow } from '@/components/list-row'
import { PageAction, PageHeader } from '@/components/page-header'
import { usePermissions, useUser } from '@/components/session-context'
import { SettingsListState } from '@/components/settings/settings-list-state'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { useProperties } from '@/hooks/ledger'
import { useRemoveUser, useSaveUser } from '@/hooks/settings'
import { useMembers } from '@/hooks/team'
import { getErrorMessage } from '@/lib/api/errors'
import type { Member } from '@/lib/api/types'
import { counted } from '@/lib/format'
import {
  ASSIGNABLE_ROLES,
  type AssignableRole,
  draftFromPerson,
  newPersonDraft,
  type PersonDraft,
  personChanges,
  propertiesLabel,
  ROLE_DESCRIPTIONS,
  ROLE_LABELS,
  toPersonBody,
} from '@/lib/team'

import { PropertyChecklist } from './property-checklist'

/**
 * Everyone who can log in, and which houses a homeowner sees.
 *
 * There are no invitations: adding someone is all it takes, as they log in with
 * a code sent to their address. Only an owner changes who is here; a manager
 * reads the list.
 */
export function Users() {
  const user = useUser()
  const { ownsCompany } = usePermissions()
  const members = useMembers()
  const properties = useProperties().data ?? []
  const items = members.data ?? []
  const names = (ids: string[]) =>
    ids.map((id) => properties.find((property) => property.id === id)?.name ?? '')
  const [dialog, setDialog] = useState<{ person: Member | null; key: number } | null>(
    null,
  )
  const [open, setOpen] = useState(false)
  const openDialog = (person: Member | null) => {
    setDialog({ person, key: Date.now() })
    setOpen(true)
  }

  return (
    <>
      <PageHeader
        title="Users"
        actions={
          ownsCompany ? (
            <PageAction
              label="Add person"
              icon={<Plus className="size-4" />}
              onClick={() => openDialog(null)}
            />
          ) : undefined
        }
      />

      <ul className="flex flex-col">
        <ListHeading>{counted(items.length, 'person', 'people')}</ListHeading>

        {items.length === 0 && (
          <li className="py-10 text-center text-sm text-muted-foreground">
            <SettingsListState query={members} empty="Nobody yet." />
          </li>
        )}

        {items.map((member) => {
          const you = member.user_id === user.id
          // Owners aren't edited here, and your own name is in Profile.
          const editable = ownsCompany && member.role !== 'owner' && !you
          return (
            <ListRow
              key={member.user_id}
              {...(editable && { onSelect: () => openDialog(member) })}
              label={`${member.name ?? member.email}, ${ROLE_LABELS[member.role]}`}
              mark={<UserAvatar user={member} className="size-11" />}
              title={
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate">{member.name ?? member.email}</span>
                  {you && (
                    <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-muted-foreground dark:bg-neutral-800">
                      You
                    </span>
                  )}
                </span>
              }
              meta={
                <span className="truncate">
                  {ROLE_LABELS[member.role]} ·{' '}
                  {propertiesLabel(member.role, names(member.property_ids))}
                </span>
              }
            />
          )
        })}
      </ul>

      {dialog && (
        <PersonDialog
          key={dialog.key}
          person={dialog.person}
          open={open}
          onOpenChange={setOpen}
        />
      )}
    </>
  )
}

function RoleRows({
  role,
  onChange,
  disabled,
}: {
  role: AssignableRole
  onChange: (role: AssignableRole) => void
  disabled: boolean
}) {
  return (
    <div className="grid gap-1">
      <FieldRows>
        <FieldRow label="Role">
          <RowSelect
            label="Role"
            value={role}
            onValueChange={(value) => onChange(value as AssignableRole)}
            placeholder="Select"
            disabled={disabled}
          >
            {ASSIGNABLE_ROLES.map((option) => (
              <SelectItem key={option} value={option}>
                {ROLE_LABELS[option]}
              </SelectItem>
            ))}
          </RowSelect>
        </FieldRow>
      </FieldRows>
      <p className="px-1 text-xs text-muted-foreground">{ROLE_DESCRIPTIONS[role]}</p>
    </div>
  )
}

/** Someone to add, or someone already here to change or remove. */
function PersonDialog({
  person,
  open,
  onOpenChange,
}: {
  person: Member | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const properties = useProperties().data ?? []
  const save = useSaveUser()
  const remove = useRemoveUser()
  const [draft, setDraft] = useState<PersonDraft>(() =>
    person ? draftFromPerson(person) : newPersonDraft(),
  )
  const [error, setError] = useState<string>()
  const [confirming, setConfirming] = useState(false)
  const [removeError, setRemoveError] = useState<string>()
  const busy = save.isPending || remove.isPending
  const name = person ? (person.name ?? person.email) : ''

  const set = <K extends keyof PersonDraft>(field: K, value: PersonDraft[K]) => {
    setDraft((current) => ({ ...current, [field]: value }))
    setError(undefined)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const send = async (): Promise<string | undefined> => {
      if (person === null) {
        const result = toPersonBody(draft)
        if ('error' in result) return result.error
        await save.mutateAsync({ userId: null, body: result.body })
        return undefined
      }
      const result = personChanges(person, draft)
      if ('error' in result) return result.error
      if (Object.keys(result.body).length > 0) {
        await save.mutateAsync({ userId: person.user_id, body: result.body })
      }
      return undefined
    }
    try {
      const problem = await send()
      if (problem) {
        setError(problem)
        return
      }
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(
      person
        ? `${name} saved`
        : `${draft.name.trim() || draft.email.trim()} can log in now`,
    )
  }

  const confirmRemove = async () => {
    if (!person) return
    try {
      await remove.mutateAsync(person.user_id)
    } catch (failure) {
      setRemoveError(getErrorMessage(failure))
      return
    }
    setConfirming(false)
    onOpenChange(false)
    toast.success(`${name} removed`)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-h-[calc(100svh-2rem)] overflow-y-auto sm:max-w-md"
        // Focusing an existing address would select all of it.
        onOpenAutoFocus={(event) => person && event.preventDefault()}
      >
        <DialogHeader className="text-left">
          <DialogTitle className="text-base leading-4 font-medium">
            {person ? name : 'Add person'}
          </DialogTitle>
        </DialogHeader>
        {!person && (
          <p className="text-sm text-muted-foreground">
            They log in with a code emailed to this address. Nothing is sent until they
            ask for one.
          </p>
        )}

        <form className="grid gap-4" noValidate onSubmit={submit}>
          <Panel className="py-1">
            <PlainInput
              id="person-email"
              type="email"
              value={draft.email}
              onChange={(value) => set('email', value)}
              placeholder="Email address"
              autoComplete="off"
              disabled={busy}
              required
            />
          </Panel>
          <Panel className="py-1">
            <PlainInput
              id="person-name"
              value={draft.name}
              onChange={(value) => set('name', value)}
              placeholder="Name"
              autoComplete="off"
              disabled={busy}
            />
          </Panel>
          <RoleRows
            role={draft.role}
            onChange={(role) => set('role', role)}
            disabled={busy}
          />
          {/* Only homeowners see a subset; for a manager a list would be a
              fiction the ledger then ignores. */}
          {draft.role === 'homeowner' && (
            <PropertyChecklist
              properties={properties}
              selected={draft.propertyIds}
              onChange={(ids) => set('propertyIds', ids)}
              disabled={busy}
            />
          )}
          <InputError message={error} className="text-center" />
          <Button
            type="submit"
            disabled={busy}
            className="h-12 w-full rounded-full text-base font-semibold"
          >
            {busy && <Spinner className="size-5" />}
            {person ? 'Save changes' : 'Add person'}
          </Button>
          {person && (
            <DialogActions>
              <TextAction
                destructive
                onClick={() => {
                  setRemoveError(undefined)
                  setConfirming(true)
                }}
                disabled={busy}
              >
                Remove
              </TextAction>
            </DialogActions>
          )}
        </form>
      </DialogContent>

      {person && (
        <ConfirmDialog
          title="Remove person"
          action="Remove person"
          open={confirming}
          onOpenChange={setConfirming}
          onConfirm={() => void confirmRemove()}
          pending={remove.isPending}
          error={removeError}
        >
          {name} will no longer be able to log in, and their Shortcut tokens stop working.
          What they recorded stays.
        </ConfirmDialog>
      )}
    </Dialog>
  )
}
