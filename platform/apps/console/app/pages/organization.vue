<script setup lang="ts">
import { createManagementClient, ManagementApiError, type Organization, type CurrentIdentity } from '@ocarinow/management-client'

const client = createManagementClient()
const { data: session } = await useFetch('/api/auth/session', { server: false })
const identity = ref<CurrentIdentity | null>(null)
const organization = ref<Organization | null>(null)
const selected = ref('')
const name = ref('')
const busy = ref(false)
const message = ref('')
const problem = ref('')
const reference = ref<string | null>(null)
let generation = 0

function failure(error: unknown) {
  const status = error instanceof ManagementApiError ? error.status : 503
  reference.value = error instanceof ManagementApiError ? error.requestId : null
  problem.value = ({ 401: 'Your session ended. Sign in again.', 403: 'This account has no active platform access.', 404: 'This organization is unavailable.', 409: 'Someone changed this organization. Reload before saving again.', 422: 'Enter a display name between 1 and 100 characters.' } as Record<number, string>)[status] ?? 'Management is temporarily unavailable. Please retry.'
  organization.value = null
  name.value = ''
  if ([401, 403].includes(status)) { identity.value = null; selected.value = '' }
}
async function choose(id: string) {
  const current = ++generation
  selected.value = id
  organization.value = null
  name.value = ''
  message.value = ''
  problem.value = ''
  reference.value = null
  busy.value = true
  try {
    const result = await client.getOrganization(id)
    if (current !== generation) return
    organization.value = result.value
    name.value = result.value.display_name
    reference.value = result.requestId
  } catch (error) { if (current === generation) failure(error) }
  finally { if (current === generation) busy.value = false }
}
async function load() {
  generation++
  identity.value = null
  organization.value = null
  selected.value = ''
  name.value = ''
  problem.value = ''
  message.value = ''
  busy.value = true
  try {
    identity.value = (await client.getMe()).value
    const first = identity.value.organizations[0]
    if (first) await choose(first.id)
    else message.value = 'No organizations are available to this account.'
  } catch (error) { failure(error) }
  finally { busy.value = false }
}
async function save() {
  const current = organization.value
  if (!current || !session.value?.csrf || busy.value) return
  busy.value = true
  problem.value = ''
  message.value = ''
  try {
    const result = await client.updateOrganization(current.id, { display_name: name.value, version: current.version }, session.value.csrf)
    organization.value = result.value
    name.value = result.value.display_name
    reference.value = result.requestId
    const item = identity.value?.organizations.find(item => item.id === current.id)
    if (item) Object.assign(item, result.value)
    message.value = 'Organization updated.'
  } catch (error) { failure(error) }
  finally { busy.value = false }
}
onMounted(load)
onBeforeUnmount(() => { generation++; identity.value = null; organization.value = null; name.value = '' })
</script>

<template>
  <div>
    <p class="mb-3 text-xs font-semibold uppercase tracking-wider text-primary">Management</p>
    <h1 class="text-3xl font-semibold">Organization settings</h1>
    <p class="mt-3 text-muted-foreground">Manage the organization you are authorized to access.</p>
    <div class="mt-6 flex flex-wrap gap-2" aria-label="Available organizations">
      <UiButton v-for="item in identity?.organizations" :key="item.id" variant="outline" :disabled="busy" :aria-pressed="selected === item.id" @click="choose(item.id)">{{ item.display_name }}</UiButton>
    </div>
    <UiCard class="mt-6 gap-5 p-6">
      <form v-if="organization" class="space-y-5" @submit.prevent="save">
        <div class="space-y-2"><UiLabel for="organization-name">Display name</UiLabel>
          <UiInput id="organization-name" v-model="name" maxlength="100" required :disabled="busy || !organization.can_update" /></div>
        <p v-if="!organization.can_update" class="text-sm text-muted-foreground">You have read-only access.</p>
        <UiButton v-if="organization.can_update" type="submit" :disabled="busy || !session?.csrf">{{ busy ? 'Saving…' : 'Save changes' }}</UiButton>
      </form>
      <p v-if="busy && !organization" role="status">Loading organization…</p>
      <p v-if="message" role="status">{{ message }}</p>
      <p v-if="problem" role="alert" class="text-destructive">{{ problem }}</p>
      <div v-if="problem" class="flex gap-3"><UiButton variant="outline" :disabled="busy" @click="load">Reload</UiButton><a href="/auth/login" class="text-sm underline">Sign in</a></div>
      <p v-if="reference" class="break-all text-xs text-muted-foreground">Request reference: {{ reference }}</p>
    </UiCard>
    <PlatformSession />
  </div>
</template>
