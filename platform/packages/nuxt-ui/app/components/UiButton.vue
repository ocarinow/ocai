<script setup lang="ts">
import { computed } from 'vue'
import { Primitive } from 'reka-ui'
import { cva } from 'class-variance-authority'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'outline'
  disabled?: boolean
  class?: ClassValue
}>(), { variant: 'primary', disabled: false })

const variants = cva(
  'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50',
  { variants: { variant: {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
    outline: 'border bg-white text-foreground hover:bg-muted',
  } } },
)
const classes = computed(() => twMerge(clsx(variants({ variant: props.variant }), props.class)))
</script>

<template>
  <Primitive as="button" type="button" :class="classes" :disabled="disabled"><slot /></Primitive>
</template>
