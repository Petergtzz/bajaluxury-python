import type { FieldPath, FieldValues, UseFormSetError } from 'react-hook-form'

import { ClientResponseError, isValidationProblems } from './client'

const FALLBACK = 'Something went wrong. Please try again.'

/** Puts a 422's problems on the fields they are about; the rest on `root`. */
export const setValidationErrors = <Values extends FieldValues>(
  error: ClientResponseError,
  setError: UseFormSetError<Values>,
): void => {
  const { detail } = error.body
  if (!isValidationProblems(detail)) {
    setError('root' as FieldPath<Values>, { message: error.message })
    return
  }
  for (const problem of detail) {
    const field = problem.loc.slice(1).join('.') || 'root'
    setError(field as FieldPath<Values>, { type: problem.type, message: problem.msg })
  }
}

/** A sentence to show for a failed call. */
export const getErrorMessage = (error: unknown): string =>
  error instanceof ClientResponseError &&
  error.status < 500 &&
  typeof error.body.detail === 'string'
    ? error.body.detail
    : FALLBACK
