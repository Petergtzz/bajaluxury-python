/** IANA timezones the browser knows, with UTC, which browsers list separately. */
export const getTimezones = (): string[] => {
  const zones = Intl.supportedValuesOf('timeZone')
  return zones.includes('UTC') ? zones : ['UTC', ...zones]
}

export const getBrowserTimezone = (): string =>
  Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
