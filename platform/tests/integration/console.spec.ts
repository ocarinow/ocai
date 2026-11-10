import { test, expect } from '@playwright/test'

test('built console uses the gateway and recovers from an unavailable service', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Gateway overview' })).toBeVisible()
  await expect(page.getByRole('status')).toHaveText('Connected to the gateway service.')
  await expect(page.getByText('ocai-gateway', { exact: true })).toBeVisible()
  await expect(page.getByText('Not configured', { exact: true })).toBeVisible()
  const response = await page.request.get('/api/management/status')
  expect(response.headers()['x-request-id']).toMatch(/^[a-f0-9]{32}$/)
  expect(response.headers()['cache-control']).toBe('no-store')
  expect(await response.json()).toEqual({ service: 'ocai-gateway', stage: 'foundation', inference_ready: false })
  await page.screenshot({ path: testInfo.outputPath('desktop.png'), fullPage: true })

  await page.route('**/api/management/status', route => route.abort())
  await page.getByRole('button', { name: 'Refresh status' }).click()
  await expect(page.getByRole('status')).toContainText('unavailable')
  await expect(page.getByText('Status unknown', { exact: true })).toBeVisible()
  await expect(page.getByText('ocai-gateway', { exact: true })).not.toBeVisible()
  await page.unroute('**/api/management/status')
  await page.getByRole('button', { name: 'Refresh status' }).click()
  await expect(page.getByRole('status')).toHaveText('Connected to the gateway service.')

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('heading', { name: 'Gateway overview' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true })
  expect(errors).toEqual([])
})
