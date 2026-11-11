import type { paths } from './schema'

export type SystemStatus = paths['/management/v1/status']['get']['responses'][200]['content']['application/json']
export type Organization = paths['/management/v1/organizations/{organization_id}']['get']['responses'][200]['content']['application/json']
export type CurrentIdentity = paths['/management/v1/me']['get']['responses'][200]['content']['application/json']
export type OrganizationPatch = paths['/management/v1/organizations/{organization_id}']['patch']['requestBody']['content']['application/json']
export type Fetcher = (url: string, init?: RequestInit) => Promise<Response>

export class ManagementApiError extends Error {
  readonly status: number
  readonly requestId: string | null
  constructor(status: number, requestId: string | null) {
    super('The management request could not be completed. Please try again.')
    this.name = 'ManagementApiError'
    this.status = status
    this.requestId = requestId
  }
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function object(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null && !Array.isArray(value) }
function organization(value: unknown): Organization {
  if (!object(value) || typeof value.id !== 'string' || !uuid.test(value.id)
    || typeof value.display_name !== 'string' || value.display_name.length < 1 || value.display_name.length > 100
    || typeof value.version !== 'number' || !Number.isSafeInteger(value.version) || value.version < 1
    || typeof value.can_update !== 'boolean') throw new Error('Invalid organization response.')
  return { id: value.id, display_name: value.display_name, version: value.version, can_update: value.can_update }
}
function identity(value: unknown): CurrentIdentity {
  if (!object(value) || typeof value.principal_id !== 'string' || !uuid.test(value.principal_id)
    || !Array.isArray(value.organizations) || value.organizations.length > 100) throw new Error('Invalid identity response.')
  return { principal_id: value.principal_id, organizations: value.organizations.map(organization) }
}
function status(value: unknown): SystemStatus {
  if (!object(value) || value.service !== 'ocai-gateway' || value.stage !== 'foundation' || value.inference_ready !== false) throw new Error('Invalid status response.')
  return { service: value.service, stage: value.stage, inference_ready: value.inference_ready }
}
function resourcePath(id: string): string {
  if (!uuid.test(id)) throw new ManagementApiError(422, null)
  return '/organizations/' + id
}

export function createManagementClient(baseUrl = '/api/management', fetcher: Fetcher = fetch) {
  async function request<T>(path: string, parse: (value: unknown) => T, options: { signal?: AbortSignal; body?: OrganizationPatch; csrf?: string } = {}): Promise<{ value: T; requestId: string | null }> {
    let response: Response
    try {
      response = await fetcher(`${baseUrl.replace(/\/$/, '')}${path}`, {
        method: options.body ? 'PATCH' : 'GET', credentials: 'same-origin', cache: 'no-store',
        headers: options.body ? { 'content-type': 'application/json', ...(options.csrf ? { 'x-csrf-token': options.csrf } : {}) } : {},
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(5000)]) : AbortSignal.timeout(5000),
      })
    } catch { throw new ManagementApiError(0, null) }
    const rawId = response.headers.get('x-request-id')
    const requestId = rawId && /^[a-f0-9]{32}$/.test(rawId) ? rawId : null
    if (!response.ok) { await response.body?.cancel(); throw new ManagementApiError(response.status, requestId) }
    try {
      if (!response.body) throw new Error()
      const reader = response.body.getReader()
      const chunks: Uint8Array[] = []
      let size = 0
      try {
        while (true) {
          const next = await reader.read()
          if (next.done) break
          size += next.value.byteLength
          if (size > 65536) throw new Error()
          chunks.push(next.value)
        }
      } finally { await reader.cancel() }
      const bytes = new Uint8Array(size)
      let offset = 0
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length }
      return { value: parse(JSON.parse(new TextDecoder().decode(bytes)) as unknown), requestId }
    } catch { throw new ManagementApiError(502, requestId) }
  }
  return {
    async getStatus(signal?: AbortSignal) {
      const result = await request('/status', status, { signal })
      return { status: result.value, requestId: result.requestId }
    },
    async getMe(signal?: AbortSignal) { return await request('/me', identity, { signal }) },
    async getOrganization(id: string, signal?: AbortSignal) { return await request(resourcePath(id), organization, { signal }) },
    async updateOrganization(id: string, body: OrganizationPatch, csrf?: string) {
      return await request(resourcePath(id), organization, { body, csrf })
    },
  }
}
