import { defineEventHandler } from 'h3'
import { runtime, safeSession, readSession, writeCookie } from '../../session/http.ts'
import { SessionFailure } from '../../session/service.ts'

export default defineEventHandler(event => safeSession(event, async () => {
  const { service, settings } = runtime(event)
  const session = readSession(event, settings)
  if (!session) return { authenticated: false, csrf: null }
  try {
    const current = await service.current(session)
    return { authenticated: true, csrf: current.csrf }
  } catch (error) {
    if (!(error instanceof SessionFailure) || error.status !== 401) throw error
    writeCookie(event, settings, '')
    return { authenticated: false, csrf: null }
  }
}))
