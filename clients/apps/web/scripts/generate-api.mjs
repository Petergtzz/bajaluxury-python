// Writes src/lib/api/v1.ts from the API's OpenAPI description.
// `--check` fails instead of writing when the committed file is out of date.
import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import openapiTS, { astToString, COMMENT_HEADER } from 'openapi-typescript'

const app = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const server = resolve(app, '../../../server')
const python = process.env.BAJA_PYTHON ?? resolve(server, '../venv/bin/python')
const output = resolve(app, 'src/lib/api/v1.ts')

const spec = JSON.parse(
  execFileSync(python, ['-m', 'scripts.generate_openapi'], {
    cwd: server,
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  }),
)
// A field with a default is optional in a request, not required.
const source =
  COMMENT_HEADER + astToString(await openapiTS(spec, { defaultNonNullable: false }))

if (process.argv.includes('--check')) {
  let current = ''
  try {
    current = readFileSync(output, 'utf8')
  } catch {}
  if (current !== source) {
    console.error(
      'src/lib/api/v1.ts is out of date with the API. Run `pnpm run generate`.',
    )
    process.exit(1)
  }
} else {
  writeFileSync(output, source)
}
