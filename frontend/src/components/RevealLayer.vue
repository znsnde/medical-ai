<template>
  <div
    class="absolute inset-0 pointer-events-none bg-cover bg-center"
    :style="{
      backgroundImage: 'url(' + imageCt + ')',
      zIndex: 30,
      WebkitMaskImage: maskStyle,
      maskImage: maskStyle,
      WebkitMaskSize: '100% 100%',
      maskSize: '100% 100%',
      WebkitMaskRepeat: 'no-repeat',
      maskRepeat: 'no-repeat',
    }"
  ></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  imageCt: string
  cursorX: number
  cursorY: number
}>()

const SPOTLIGHT_R = 260

const maskStyle = computed(() => {
  const cx = props.cursorX
  const cy = props.cursorY

  // 光标在屏幕外时不显示遮罩
  if (cx < 0 || cy < 0) {
    return 'none'
  }

  return `radial-gradient(circle ${SPOTLIGHT_R}px at ${cx}px ${cy}px,
    rgba(0,0,0,1) 0%,
    rgba(0,0,0,1) 40%,
    rgba(0,0,0,0.75) 60%,
    rgba(0,0,0,0.4) 75%,
    rgba(0,0,0,0.12) 88%,
    transparent 100%)`
})
</script>
