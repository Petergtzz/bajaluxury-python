import { useMutation } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'

export function useRequestLoginCode() {
  return useMutation({
    mutationFn: (email: string) =>
      unwrap(api.POST('/v1/auth/login-code/request', { body: { email } })),
  })
}

export function useAuthenticateLoginCode() {
  return useMutation({
    mutationFn: (body: { email: string; code: string }) =>
      unwrap(api.POST('/v1/auth/login-code/authenticate', { body })),
  })
}

export function useLogout() {
  return useMutation({ mutationFn: () => unwrap(api.POST('/v1/auth/logout')) })
}
