<template>
  <NuxtLayout>
    <template #navigation>
      <p class="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Gateway</p>
      <NuxtLink to="/" class="block rounded-lg bg-primary/10 px-3 py-2.5 text-sm font-medium text-primary" aria-current="page">Overview</NuxtLink>
    </template>
    <NuxtPage />
  </NuxtLayout>
</template>
