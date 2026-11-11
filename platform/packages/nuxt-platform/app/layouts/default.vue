<template>
  <div class="min-h-screen font-sans">
    <a href="#main-content" class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3">Skip to content</a>
    <header class="flex h-20 items-center justify-between border-b bg-white px-5 md:px-9">
      <NuxtLink to="/" aria-label="Ocarinow home" class="flex items-center gap-3 text-xl font-semibold tracking-tight">
        <span aria-hidden="true" class="grid size-9 place-items-center rounded-xl bg-primary text-white">o.</span>
        ocarinow<span class="hidden font-normal text-muted-foreground sm:inline">/ console</span>
      </NuxtLink>
      <UiBadge variant="outline" class="text-muted-foreground">Development preview</UiBadge>
    </header>
    <div class="mx-auto flex max-w-7xl flex-col md:flex-row">
      <aside class="border-b px-5 py-6 md:min-h-[calc(100vh-5rem)] md:w-56 md:shrink-0 md:border-r md:border-b-0 md:px-6 md:py-10">
        <nav aria-label="Main navigation"><slot name="navigation" /></nav>
        <p class="mt-12 hidden text-xs leading-5 text-muted-foreground md:block">One common interface.<br>Governed AI operations.</p>
      </aside>
      <main id="main-content" class="min-w-0 flex-1 px-5 py-8 md:px-12 md:py-12"><slot /></main>
    </div>
  </div>
</template>
