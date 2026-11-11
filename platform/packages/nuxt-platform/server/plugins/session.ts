import { defineNitroPlugin, useRuntimeConfig } from '#imports'
import { type SessionSettings, validateSettings } from '../session/config.ts'
import { TokenCipher } from '../session/crypto.ts'
import { IdentityClient, discover } from '../session/oidc.ts'
import { ConsoleSessions } from '../session/service.ts'
import { SessionStore } from '../session/store.ts'

export default defineNitroPlugin(async (nitro) => {
  const raw = useRuntimeConfig().session
  if (raw.enabled !== true && String(raw.enabled) !== 'true') return
  let stage = 'configuration'
  let store: SessionStore | undefined
  try {
    const settings: SessionSettings = { ...raw, keys: typeof raw.keys === 'string' ? raw.keys : JSON.stringify(raw.keys), enabled: true, local: raw.local === true || String(raw.local) === 'true' }
    validateSettings(settings)
    stage = 'encryption'
    const cipher = new TokenCipher(settings.activeKey, settings.keys)
    stage = 'storage'
    store = new SessionStore(settings)
    await store.open()
    stage = 'identity'
    const identity = new IdentityClient(await discover(settings), settings)
    const service = new ConsoleSessions(store, cipher, identity)
    nitro.hooks.hook('request', event => { event.context.consoleSessions = { service, settings } })
    const cleanup = setInterval(() => { void service.store.cleanup().catch(() => {}) }, 60000)
    cleanup.unref()
    nitro.hooks.hook('close', async () => { clearInterval(cleanup); await service.store.close() })
  } catch {
    await store?.close()
    // Nitro catches plugin rejections and may still listen; an enabled broken
    // identity boundary must instead fail this Node service's startup.
    console.error('Console session startup failed (' + stage + ').')
    process.exit(1)
  }
})
