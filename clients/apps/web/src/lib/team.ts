import type { schemas } from '@/lib/api/client'
import type { ManagedUser, Role } from '@/lib/api/types'

export const ROLE_LABELS: Record<Role, string> = {
  owner: 'Owner',
  manager: 'Manager',
  homeowner: 'Homeowner',
}

export type AssignableRole = Exclude<Role, 'owner'>

export const ROLE_DESCRIPTIONS: Record<AssignableRole, string> = {
  manager:
    'Records and changes transactions, guest expenses and checklists, sends invoices and reports, and manages the houses.',
  homeowner:
    'Sees the ledger, balance, checklists and statements of the houses assigned to them, and changes nothing.',
}

/** The roles someone can be given; ownership isn't handed over here. */
export const ASSIGNABLE_ROLES: AssignableRole[] = ['manager', 'homeowner']

const sameIds = (a: string[], b: string[]) =>
  a.length === b.length && [...a].sort().join() === [...b].sort().join()

export type PersonDraft = {
  email: string
  name: string
  role: AssignableRole
  propertyIds: string[]
}

export const newPersonDraft = (): PersonDraft => ({
  email: '',
  name: '',
  // Manager, not the most privileged answer or the most restricted one.
  role: 'manager',
  propertyIds: [],
})

export const draftFromPerson = (person: ManagedUser): PersonDraft => ({
  email: person.email,
  name: person.name ?? '',
  role: person.role === 'homeowner' ? 'homeowner' : 'manager',
  propertyIds: person.property_ids,
})

const EMAIL = /^[^\s@]+@[^\s@]+$/

/** The create request: someone who can log in with that address from now on. */
export const toPersonBody = (
  draft: PersonDraft,
): { body: schemas['ManagedUserCreate'] } | { error: string } => {
  const email = draft.email.trim()
  if (!EMAIL.test(email)) {
    return { error: 'Enter the email address they log in with.' }
  }
  return {
    body: {
      email,
      name: draft.name.trim() || null,
      role: draft.role,
      // Owners and managers see every house: a list would be a fiction.
      property_ids: draft.role === 'homeowner' ? draft.propertyIds : [],
    },
  }
}

/**
 * What saving someone has to do: only what changed. Houses belong to
 * homeowners only; making one a manager drops theirs on its own, so they are
 * only sent for someone who ends up a homeowner.
 */
export const personChanges = (
  person: ManagedUser,
  draft: PersonDraft,
): { body: schemas['ManagedUserUpdate'] } | { error: string } => {
  const email = draft.email.trim()
  if (!EMAIL.test(email)) {
    return { error: 'Enter the email address they log in with.' }
  }
  const name = draft.name.trim() || null
  return {
    body: {
      ...(email !== person.email && { email }),
      ...(name !== person.name && { name }),
      ...(draft.role !== person.role && { role: draft.role }),
      ...(draft.role === 'homeowner' &&
        !sameIds(person.property_ids, draft.propertyIds) && {
          property_ids: draft.propertyIds,
        }),
    },
  }
}

/** "Colinas 21, Colinas 30", or what someone without assignments sees. */
export const propertiesLabel = (role: Role, names: string[]): string => {
  if (role !== 'homeowner') {
    return 'All properties'
  }
  return names.length === 0 ? 'No house yet' : names.join(', ')
}
