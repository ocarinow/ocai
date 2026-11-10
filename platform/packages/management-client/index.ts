import type { paths } from './schema'

export type SystemStatus = paths['/management/v1/status']['get']['responses'][200]['content']['application/json']
export type Fetcher = (url: string, init?: RequestInit) => Promise<Response>

export class ManagementApiError extends Error {
  readonly status: number
  readonly requestId: string | null
  constructor(status: number, requestId: string | null) {
    super('The management service could not be reached. Please try again.')
    this.name = 'ManagementApiError'
    this.status = status
    this.requestId = requestId
  }
}

function isStatus(value: unknown): value is SystemStatus {
  return typeof value === 'object' && value !== null
    && 'service' in value && value.service === 'ocai-gateway'
    && 'stage' in value && value.stage === 'foundation'
    && 'inference_ready' in value && value.inference_ready === false
}

export function createManagementClient(baseUrl = '/api/management', fetcher: Fetcher = fetch) {
  return {
    async getStatus(signal?: AbortSignal): Promise<{ status: SystemStatus; requestId: string | null }> {
      let response: Response
      try {
        response = await fetcher(`${baseUrl.replace(/\/$/, '')}/status`, {
          method: 'GET', credentials: 'same-origin', cache: 'no-store',
          signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(5000)]) : AbortSignal.timeout(5000),
        })
      } catch {
        throw new ManagementApiError(0, null)
      }
      const rawId = response.headers.get('x-request-id')
      const requestId = rawId && /^[a-f0-9]{32}$/.test(rawId) ? rawId : null
      if (!response.ok) throw new ManagementApiError(response.status, requestId)
      let body: unknown
      try { body = await response.json() } catch { throw new ManagementApiError(502, requestId) }
      if (!isStatus(body)) throw new ManagementApiError(502, requestId)
      // Return the allowlisted fields only, even if upstream adds other metadata.
      return { status: { service: body.service, stage: body.stage, inference_ready: body.inference_ready }, requestId }
    },
  }
}
