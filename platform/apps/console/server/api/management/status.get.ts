import { createManagementClient } from '@ocarinow/management-client'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  setHeader(event, 'cache-control', 'no-store')
  try {
    const upstream = new URL(config.gatewayBaseUrl)
    if (!['http:', 'https:'].includes(upstream.protocol) || upstream.username || upstream.password || upstream.search || upstream.hash) {
      throw new Error('Invalid upstream configuration')
    }
    // Fixed operation and operator-configured host; never forward caller headers,
    // cookies, query parameters or a caller-selected URL. No redirects or retries.
    const client = createManagementClient(
      new URL('/management/v1', upstream).href,
      (url, init) => fetch(url, { ...init, redirect: 'error', credentials: 'omit' }),
    )
    const result = await client.getStatus()
    if (result.requestId) setHeader(event, 'x-request-id', result.requestId)
    return result.status
  } catch {
    setResponseStatus(event, 503)
    return { error: { code: 'service_unavailable', message: 'Management service unavailable.' } }
  }
})
