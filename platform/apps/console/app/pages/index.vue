<script setup lang="ts">
import { createManagementClient, ManagementApiError } from '@ocarinow/management-client'

const client = createManagementClient()
const { data, status, error, refresh } = await useAsyncData('gateway-system-status', async () => {
  try { return await client.getStatus() }
  catch (cause) {
    throw createError({ statusCode: 503, message: cause instanceof ManagementApiError ? cause.message : 'Management service unavailable.' })
  }
}, { server: false })
const checking = computed(() => status.value === 'pending' || status.value === 'idle')
const connected = computed(() => status.value === 'success' && !!data.value)
</script>

<template>
  <div>
    <p class="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-primary">AI Gateway</p>
    <div class="flex flex-wrap items-start justify-between gap-5">
      <div><h1 class="text-3xl font-semibold tracking-tight md:text-4xl">Gateway overview</h1>
        <p class="mt-3 max-w-xl leading-7 text-muted-foreground">A shared entry point for your AI applications.<br class="hidden sm:block"> Connect, govern, and understand every request.</p></div>
      <UiButton variant="outline" :disabled="checking" @click="refresh()">{{ checking ? 'Checking…' : 'Refresh status' }}</UiButton>
    </div>

    <UiCard role="region" aria-labelledby="connection-title" class="mt-10 gap-0 p-6 md:p-8">
      <div class="flex items-start gap-4">
        <span aria-hidden="true" class="mt-1 grid size-11 shrink-0 place-items-center rounded-xl" :class="connected ? 'bg-emerald-50 text-emerald-700' : 'bg-muted text-muted-foreground'">
          <svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 12h4l3-7 3 14 3-7h3" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </span>
        <div class="flex-1"><h2 id="connection-title" class="text-lg font-semibold">Management connection</h2>
          <p role="status" aria-live="polite" class="mt-1 text-sm leading-6" :class="error ? 'text-red-700' : 'text-muted-foreground'">
            {{ checking ? 'Checking the gateway service…' : connected ? 'Connected to the gateway service.' : 'The gateway service is unavailable. Check the service and try again.' }}
          </p>
        </div>
        <UiBadge v-if="connected" variant="secondary">Connected</UiBadge>
      </div>
      <dl v-if="connected && data" class="mt-7 grid gap-6 border-t pt-6 sm:grid-cols-2">
        <div><dt class="text-xs uppercase tracking-wider text-muted-foreground">Service</dt><dd class="mt-2 text-sm font-medium">{{ data.status.service }}</dd></div>
        <div><dt class="text-xs uppercase tracking-wider text-muted-foreground">Request reference</dt><dd class="mt-2 break-all font-mono text-xs">{{ data.requestId ?? 'Not provided' }}</dd></div>
      </dl>
    </UiCard>

    <UiCard role="region" aria-labelledby="setup-title" class="mt-6 gap-0 p-6 md:p-8">
      <div class="flex flex-wrap items-center justify-between gap-3"><h2 id="setup-title" class="text-lg font-semibold">Model access</h2>
        <UiBadge variant="outline">{{ connected ? 'Not configured' : 'Status unknown' }}</UiBadge></div>
      <p class="mt-3 max-w-xl text-sm leading-7 text-muted-foreground">{{ connected ? 'The platform foundation is available. Organization access and provider connections are not available in this development preview.' : 'Connect to the management service to check gateway setup.' }}</p>
    </UiCard>
    <p class="mt-8 text-xs leading-6 text-muted-foreground">Service availability is separate from inference readiness. This preview cannot process model requests.</p>
  </div>
</template>
