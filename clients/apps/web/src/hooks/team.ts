import { useQuery } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'
import type { Member } from '@/lib/api/types'

/** Everyone who can log in, named as the report screens name them. */
export const useMembers = () =>
  useQuery({
    queryKey: ['users'],
    queryFn: () => unwrap(api.GET('/v1/users/')),
    select: (users): Member[] => users.map((user) => ({ ...user, user_id: user.id })),
  })

/** Each homeowner's properties, by user: which reports they may receive. */
export const useHomeownerProperties = (
  members: Member[],
): Record<string, string[] | undefined> =>
  Object.fromEntries(
    members
      .filter((member) => member.role === 'homeowner')
      .map((member) => [member.user_id, member.property_ids]),
  )
