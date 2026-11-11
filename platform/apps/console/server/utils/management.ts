import { createManagementClient, ManagementApiError } from '@ocarinow/management-client'
import { authenticatedSession, safeSession, SessionFailure, runtime } from '@ocarinow/nuxt-platform/server/session'
import { setHeader, type H3Event } from 'h3'
import { useRuntimeConfig } from '#imports'

export async function managementRequest<T>(event: H3Event, mutation: boolean, operation: (client: ReturnType<typeof createManagementClient>) => Promise<{ value: T; requestId: string | null }>): Promise<T> {
  return await safeSession(event, async () => {
    const session = await authenticatedSession(event, mutation)
    const config = useRuntimeConfig(event)
    const upstream = new URL(config.gatewayBaseUrl)
    const local = runtime(event).settings.local
    if (!(upstream.protocol === 'https:' || (local && upstream.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(upstream.hostname))) || upstream.username || upstream.password || upstream.search || upstream.hash) throw new Error('Invalid upstream.')
    const client = createManagementClient(new URL('/management/v1', upstream).href, (url, options) => fetch(url, {
      ...options, redirect: 'error', credentials: 'omit',
      headers: { 'authorization': 'Bearer ' + session.accessToken, ...(options?.body ? { 'content-type': 'application/json' } : {}) },
    }))
    try {
      const result = await operation(client)
      if (result.requestId) setHeader(event, 'x-request-id', result.requestId)
      return result.value
    } catch (error) {
      if (!(error instanceof ManagementApiError)) throw error
      if (error.requestId) setHeader(event, 'x-request-id', error.requestId)
      const code = [401, 403, 404, 409, 422, 503].includes(error.status) ? error.status : 503
      // Retain only controlled status; never forward upstream bodies or exception causes.
      throw new SessionFailure(code)
    }
  })
}
