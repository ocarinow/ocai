<script setup lang="ts">
const { data, error, refresh } = await useFetch('/api/auth/session', { server: false })
const busy = ref(false)
const failed = ref(false)
const route = useRoute()
async function logout(provider: boolean) {
  if (!data.value?.csrf) return
  busy.value = true
  failed.value = false
  try {
    const result = await $fetch('/api/auth/logout', { method: 'POST', headers: {
      'x-csrf-token': data.value.csrf, 'x-provider-logout': String(provider),
    } })
    clearNuxtData()
    if (result.providerLogout) await navigateTo(result.providerLogout, { external: true })
    else await refresh()
  } catch { failed.value = true }
  finally { busy.value = false }
}
</script>

<template>
  <UiCard class="mt-6 gap-3 p-6" aria-label="Console session">
    <h2 class="text-lg font-semibold">Console access</h2>
    <template v-if="data?.authenticated && !error">
      <p class="text-sm text-muted-foreground">You are signed in. Organization management will be available in the next release.</p>
      <div class="flex flex-wrap gap-3">
        <UiButton variant="outline" :disabled="busy" @click="logout(false)">Sign out</UiButton>
        <UiButton variant="ghost" :disabled="busy" @click="logout(true)">Sign out and visit identity provider</UiButton>
      </div>
      <p class="text-xs text-muted-foreground">Signing out ends this console session. Identity-provider sign-out is a separate step.</p>
    </template>
    <template v-else-if="!error && data">
      <p class="text-sm text-muted-foreground">Sign in to access your console session.</p>
      <UiButton as-child class="w-fit"><a href="/auth/login">Sign in</a></UiButton>
    </template>
    <p v-else class="text-sm text-muted-foreground">Sign-in service is unavailable.</p>
    <p v-if="failed || route.query.signin === 'failed'" role="alert" class="text-sm text-destructive">Sign-in or sign-out could not finish. Please try again.</p>
  </UiCard>
</template>
