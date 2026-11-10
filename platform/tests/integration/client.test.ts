import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { test } from 'node:test'
import { createManagementClient, ManagementApiError } from '../../packages/management-client/index.ts'

const status = { service: 'ocai-gateway', stage: 'foundation', inference_ready: false }

test('typed client permits only its fixed operation and safe response fields', async () => {
  const client = createManagementClient('/api/management/', async (url, options) => {
    assert.equal(url, '/api/management/status')
    assert.equal(options?.cache, 'no-store')
    assert.equal(options?.credentials, 'same-origin')
    assert.ok(options?.signal)
    return Response.json({ ...status, secret: 'private' }, { headers: { 'x-request-id': 'a'.repeat(32) } })
  })
  assert.deepEqual(await client.getStatus(), { status, requestId: 'a'.repeat(32) })
})

test('network, upstream, malformed JSON and schema errors never expose upstream text', async () => {
  const cases = [
    async () => { throw new Error('private-network-detail') },
    async () => new Response('private-error-detail', { status: 500 }),
    async () => new Response('private-invalid-json'),
    async () => Response.json({ ...status, inference_ready: true, secret: 'private' }),
  ]
  for (const fetcher of cases) {
    await assert.rejects(createManagementClient('/api/management', fetcher).getStatus(), error => {
      assert.ok(error instanceof ManagementApiError)
      assert.equal(error.message.includes('private'), false)
      return true
    })
  }
})

test('incoming request references are bounded before display', async () => {
  const client = createManagementClient('', async () => Response.json(status, { headers: { 'x-request-id': 'sensitive upstream value' } }))
  assert.equal((await client.getStatus()).requestId, null)
})

test('UI and platform layers cannot depend on product apps or management data', () => {
  for (const name of ['nuxt-ui', 'nuxt-platform']) {
    const base = resolve('packages', name)
    const pkg = JSON.parse(readFileSync(resolve(base, 'package.json'), 'utf8'))
    assert.equal(pkg.private, true)
    assert.equal('@ocarinow/console' in pkg.dependencies, false)
    if (name === 'nuxt-ui') assert.equal('@ocarinow/management-client' in pkg.dependencies, false)
    for (const path of readdirSync(resolve(base, 'app'), { recursive: true, encoding: 'utf8' })) {
      if (!/\.(vue|ts)$/.test(path)) continue
      const source = readFileSync(resolve(base, 'app', path), 'utf8')
      assert.doesNotMatch(source, /from ['"][^'"]*(?:apps\/console|@ocarinow\/console)/)
      if (name === 'nuxt-ui') assert.doesNotMatch(source, /management-client|useFetch|\$fetch|fetch\(/)
    }
  }
})
