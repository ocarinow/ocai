import { defineEventHandler, getHeader } from 'h3'
import { runtime, safeSession, readSession, writeCookie, requireOrigin } from '../../session/http.ts'

export default defineEventHandler(event => safeSession(event, async () => {
  const { service, settings } = runtime(event)
  requireOrigin(event, settings)
  const providerLogout = await service.logout(readSession(event, settings), getHeader(event, 'x-csrf-token') ?? '', getHeader(event, 'x-provider-logout') === 'true')
  writeCookie(event, settings, '')
  return { signedOut: true, providerLogout: providerLogout ?? null }
}))
