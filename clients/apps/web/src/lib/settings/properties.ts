import type { schemas } from '@/lib/api/client'
import type { PaymentMethod, Property } from '@/lib/api/types'
import { METHODS } from '@/lib/ledger/filters'

export type PropertyDraft = {
  name: string
  address: string
  /** Whose expenses come out of the owner's balance with us. */
  balanceMethods: PaymentMethod[]
}

export const draftFromProperty = (property: Property | null): PropertyDraft => ({
  name: property?.name ?? '',
  address: property?.address ?? '',
  // Cash, as the API starts a new property: what we pay from the float.
  balanceMethods: property?.balance_methods ?? ['cash'],
})

const NAME_REQUIRED = { error: 'Enter a name.' } as const

/** In the order the ledger lists them, so a change reads as one. */
const ordered = (methods: PaymentMethod[]) =>
  METHODS.filter((one) => methods.includes(one))

/** The create request for a new property, a blank address sent as null. */
export const toNewPropertyBody = (
  draft: PropertyDraft,
): { body: schemas['PropertyCreate'] } | { error: string } => {
  const name = draft.name.trim()
  return name
    ? {
        body: {
          name,
          address: draft.address.trim() || null,
          balance_methods: ordered(draft.balanceMethods),
        },
      }
    : NAME_REQUIRED
}

/** The update request for an existing property: only what changed. */
export const toPropertyChanges = (
  draft: PropertyDraft,
  property: Property,
): { body: schemas['PropertyUpdate'] } | { error: string } => {
  const result = toNewPropertyBody(draft)
  if ('error' in result) {
    return result
  }
  const { name, address, balance_methods } = result.body
  const methods = balance_methods ?? []
  const sameMethods =
    methods.length === property.balance_methods.length &&
    methods.every((one) => property.balance_methods.includes(one))
  return {
    body: {
      ...(name !== property.name && { name }),
      ...(address !== property.address && { address }),
      ...(!sameMethods && { balance_methods: methods }),
    },
  }
}

/** What a property's row says about its balance: which payments come out of it. */
export const describeBalance = (methods: PaymentMethod[]): string =>
  methods.length === 0
    ? 'No expense comes out of the balance'
    : `Balance pays ${ordered(methods).join(', ')}`

/** Archived ones last: they are kept for their history, not for use. */
export const sortForSettings = <T extends { is_archived: boolean }>(items: T[]): T[] => [
  ...items.filter((item) => !item.is_archived),
  ...items.filter((item) => item.is_archived),
]
