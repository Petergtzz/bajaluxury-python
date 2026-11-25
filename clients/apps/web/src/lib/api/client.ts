import createOpenAPIFetchClient, {
  type FetchResponse,
  type HeadersOptions,
  type ParseAsResponse,
} from 'openapi-fetch'
import type { ResponseObjectMap, SuccessResponse } from 'openapi-typescript-helpers'

import type { components, paths } from './v1'

export type schemas = components['schemas']

export const createClient = (baseUrl: string, headers?: HeadersOptions) =>
  createOpenAPIFetchClient<paths>({
    baseUrl,
    credentials: 'include',
    headers,
    // Looked up per call, so tests can stub it.
    fetch: (request) => globalThis.fetch(request),
  })

type ValidationProblem = { loc: (string | number)[]; msg: string; type: string }

/** Every error the API sends: `detail` is a list only when a request is invalid. */
export type ErrorBody = { error: string; detail: string | ValidationProblem[] }

export class ClientResponseError extends Error {
  readonly body: ErrorBody
  readonly response: Response

  constructor(body: ErrorBody, response: Response) {
    super(typeof body.detail === 'string' ? body.detail : body.error)
    this.name = 'ClientResponseError'
    this.body = body
    this.response = response
  }

  get status(): number {
    return this.response.status
  }
}

const toErrorBody = (error: unknown, response: Response): ErrorBody =>
  typeof error === 'object' && error !== null && 'error' in error && 'detail' in error
    ? (error as ErrorBody)
    : { error: `HTTP${response.status}`, detail: response.statusText }

/** The body of a successful call, or a ClientResponseError with the API's answer. */
export const unwrap = async <
  T extends Record<string | number, unknown>,
  Options,
  Media extends `${string}/${string}`,
>(
  request: Promise<FetchResponse<T, Options, Media>>,
): Promise<ParseAsResponse<SuccessResponse<ResponseObjectMap<T>, Media>, Options>> => {
  const { data, error, response } = await request
  if (!response.ok) {
    throw new ClientResponseError(toErrorBody(error, response), response)
  }
  return data as ParseAsResponse<SuccessResponse<ResponseObjectMap<T>, Media>, Options>
}

export const isValidationProblems = (
  detail: ErrorBody['detail'],
): detail is ValidationProblem[] => Array.isArray(detail)

/** The browser's client: its own origin, which passes /v1 on to the API. */
export const api = createClient(
  typeof window === 'undefined' ? '' : window.location.origin,
)
