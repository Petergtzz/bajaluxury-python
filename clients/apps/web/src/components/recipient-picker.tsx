'use client'

import { FieldRow, Panel } from '@/components/dialog-fields'
import { Checkbox } from '@/components/ui/checkbox'
import { Spinner } from '@/components/ui/spinner'
import type { Member } from '@/lib/api/types'
import { addressing, isHomeowner, recipientName } from '@/lib/reports'

/**
 * Everybody who may hear about a property, with a tick beside each.
 *
 * Reports and Inspections ask the same question, so they ask it with the same
 * list. Whether somebody is addressed or copied follows from their role rather
 * than from a second control, and the word beside their name says which they
 * are - before the tick, so the consequence is visible in advance.
 */
export function RecipientPicker({
  choices,
  chosen,
  onToggle,
  loading,
  disabled,
}: {
  /** Everybody who can see the property. */
  choices: Member[]
  /** The user ids that are ticked. */
  chosen: Set<string>
  onToggle: (userId: string) => void
  loading?: boolean
  disabled?: boolean
}) {
  // A ticked row says exactly what saving would do - an owner being ticked is
  // what turns everybody else into a copy. An unticked row says what the
  // person's role makes them, which is what ticking them normally means.
  const picked = choices.filter((one) => chosen.has(one.user_id))
  const kinds = addressing(picked)
  const byRole = (member: Member) => (isHomeowner(member) ? 'to' : 'cc')

  // Only worth saying where there was an owner to tick: otherwise it explains
  // a choice nobody made.
  const straight =
    picked.length > 0 && !picked.some(isHomeowner) && choices.some(isHomeowner)

  return (
    <>
      <Panel className="max-h-64 overflow-y-auto">
        {loading && (
          <p className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
            <Spinner />
            Loading
          </p>
        )}
        {!loading && choices.length === 0 && (
          <p className="py-2 text-sm text-muted-foreground">
            Nobody can see this property yet. Assign it to someone first.
          </p>
        )}
        {choices.map((member) => {
          const ticked = chosen.has(member.user_id)
          const kind = ticked ? kinds[member.user_id] : byRole(member)
          return (
            <FieldRow key={member.user_id} label={recipientName(member)}>
              <span className="flex items-center gap-3">
                <span
                  className={
                    ticked
                      ? 'text-sm text-muted-foreground'
                      : 'text-sm text-muted-foreground/60'
                  }
                >
                  {kind === 'to' ? 'To' : 'Cc'}
                </span>
                <Checkbox
                  aria-label={recipientName(member)}
                  checked={ticked}
                  onCheckedChange={() => onToggle(member.user_id)}
                  disabled={disabled}
                />
              </span>
            </FieldRow>
          )
        })}
      </Panel>

      {straight && (
        <p className="-mt-2 px-1 text-xs text-muted-foreground">
          No owner is ticked, so it is addressed to the people who are.
        </p>
      )}
    </>
  )
}
