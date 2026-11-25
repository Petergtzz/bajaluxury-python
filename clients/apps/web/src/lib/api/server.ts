import { cookies, headers } from 'next/headers'
import { cache } from 'react'

import { createClient } from './client'
import { decodeUser, getAPIURL, USER_HEADER } from './session'

/** The client for server components: the visitor's cookies go along. */
export const getServerSideAPI = cache(async () =>
  createClient(getAPIURL(), { Cookie: (await cookies()).toString() }),
)

/** Who is logged in, as the proxy found for this request. */
export const getAuthenticatedUser = cache(async () =>
  decodeUser((await headers()).get(USER_HEADER)),
)
