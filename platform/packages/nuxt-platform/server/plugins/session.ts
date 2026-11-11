import { defineNitroPlugin, useRuntimeConfig } from '#imports'
import { type SessionSettings, validateSettings } from '../session/config.ts'
import { TokenCipher } from '../session/crypto.ts'
import { IdentityClient, discover } from '../session/oidc.ts'
import { ConsoleSessions } from '../session/service.ts'
import { SessionStore } from '../session/store.ts'

export default defineNitroPlugin(async (nitro) => {
  const raw = useRuntimeConfig().session
  if (raw.enabled !== true && String(raw.enabled) !== 'true') return
  let store: SessionStore | undefined
  try {
    const settings: SessionSettings = { ...raw, enabled: true, local: raw.local === true || String(raw.local) === 'true' }
    validateSettings(settings)
    const cipher = new TokenCipher(settings.activeKey, settings.keys)
    store = new SessionStore(settings)
    await store.open()
    const identity = new IdentityClient(await discover(settings), settings)
    const service = new ConsoleSessions(store, cipher, identity)
    nitro.hooks.hook('request', event => { event.context.consoleSessions = { service, settings } })
    const cleanup = setInterval(() => { void service.store.cleanup().catch(() => {}) }, 60000)
    cleanup.unref()
    nitro.hooks.hook('close', async () => { clearInterval(cleanup); await service.store.close() })
  } catch {
    await store?.close()
    throw new Error('Console sessions could not start; verify explicit configuration and dependencies.')
  }
})
