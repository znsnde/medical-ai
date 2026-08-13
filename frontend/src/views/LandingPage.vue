<template>
  <div
    class="relative min-h-screen bg-[#0F172A] overflow-hidden select-none"
    style="font-family: 'Inter', sans-serif; min-height: 100dvh;"
  >
    <!-- ═══ z-10: 底层粒子背景 ═══ -->
    <div
      class="absolute inset-0 bg-cover bg-center bg-no-repeat hero-zoom"
      style="background-image: url('https://images.unsplash.com/photo-1579154210463-cd144e976a3c?q=85&w=1280'); z-index: 10;"
    ></div>

    <!-- ═══ z-30: CT 影像遮罩（光标探照） ═══ -->
    <RevealLayer
      :image-ct="ctImageUrl"
      :cursor-x="cursorPos.x"
      :cursor-y="cursorPos.y"
    />

    <!-- ═══ z-50: 文字内容 ═══ -->
    <div class="absolute inset-0 pointer-events-none" style="z-index: 50;">
      <!-- 居中主标语 -->
      <div class="absolute top-[14%] left-0 right-0 flex flex-col items-center text-center px-5">
        <h1 class="text-[#E2E8F0] leading-[0.95]">
          <span
            class="block font-display italic font-normal text-5xl sm:text-7xl md:text-8xl tracking-tighter hero-anim hero-reveal"
            style="animation-delay: 0.25s; letter-spacing: -0.05em;"
          >{{ $t('landing.title1') }}</span>
          <span
            class="block font-normal text-5xl sm:text-7xl md:text-8xl -mt-1 hero-anim hero-reveal"
            style="animation-delay: 0.42s; letter-spacing: -0.08em;"
          >{{ $t('landing.title2') }}</span>
        </h1>
      </div>

      <!-- 左下角简介 -->
      <div
        class="hidden sm:block absolute bottom-14 left-10 md:left-14 max-w-[260px] hero-anim hero-fade"
        style="animation-delay: 0.7s;"
      >
        <p class="text-sm text-white/70 leading-relaxed">
          {{ $t('landing.subtitle') }}
        </p>
      </div>

      <!-- 右下角入口 -->
      <div
        class="absolute bottom-10 sm:bottom-24 left-5 right-5 sm:left-auto sm:right-10 md:right-14 max-w-full sm:max-w-[260px] flex flex-col items-start gap-4 sm:gap-5 hero-anim hero-fade"
        style="animation-delay: 0.85s;"
      >
        <p class="text-xs sm:text-sm text-white/70 leading-relaxed">
          {{ $t('landing.description') }}
        </p>
        <button
          class="bg-[#007AFF] hover:bg-[#0060D0] text-white text-sm font-medium px-7 py-3 rounded-full transition-all hover:scale-[1.03] active:scale-95 hover:shadow-lg hover:shadow-[#007AFF]/20 pointer-events-auto"
          @click="goToSystem"
        >{{ $t('landing.enterBtn') }}</button>
      </div>
    </div>

    <!-- ═══ z-[100]: 顶部导航 ═══ -->
    <nav class="fixed top-0 left-0 right-0 p-4 sm:p-5 flex items-center justify-between" style="z-index: 100;">
      <!-- Logo -->
      <div class="flex items-center gap-2">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
          <path d="M3 12H6L9 3L12 21L15 9L18 15L21 12H22" stroke="#007AFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </svg>
        <span class="font-display italic text-2xl text-[#E2E8F0]">{{ $t('landing.platform') }}</span>
      </div>

      <!-- 导航胶囊 -->
      <div class="hidden md:flex absolute left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-md border border-white/20 rounded-full px-2 py-2 gap-1 items-center">
        <button class="text-[#E2E8F0] px-4 py-1.5 rounded-full text-sm font-medium bg-white/10">{{ $t('landing.navRecord') }}</button>
        <button class="text-white/70 hover:text-white hover:bg-white/10 px-4 py-1.5 rounded-full text-sm transition-colors">{{ $t('landing.navDiagnosis') }}</button>
        <button class="text-white/70 hover:text-white hover:bg-white/10 px-4 py-1.5 rounded-full text-sm transition-colors">{{ $t('landing.navFollowup') }}</button>
        <button class="text-white/70 hover:text-white hover:bg-white/10 px-4 py-1.5 rounded-full text-sm transition-colors">{{ $t('landing.navPaper') }}</button>
        <button class="text-white/70 hover:text-white hover:bg-white/10 px-4 py-1.5 rounded-full text-sm transition-colors">{{ $t('landing.navReport') }}</button>
      </div>

      <!-- 右侧 -->
      <div class="flex items-center gap-3">
        <button class="text-white/50 text-xs hover:text-white mr-1 pointer-events-auto" @click.stop="switchLang('zh-CN')">中</button>
        <span class="text-white/20 text-xs">|</span>
        <button class="text-white/50 text-xs hover:text-white mr-3 pointer-events-auto" @click.stop="switchLang('en-US')">EN</button>
        <button
          class="hidden md:block bg-[#007AFF] text-white text-sm font-semibold px-6 py-2.5 rounded-full hover:bg-[#0060D0] transition-all hover:shadow-lg hover:shadow-[#007AFF]/20 pointer-events-auto"
          @click="goToSystem"
        >{{ $t('landing.loginBtn') }}</button>
        <button class="md:hidden text-white/70 p-1 pointer-events-auto" @click="goToSystem">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import RevealLayer from '../components/RevealLayer.vue'

const { locale } = useI18n()
const switchLang = (lang) => {
  locale.value = lang
  localStorage.setItem('language', lang)
}

const router = useRouter()

const ctImageUrl = 'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?q=85&w=1280'

// ── 光标跟踪 ──
const mouse = { x: -999, y: -999 }
const smooth = { x: -999, y: -999 }
const cursorPos = ref({ x: -999, y: -999 })
let rafId: number | null = null

const onMouseMove = (e: MouseEvent) => {
  mouse.x = e.clientX
  mouse.y = e.clientY
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t

const animate = () => {
  smooth.x = lerp(smooth.x, mouse.x, 0.1)
  smooth.y = lerp(smooth.y, mouse.y, 0.1)
  cursorPos.value = { x: smooth.x, y: smooth.y }
  rafId = requestAnimationFrame(animate)
}

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove)
  rafId = requestAnimationFrame(animate)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  if (rafId !== null) cancelAnimationFrame(rafId)
})

const goToSystem = () => {
  const token = localStorage.getItem('medical_token')
  if (token) {
    router.push('/dashboard')
  } else {
    router.push('/login')
  }
}
</script>
