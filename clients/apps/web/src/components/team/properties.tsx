'use client'

import { House, Plus } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { toast } from 'sonner'

import { DialogActions, TextAction } from '@/components/dialog-actions'
import { FieldRow, Panel, PlainInput } from '@/components/dialog-fields'
import { InputError } from '@/components/input-error'
import { ListHeading } from '@/components/list-heading'
import { ListRow, RowMark } from '@/components/list-row'
import { PageAction, PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { useProperties } from '@/hooks/ledger'
import { useSaveProperty } from '@/hooks/settings'
import { getErrorMessage } from '@/lib/api/errors'
import type { Property } from '@/lib/api/types'
import { counted, sentence } from '@/lib/format'
import { METHODS } from '@/lib/ledger/filters'
import {
  describeBalance,
  draftFromProperty,
  type PropertyDraft,
  sortForSettings,
  toNewPropertyBody,
  toPropertyChanges,
} from '@/lib/settings/properties'

import { SettingsListState } from '@/components/settings/settings-list-state'

/**
 * The houses: what each is called, where it is, and which payments come out of
 * its owner's balance with us. A house no longer managed is archived, not
 * deleted: its ledger stays.
 */
export function Properties() {
  const properties = useProperties()
  const [dialog, setDialog] = useState<{
    property: Property | null
    key: number
  } | null>(null)
  const [open, setOpen] = useState(false)
  const openDialog = (property: Property | null) => {
    setDialog({ property, key: Date.now() })
    setOpen(true)
  }
  const items = sortForSettings(properties.data ?? [])

  return (
    <>
      <PageHeader
        title="Properties"
        actions={
          <PageAction
            label="Add property"
            icon={<Plus className="size-4" />}
            onClick={() => openDialog(null)}
          />
        }
      />

      <ul className="flex flex-col">
        <ListHeading>{counted(items.length, 'property', 'properties')}</ListHeading>

        {items.length === 0 && (
          <li className="py-10 text-center text-sm text-muted-foreground">
            <SettingsListState
              query={properties}
              empty="No properties yet. Add one to start recording transactions against it."
            />
          </li>
        )}

        {items.map((property) => (
          <ListRow
            key={property.id}
            onSelect={() => openDialog(property)}
            label={`${property.name}, ${property.address ?? 'no address yet'}`}
            mark={
              <RowMark className="bg-sky-100 dark:bg-sky-500/20">
                <House className="size-5 text-sky-900 dark:text-sky-100" aria-hidden />
              </RowMark>
            }
            title={property.name}
            meta={
              <span className="truncate">
                {[property.address, describeBalance(property.balance_methods)]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
            }
            trailing={
              property.is_archived ? (
                <span className="shrink-0 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-muted-foreground dark:bg-neutral-800">
                  Archived
                </span>
              ) : undefined
            }
          />
        ))}
      </ul>

      {dialog && (
        <PropertyDialog
          key={dialog.key}
          property={dialog.property}
          open={open}
          onOpenChange={setOpen}
        />
      )}
    </>
  )
}

function PropertyDialog({
  property,
  open,
  onOpenChange,
}: {
  property: Property | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const saveProperty = useSaveProperty()
  const [draft, setDraft] = useState<PropertyDraft>(() => draftFromProperty(property))
  const [error, setError] = useState<string>()
  const busy = saveProperty.isPending

  const set = <K extends keyof PropertyDraft>(field: K, value: PropertyDraft[K]) => {
    setDraft((current) => ({ ...current, [field]: value }))
    setError(undefined)
  }

  const send = async (): Promise<boolean> => {
    if (property === null) {
      const result = toNewPropertyBody(draft)
      if ('error' in result) {
        setError(result.error)
        return false
      }
      await saveProperty.mutateAsync({ propertyId: null, body: result.body })
      return true
    }
    const result = toPropertyChanges(draft, property)
    if ('error' in result) {
      setError(result.error)
      return false
    }
    if (Object.keys(result.body).length > 0) {
      await saveProperty.mutateAsync({
        propertyId: property.id,
        body: result.body,
      })
    }
    return true
  }

  const save = async () => {
    try {
      if (!(await send())) {
        return
      }
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(property ? 'Property saved' : 'Property added')
  }

  const toggleArchived = async (existing: Property) => {
    try {
      await saveProperty.mutateAsync({
        propertyId: existing.id,
        body: { is_archived: !existing.is_archived },
      })
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(existing.is_archived ? 'Property restored' : 'Property archived')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-md"
        // Focusing the name of an existing property would select all of it.
        onOpenAutoFocus={(event) => property && event.preventDefault()}
      >
        <DialogHeader className="text-left">
          <DialogTitle className="text-base leading-4 font-medium">
            {property ? 'Edit property' : 'Add property'}
          </DialogTitle>
        </DialogHeader>

        <form
          className="grid gap-4"
          noValidate
          onSubmit={(event: FormEvent) => {
            event.preventDefault()
            void save()
          }}
        >
          <Panel className="py-1">
            <PlainInput
              id="property-name"
              value={draft.name}
              onChange={(value) => set('name', value)}
              placeholder="Name"
              disabled={busy}
              required
            />
          </Panel>
          <Panel className="py-1">
            <PlainInput
              id="property-address"
              value={draft.address}
              onChange={(value) => set('address', value)}
              placeholder="Address"
              disabled={busy}
            />
          </Panel>

          <div className="grid gap-1">
            <Panel className="py-0">
              {METHODS.map((method) => (
                <FieldRow key={method} label={sentence(method)}>
                  <Checkbox
                    aria-label={sentence(method)}
                    checked={draft.balanceMethods.includes(method)}
                    onCheckedChange={() =>
                      set(
                        'balanceMethods',
                        draft.balanceMethods.includes(method)
                          ? draft.balanceMethods.filter((one) => one !== method)
                          : [...draft.balanceMethods, method],
                      )
                    }
                    disabled={busy}
                  />
                </FieldRow>
              ))}
            </Panel>
            <p className="px-1 text-xs text-muted-foreground">
              Expenses paid this way come out of the owner’s balance with us. A change
              applies to what is recorded from now on.
            </p>
          </div>

          <InputError message={error} className="text-center" />

          <Button
            type="submit"
            disabled={busy}
            className="h-12 w-full rounded-full text-base font-semibold"
          >
            {busy && <Spinner className="size-5" />}
            {property ? 'Save changes' : 'Add property'}
          </Button>
          {property && (
            <DialogActions>
              <TextAction onClick={() => void toggleArchived(property)} disabled={busy}>
                {property.is_archived ? 'Restore' : 'Archive'}
              </TextAction>
            </DialogActions>
          )}
        </form>
      </DialogContent>
    </Dialog>
  )
}
