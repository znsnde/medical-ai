<template>
  <div class="dicom-viewer">
    <!-- 顶部信息栏 -->
    <div class="viewer-header">
      <div class="header-left">
        <el-button @click="goBack" text>
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h3>医学影像查看器</h3>
        <el-tag type="success" v-if="refImageName">{{ refImageName }}</el-tag>
      </div>
      <div class="header-right">
        <el-button-group>
          <el-button :type="fitMode === 'contain' ? 'primary' : ''" @click="fitMode='contain'" size="small">适应</el-button>
          <el-button :type="fitMode === 'original' ? 'primary' : ''" @click="fitMode='original'" size="small">原图</el-button>
        </el-button-group>
        <el-button @click="toggleFullscreen" size="small">
          <el-icon><FullScreen /></el-icon>
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" class="viewer-body">
      <!-- 主图像区 -->
      <el-col :span="18">
        <el-card class="image-card" :body-style="{ padding: '12px' }">
          <div class="image-container" ref="imageContainerRef">
            <img
              v-if="imageUrl"
              :src="imageUrl"
              :style="imageStyle"
              class="main-image"
              alt="医学影像"
              draggable="false"
            />
            <div v-else class="image-placeholder">
              <el-icon :size="48"><Picture /></el-icon>
              <p>{{ loading ? '加载中...' : '暂无图像' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧信息面板 -->
      <el-col :span="6">
        <!-- 诊断信息 -->
        <el-card class="ctrl-card">
          <template #header><span>📋 诊断信息</span></template>
          <div class="diagnosis-info">
            <div class="info-row">
              <span class="info-label">匹配影像</span>
              <span class="info-value diagnosis-name">{{ refImageName || '--' }}</span>
            </div>
            <div class="info-row" v-if="refImageDiagnosis">
              <span class="info-label">诊断依据</span>
              <span class="info-value diagnosis-text">{{ refImageDiagnosis }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">影像来源</span>
              <span class="info-value" style="font-size:11px;">公共医学影像库</span>
            </div>
          </div>
        </el-card>

        <!-- 图像调整 -->
        <el-card class="ctrl-card" style="margin-top:12px;">
          <template #header><span>🎚️ 图像调整</span></template>
          <div class="slider-group">
            <label>亮度</label>
            <el-slider v-model="brightness" :min="0" :max="200" :step="1" show-input input-size="small" />
          </div>
          <div class="slider-group">
            <label>对比度</label>
            <el-slider v-model="contrast" :min="0" :max="200" :step="1" show-input input-size="small" />
          </div>
          <el-button size="small" @click="resetImageAdjust" style="margin-top:4px;">重置</el-button>
        </el-card>

        <!-- 缩放 -->
        <el-card class="ctrl-card" style="margin-top:12px;">
          <template #header><span>🔍 缩放</span></template>
          <div class="zoom-controls">
            <el-button size="small" @click="zoomOut" :disabled="zoom <= 0.1">-</el-button>
            <span class="zoom-value">{{ Math.round(zoom * 100) }}%</span>
            <el-button size="small" @click="zoomIn" :disabled="zoom >= 5">+</el-button>
            <el-button size="small" @click="zoom=1" style="margin-left:8px;">重置</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, FullScreen, Picture } from '@element-plus/icons-vue'
import request from '../utils/request'

const route = useRoute()
const router = useRouter()

const recordId = computed(() => route.params.record_id)

// ── 图像状态 ──
const imageUrl = ref('')
const loading = ref(true)
const fitMode = ref('contain')
const zoom = ref(1)
const brightness = ref(100)
const contrast = ref(100)
const refImageName = ref('')
const refImageDiagnosis = ref('')
const isFullscreen = ref(false)
const imageContainerRef = ref(null)
let currentObjectUrl = ''

const imageStyle = computed(() => {
  const base = {
    transition: 'transform 0.1s ease',
    filter: `brightness(${brightness.value}%) contrast(${contrast.value}%)`,
    cursor: 'grab'
  }
  if (fitMode.value === 'contain') {
    return {
      ...base,
      maxWidth: '100%',
      maxHeight: 'calc(100vh - 180px)',
      objectFit: 'contain',
      transform: `scale(${zoom.value})`
    }
  }
  return {
    ...base,
    width: 'auto',
    height: 'auto',
    transform: `scale(${zoom.value})`,
    transformOrigin: 'top left'
  }
})

// ── 加载参考影像（根据诊断自动匹配） ──
const loadImage = async () => {
  loading.value = true
  try {
    if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl)
    const res = await request.get(`/reference-image/by-record/${recordId.value}`, {
      responseType: 'blob'
    })
    const blob = res instanceof Blob ? res : new Blob([res])
    currentObjectUrl = URL.createObjectURL(blob)
    imageUrl.value = currentObjectUrl

    if (res.headers) {
      refImageName.value = decodeURIComponent(res.headers['x-image-display-name'] || '') || '参考影像'
      refImageDiagnosis.value = decodeURIComponent(res.headers['x-image-diagnosis'] || '')
    }
  } catch (e) {
    imageUrl.value = ''
    ElMessage.error('加载影像失败')
  } finally {
    loading.value = false
  }
}

const resetImageAdjust = () => {
  brightness.value = 100
  contrast.value = 100
}

// ── 缩放 ──
const zoomIn = () => { zoom.value = Math.min(5, Math.round((zoom.value + 0.1) * 10) / 10) }
const zoomOut = () => { zoom.value = Math.max(0.1, Math.round((zoom.value - 0.1) * 10) / 10) }

// ── 全屏 ──
const toggleFullscreen = async () => {
  const el = document.documentElement
  if (!isFullscreen.value) await el.requestFullscreen?.()
  else await document.exitFullscreen?.()
}
const onFullscreenChange = () => { isFullscreen.value = !!document.fullscreenElement }

const goBack = () => router.back()

// ── 生命周期 ──
onMounted(async () => {
  await loadImage()
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl)
})
</script>

<style scoped>
.dicom-viewer { padding: 0; height: 100%; }

.viewer-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; flex-wrap: wrap; gap: 8px;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-left h3 { margin: 0; font-size: 16px; }
.header-right { display: flex; gap: 8px; align-items: center; }

.viewer-body { height: calc(100vh - 140px); }

.image-card { height: 100%; background: #1a1a2e; border-radius: 8px; overflow: hidden; }
.image-container {
  width: 100%; height: 100%; display: flex;
  align-items: center; justify-content: center; overflow: auto;
}
.image-placeholder { color: var(--text-muted); text-align: center; }
.image-placeholder p { margin: 12px 0 0; font-size: 14px; }

.ctrl-card :deep(.el-card__body) { padding: 14px; }

/* 诊断信息 */
.info-row {
  padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 12px;
}
.info-row:last-child { border-bottom: none; }
.info-label { color: var(--text-secondary); display: block; margin-bottom: 2px; font-size: 11px; }
.info-value { color: var(--text-primary); font-weight: 500; display: block; }
.diagnosis-name { color: #67c23a; font-size: 14px; }
.diagnosis-text {
  font-size: 11px; color: var(--text-secondary); line-height: 1.5;
  max-height: 120px; overflow-y: auto;
}

.slider-group { margin-bottom: 10px; }
.slider-group label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }

.zoom-controls { display: flex; align-items: center; gap: 8px; }
.zoom-value { font-size: 14px; font-weight: 600; min-width: 48px; text-align: center; }
</style>
