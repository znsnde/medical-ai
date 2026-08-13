<template>
  <div class="dashboard">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="welcome-text">
        <h2>{{ $t('dashboard.title') }}，{{ userInfo.real_name || userInfo.username }} 👋</h2>
        <p class="welcome-sub">
          {{ roleLabel }} · {{ userInfo.department || '未设置科室' }}
          <el-tag size="small" :type="roleTagType" style="margin-left:8px;">
            {{ roleLabel }}
          </el-tag>
        </p>
      </div>
      <div class="welcome-time">
        <div class="current-time">{{ currentTime }}</div>
        <div class="current-date">{{ currentDate }}</div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="12" :sm="6" v-for="card in statCards" :key="card.label">
        <el-card class="stat-card" :style="{ borderTop: `3px solid ${card.color}` }" shadow="hover">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">{{ card.label }}</div>
              <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
            </div>
            <div class="stat-icon" :style="{ background: card.bgColor }">
              <span class="stat-emoji">{{ card.icon }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <!-- 近期病历趋势 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>📈 {{ $t('dashboard.trendTitle') }}</span>
            </div>
          </template>
          <div class="trend-chart" v-if="recentRecords.length">
            <div class="bar-chart">
              <div
                v-for="(item, index) in recentRecords"
                :key="index"
                class="bar-item"
              >
                <div class="bar-value">{{ item.count }}</div>
                <div
                  class="bar"
                  :style="{ height: getBarHeight(item.count) + 'px' }"
                ></div>
                <div class="bar-label">{{ formatDateLabel(item.date) }}</div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无病历数据" />
        </el-card>
      </el-col>

      <!-- 疾病分布 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>🏥 {{ $t('dashboard.diseaseTitle') }}</span>
            </div>
          </template>
          <div v-if="diseaseTop.length" class="disease-list">
            <div
              v-for="(item, index) in diseaseTop"
              :key="index"
              class="disease-item"
            >
              <div class="disease-rank" :class="'rank-' + (index + 1)">
                {{ index + 1 }}
              </div>
              <div class="disease-name">{{ item.name }}</div>
              <div class="disease-bar-bg">
                <div
                  class="disease-bar"
                  :style="{ width: getDiseaseWidth(item.count) + '%' }"
                ></div>
              </div>
              <div class="disease-count">{{ item.count }}例</div>
            </div>
          </div>
          <el-empty v-else description="暂无诊断数据" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷入口 -->
    <el-card shadow="hover" class="quick-actions">
      <template #header>
        <span>⚡ {{ $t('dashboard.quickActions') }}</span>
      </template>
      <div class="action-buttons">
        <el-button @click="router.push('/patient')" size="large">
          <span style="font-size:20px;margin-right:6px;">👨‍⚕️</span>
          {{ $t('dashboard.patientManage') }}
        </el-button>
        <el-button @click="router.push('/record')" size="large">
          <span style="font-size:20px;margin-right:6px;">📋</span>
          {{ $t('dashboard.recordInput') }}
        </el-button>
        <el-button @click="router.push('/diagnosis')" size="large">
          <span style="font-size:20px;margin-right:6px;">🧠</span>
          {{ $t('dashboard.aiDiagnosis') }}
        </el-button>
        <el-button @click="router.push('/report')" size="large">
          <span style="font-size:20px;margin-right:6px;">📄</span>
          {{ $t('dashboard.reportView') }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import { getUser } from '../utils/auth'

const { t } = useI18n()

const router = useRouter()

// ── 用户信息 ──
const userInfo = ref(getUser())

const roleLabel = computed(() => {
  const map = { admin: '系统管理员', doctor: '主治医师', patient: '患者' }
  return map[userInfo.value.role] || userInfo.value.role
})

const roleTagType = computed(() => {
  const map = { admin: 'danger', doctor: 'primary', patient: 'success' }
  return map[userInfo.value.role] || 'info'
})

// ── 实时时间 ──
const currentTime = ref('')
const currentDate = ref('')
let timer = null

const updateTime = () => {
  const now = new Date()
  const hours = now.getHours()
  currentTime.value = `${String(hours).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  currentDate.value = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  loadStats()
})

onUnmounted(() => {
  clearInterval(timer)
})

// ── 统计数据 ──
const totalPatients = ref(0)
const totalRecords = ref(0)
const totalReports = ref(0)
const todayRecords = ref(0)
const recentRecords = ref([])
const diseaseTop = ref([])

const statCards = computed(() => [
  { label: t('dashboard.totalPatients'), value: totalPatients.value, icon: '👨‍👩‍👧‍👦', color: '#409EFF', bgColor: '#ecf5ff' },
  { label: t('dashboard.totalRecords'), value: totalRecords.value, icon: '📋', color: '#67C23A', bgColor: '#f0f9eb' },
  { label: t('dashboard.totalReports'), value: totalReports.value, icon: '📄', color: '#E6A23C', bgColor: '#fdf6ec' },
  { label: t('dashboard.todayNew'), value: todayRecords.value, icon: '🆕', color: '#F56C6C', bgColor: '#fef0f0' }
])

const loadStats = async () => {
  try {
    const res = await request.get('/dashboard/stats')
    if (res.code === 200) {
      const d = res.data
      totalPatients.value = d.total_patients
      totalRecords.value = d.total_records
      totalReports.value = d.total_reports
      todayRecords.value = d.today_records
      recentRecords.value = d.recent_records || []
      diseaseTop.value = d.disease_top || []
    }
  } catch (e) {
    // 错误已在拦截器中处理
  }
}

// ── 图表辅助方法 ──
const maxCount = computed(() => {
  if (!recentRecords.value.length) return 1
  return Math.max(...recentRecords.value.map(r => r.count), 1)
})

const getBarHeight = (count) => {
  return Math.max(4, (count / maxCount.value) * 180)
}

const getDiseaseWidth = (count) => {
  if (!diseaseTop.value.length) return 0
  const max = diseaseTop.value[0].count
  return Math.max(5, (count / max) * 100)
}

const formatDateLabel = (dateStr) => {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  if (parts.length >= 3) {
    return `${parts[1]}/${parts[2]}`
  }
  return dateStr
}
</script>

<style scoped>
.dashboard {
  padding: 0;
}

/* ── 欢迎横幅 ── */
.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #409EFF 0%, #337ecc 100%);
  border-radius: 12px;
  padding: 24px 32px;
  margin-bottom: 24px;
  color: #fff;
}

.welcome-text h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}

.welcome-sub {
  margin: 8px 0 0;
  font-size: 14px;
  opacity: 0.9;
}

.welcome-time {
  text-align: right;
}

.current-time {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 2px;
}

.current-date {
  font-size: 14px;
  opacity: 0.85;
  margin-top: 4px;
}

/* ── 统计卡片 ── */
.stat-row {
  margin-bottom: 20px;
}

.stat-card {
  border-radius: 10px;
}

.stat-card :deep(.el-card__body) {
  padding: 20px;
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

/* ── 图表行 ── */
.chart-row {
  margin-bottom: 20px;
}

.card-header {
  font-size: 15px;
  font-weight: 600;
}

/* 柱状图 */
.trend-chart {
  padding: 10px 0;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 230px;
  padding: 0 10px;
}

.bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.bar-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.bar {
  width: 32px;
  background: linear-gradient(to top, #409EFF, #79bbff);
  border-radius: 4px 4px 0 0;
  min-height: 4px;
  transition: height 0.5s ease;
  cursor: pointer;
}

.bar:hover {
  opacity: 0.8;
}

.bar-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 8px;
}

/* ── 疾病分布 ── */
.disease-list {
  padding: 4px 0;
}

.disease-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.disease-item:last-child {
  border-bottom: none;
}

.disease-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  background: var(--neutral-bg);
  color: var(--text-secondary);
  flex-shrink: 0;
}

.rank-1 { background: #f56c6c; color: #fff; }
.rank-2 { background: #e6a23c; color: #fff; }
.rank-3 { background: #409eff; color: #fff; }

.disease-name {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.disease-bar-bg {
  flex: 2;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.disease-bar {
  height: 100%;
  background: linear-gradient(to right, #409EFF, #79bbff);
  border-radius: 4px;
  transition: width 0.6s ease;
}

.disease-count {
  width: 40px;
  text-align: right;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* ── 快捷操作 ── */
.quick-actions {
  border-radius: 10px;
}

.action-buttons {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  min-width: 140px;
  font-size: 14px;
}
</style>
