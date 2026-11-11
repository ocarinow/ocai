import { defineEventHandler, getRouterParam, getRequestWebStream } from 'h3'
import { managementRequest } from '../../../utils/management.ts'
import { SessionFailure } from '@ocarinow/nuxt-platform/server/session'

export default defineEventHandler(event => managementRequest(event, true, async (client) => {
  const stream = getRequestWebStream(event) as ReadableStream<Uint8Array> | undefined
  if (!stream) throw new SessionFailure(422)
  const reader = stream.getReader()
  const chunks: Uint8Array[] = []
  let size = 0
  const timer = setTimeout(() => { void reader.cancel() }, 5000)
  let body: unknown
  try {
    while (true) {
      const next = await reader.read()
      if (next.done) break
      size += next.value.byteLength
      if (size > 2048) throw new SessionFailure(422)
      chunks.push(next.value)
    }
    body = JSON.parse(Buffer.concat(chunks).toString('utf8')) as unknown
  } catch { throw new SessionFailure(422) }
  finally { clearTimeout(timer); await reader.cancel() }
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw new SessionFailure(422)
  const value = body as Record<string, unknown>
  if (Object.keys(value).some(key => !['display_name', 'version'].includes(key)) || typeof value.display_name !== 'string'
    || value.display_name.length > 100 || !value.display_name.trim() || typeof value.version !== 'number'
    || !Number.isSafeInteger(value.version) || value.version < 1) throw new SessionFailure(422)
  return await client.updateOrganization(getRouterParam(event, 'id') ?? '', { display_name: value.display_name.trim(), version: value.version })
}))
