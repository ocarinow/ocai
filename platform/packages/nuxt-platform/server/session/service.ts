import { digest, randomId, validId, equalSecret, TokenCipher } from './crypto.ts'
import { type LoginMaterial, type TokenMaterial, IdentityClient } from './oidc.ts'
import { SessionStore } from './store.ts'

export class SessionFailure extends Error {
  readonly status: number
  constructor(status = 503) { super(status === 401 ? 'Sign in to continue.' : status === 403 ? 'Request not permitted.' : 'Sign-in service unavailable.'); this.status = status }
}

function loginMaterial(value: unknown): LoginMaterial {
  if (!value || typeof value !== 'object') throw new SessionFailure()
  const data = value as Record<string, unknown>
  if (![data.verifier, data.nonce, data.state].every(v => typeof v === 'string' && validId(v)) || data.destination !== '/') throw new SessionFailure()
  return data as unknown as LoginMaterial
}
function tokenMaterial(value: unknown): TokenMaterial {
  if (!value || typeof value !== 'object') throw new SessionFailure()
  const data = value as Record<string, unknown>
  if (![data.subject, data.access, data.refresh, data.idToken].every(v => typeof v === 'string' && v.length > 0)
    || typeof data.expiresIn !== 'number') throw new SessionFailure()
  return data as unknown as TokenMaterial
}

/** Browser presentation and server-held API credentials have distinct return shapes. */
export class ConsoleSessions {
  constructor(readonly store: SessionStore, private readonly cipher: TokenCipher, private readonly identity: Pick<IdentityClient, 'authorization' | 'exchange' | 'refresh' | 'logoutUrl'>) {}
  async begin(): Promise<{ url: string; browser: string }> {
    const material: LoginMaterial = { verifier: randomId(), state: randomId(), nonce: randomId(), destination: '/' }
    const browser = randomId()
    const id = digest(material.state)
    const url = await this.identity.authorization(material)
    await this.store.createLogin(id, digest(browser), this.cipher.seal(material, 'login:' + id))
    return { url, browser }
  }
  async callback(url: URL, browser: string, previous?: string): Promise<{ session: string; destination: string }> {
    const states = url.searchParams.getAll('state')
    if (states.length !== 1 || !validId(states[0]!) || !validId(browser)) throw new SessionFailure(401)
    const id = digest(states[0]!)
    const encrypted = await this.store.consumeLogin(id, digest(browser))
    if (!encrypted) throw new SessionFailure(401)
    const material = loginMaterial(this.cipher.open(encrypted, 'login:' + id))
    const issued = await this.identity.exchange(url, material)
    // Prevent fixation and retire any existing browser session on successful login.
    if (previous && validId(previous)) await this.store.revoke(digest(previous))
    const session = randomId()
    const hash = digest(session)
    await this.store.create(hash, this.cipher.seal(issued, 'session:' + hash), randomId(), issued.expiresIn)
    return { session, destination: material.destination }
  }
  async current(session: string): Promise<{ csrf: string; accessToken: string }> {
    if (!validId(session)) throw new SessionFailure(401)
    const id = digest(session)
    const row = await this.store.read(id)
    if (!row) throw new SessionFailure(401)
    if (row.lease_until) throw new SessionFailure()
    try {
      let material = tokenMaterial(this.cipher.open(row.material, 'session:' + id))
      if (row.access_until.getTime() <= Date.now() + 30000) {
        if (!await this.store.lease(id, row.version)) throw new SessionFailure()
        try {
          material = await this.identity.refresh(material)
          if (!await this.store.renewed(id, row.version + 1, this.cipher.seal(material, 'session:' + id), material.expiresIn)) throw new SessionFailure(401)
        } catch {
          // Ambiguous rotated credentials are never retried, including after a crash.
          await this.store.revoke(id)
          throw new SessionFailure(401)
        }
      } else if (!await this.store.touch(id, row.version)) throw new SessionFailure()
      return { csrf: row.csrf, accessToken: material.access }
    } catch (error) {
      if (error instanceof SessionFailure) throw error
      await this.store.revoke(id)
      throw new SessionFailure(401)
    }
  }
  async logout(session: string, csrf: string, provider: boolean): Promise<string | undefined> {
    if (!validId(session)) throw new SessionFailure(401)
    const id = digest(session)
    const row = await this.store.read(id)
    if (!row) throw new SessionFailure(401)
    if (!equalSecret(csrf, row.csrf)) throw new SessionFailure(403)
    // Do not refresh or call the provider before irrevocably deleting local state.
    await this.store.revoke(id)
    return provider ? this.identity.logoutUrl() : undefined
  }
}
