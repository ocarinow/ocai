import * as oidc from 'openid-client'
import type { SessionSettings } from './config.ts'

export interface LoginMaterial { verifier: string; nonce: string; state: string; destination: string }
export interface TokenMaterial { subject: string; access: string; refresh: string; idToken: string; expiresIn: number }

/** The transport is pinned to the configured issuer, with bounded time and bodies. */
export async function discover(settings: SessionSettings): Promise<oidc.Configuration> {
  const issuer = new URL(settings.issuer)
  const boundedFetch: oidc.CustomFetch = async (url, options) => {
    const target = new URL(String(url))
    if (target.origin !== issuer.origin || target.username || target.password) throw new Error('Unqualified identity endpoint.')
    const response = await fetch(target, { ...options, body: options.body instanceof Uint8Array ? new Uint8Array(options.body) : options.body, redirect: 'error', signal: AbortSignal.timeout(5000) })
    if (!response.body) throw new Error('Empty identity response.')
    const reader = response.body.getReader()
    const chunks: Uint8Array[] = []
    let length = 0
    try {
      while (true) {
        const next = await reader.read()
        if (next.done) break
        length += next.value.byteLength
        if (length > 262144) throw new Error('Identity response too large.')
        chunks.push(next.value)
      }
    } finally { await reader.cancel() }
    return new Response(Buffer.concat(chunks), { status: response.status, headers: response.headers })
  }
  const config = await oidc.discovery(issuer, settings.clientId,
    { client_secret: settings.clientSecret, id_token_signed_response_alg: 'RS256' },
    oidc.ClientSecretBasic(settings.clientSecret), {
      timeout: 5, [oidc.customFetch]: boundedFetch,
      execute: settings.local ? [oidc.allowInsecureRequests, oidc.enableNonRepudiationChecks] : [oidc.enableNonRepudiationChecks],
    })
  const metadata = config.serverMetadata()
  if (metadata.issuer !== settings.issuer) throw new Error('Unqualified identity issuer.')
  for (const endpoint of [metadata.authorization_endpoint, metadata.token_endpoint, metadata.jwks_uri, metadata.end_session_endpoint]) {
    if (!endpoint || new URL(endpoint).origin !== issuer.origin) throw new Error('Unqualified identity endpoint.')
  }
  return config
}

function tokens(result: Awaited<ReturnType<typeof oidc.authorizationCodeGrant>>, expectedSubject?: string): TokenMaterial {
  const claims = result.claims()
  if (!claims?.sub || claims.sub.length > 255 || (expectedSubject && claims.sub !== expectedSubject)
    || !result.refresh_token || !result.id_token || result.token_type.toLowerCase() !== 'bearer'
    || !Number.isFinite(result.expires_in) || result.expires_in! <= 0 || result.expires_in! > 300) throw new Error('Invalid identity token response.')
  return { subject: claims.sub, access: result.access_token, refresh: result.refresh_token, idToken: result.id_token, expiresIn: result.expires_in! }
}

export class IdentityClient {
  constructor(private readonly config: oidc.Configuration, private readonly settings: SessionSettings) {}
  async authorization(material: LoginMaterial): Promise<string> {
    return oidc.buildAuthorizationUrl(this.config, {
      redirect_uri: this.settings.origin + '/auth/callback', response_type: 'code', scope: 'openid',
      code_challenge: await oidc.calculatePKCECodeChallenge(material.verifier), code_challenge_method: 'S256',
      state: material.state, nonce: material.nonce,
    }).href
  }
  async exchange(url: URL, material: LoginMaterial): Promise<TokenMaterial> {
    return tokens(await oidc.authorizationCodeGrant(this.config, url, {
      pkceCodeVerifier: material.verifier, expectedState: material.state, expectedNonce: material.nonce, idTokenExpected: true,
    }))
  }
  async refresh(material: TokenMaterial): Promise<TokenMaterial> {
    return tokens(await oidc.refreshTokenGrant(this.config, material.refresh), material.subject)
  }
  logoutUrl(): string {
    // No ID token in a browser URL. Local session deletion is already committed.
    return oidc.buildEndSessionUrl(this.config, { client_id: this.settings.clientId, post_logout_redirect_uri: this.settings.origin + '/' }).href
  }
}
