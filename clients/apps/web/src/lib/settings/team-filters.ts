import type { ManagedUser, Property, Role } from '@/lib/api/types'

/** Which people show: a role, and the homeowners of one house. Empty is all. */
export type UserFilters = { role: Role | ''; property: string }

const ROLES: Role[] = ['owner', 'manager', 'homeowner']

export const parseUserFilters = (params: URLSearchParams): UserFilters => {
  const role = params.get('role')
  return {
    role: ROLES.includes(role as Role) ? (role as Role) : '',
    property: params.get('property') ?? '',
  }
}

export const serializeUserFilters = (filters: UserFilters): string => {
  const params = new URLSearchParams()
  if (filters.role) params.set('role', filters.role)
  if (filters.property) params.set('property', filters.property)
  return params.toString()
}

/**
 * A house narrows the list to its homeowners: owners and managers see every
 * house, so listing them under one would answer nothing.
 */
export const applyUserFilters = <U extends ManagedUser>(
  users: U[],
  filters: UserFilters,
): U[] =>
  users.filter(
    (user) =>
      (!filters.role || user.role === filters.role) &&
      (!filters.property || user.property_ids.includes(filters.property)),
  )

/** Which houses show: those still managed, those archived, or every one. */
export type PropertyStatus = 'active' | 'archived' | 'all'

const STATUSES: PropertyStatus[] = ['active', 'archived', 'all']

/** Active unless the address says otherwise: the houses managed today. */
export const parsePropertyStatus = (params: URLSearchParams): PropertyStatus => {
  const status = params.get('status')
  return STATUSES.includes(status as PropertyStatus)
    ? (status as PropertyStatus)
    : 'active'
}

export const serializePropertyStatus = (status: PropertyStatus): string =>
  status === 'active' ? '' : `status=${status}`

export const applyPropertyStatus = (
  properties: Property[],
  status: PropertyStatus,
): Property[] =>
  status === 'all'
    ? properties
    : properties.filter((property) => property.is_archived === (status === 'archived'))
