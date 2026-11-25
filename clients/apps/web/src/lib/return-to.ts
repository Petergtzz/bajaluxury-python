/** Where to go after logging in: only a path on this site, never elsewhere. */
export const getSafeReturnTo = (value: string | null | undefined): string =>
  value && value.startsWith('/') && !value.startsWith('//') && !value.startsWith('/\\')
    ? value
    : '/'
