<template>
  <div class="kg-page">
    <!-- 顶部工具栏 -->
    <el-card class="toolbar" shadow="never">
      <div class="toolbar-inner">
        <h3 class="kg-title">🕸️ 医学知识图谱</h3>
        <div class="toolbar-actions">
          <el-input
            v-model="keyword"
            placeholder="搜索疾病 / 症状 / 药物..."
            clearable
            style="width: 260px;"
            @keyup.enter="searchGraph"
            @clear="loadFullGraph"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="depth" style="width: 110px;" @change="searchGraph">
            <el-option :value="1" label="1层" />
            <el-option :value="2" label="2层" />
            <el-option :value="3" label="3层" />
          </el-select>
          <el-button type="primary" @click="searchGraph">聚焦</el-button>
          <el-button @click="loadFullGraph">全图</el-button>
          <span class="stat">{{ nodeCount }} 节点 · {{ linkCount }} 关系</span>
        </div>
      </div>
    </el-card>

    <!-- 图谱容器 -->
    <el-card class="graph-card" shadow="never">
      <div ref="chartRef" class="graph-container"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { Search } from '@element-plus/icons-vue'
import request from '../utils/request'

const chartRef = ref(null)
const keyword = ref('')
const depth = ref(2)
const nodeCount = ref(0)
const linkCount = ref(0)

let chart = null
let observer = null

// 节点类型配色
const TYPE_COLORS = {
  Disease: '#F56C6C',
  Symptom: '#409EFF',
  Medication: '#67C23A',
  Treatment: '#9B59B6',
  Department: '#E6A23C',
  Check: '#00B0F0',
  Drug: '#E91E63',
}
const DEFAULT_COLOR = '#909399'

const typeNameMap = {
  Disease: '疾病', Symptom: '症状', Medication: '用药',
  Treatment: '治疗方案', Department: '科室', Check: '检查项目', Drug: '药物',
}

const symbolSize = (type) => {
  switch (type) {
    case 'Disease': return 34
    case 'Department': return 28
    case 'Medication': return 24
    case 'Treatment': return 22
    default: return 20
  }
}

// 读取主题 CSS 变量（夜间/白天自适应文字颜色）
const readThemeColor = (prop, fallback) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(prop).trim()
  return v || fallback
}

const updateThemeColors = () => {
  if (!chart) return
  const labelColor = readThemeColor('--text-secondary', '#64748B')
  const edgeColor = readThemeColor('--text-muted', '#94A3B8')
  chart.setOption({
    legend: [{ textStyle: { color: labelColor } }],
    series: [{ label: { color: labelColor }, lineStyle: { color: edgeColor } }],
  })
}

const renderGraph = (nodes, links) => {
  nodeCount.value = nodes.length
  linkCount.value = links.length
  if (!chart) return

  // 按节点类型构建分类与配色
  const typeSet = [...new Set(nodes.map(n => n.type))]
  const catIndex = {}
  typeSet.forEach((t, i) => { catIndex[t] = i })
  const categories = typeSet.map(t => ({
    name: t,
    itemStyle: { color: TYPE_COLORS[t] || DEFAULT_COLOR },
  }))

  const nameOf = (id) => {
    const hit = nodes.find(n => n.id === id)
    return hit ? hit.label : id
  }

  const labelColor = readThemeColor('--text-secondary', '#64748B')
  const edgeColor = readThemeColor('--text-muted', '#94A3B8')

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params) => {
        if (params.dataType === 'edge') {
          const d = params.data
          return `<b>${nameOf(d.source)} → ${nameOf(d.target)}</b><br/>关系：${d.rel}` +
                 (d.desc ? `<br/><span style="color:#94A3B8;">${d.desc}</span>` : '')
        }
        const t = typeNameMap[params.data.type] || params.data.type
        return `<b>${params.data.label}</b><br/>类型：${t}`
      },
      backgroundColor: 'rgba(17,24,39,0.92)',
      borderColor: 'rgba(255,255,255,0.12)',
      textStyle: { color: '#E2E8F0' },
    },
    legend: [{
      top: 6,
      left: 'center',
      data: categories.map(c => c.name),
      textStyle: { color: labelColor, fontSize: 12 },
      itemWidth: 14,
      itemHeight: 10,
    }],
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      categories,
      data: nodes.map(n => ({
        id: n.id,
        name: n.label,
        label: n.label,
        type: n.type,
        category: catIndex[n.type],
        symbolSize: symbolSize(n.type),
      })),
      links: links.map(l => ({
        source: l.source,
        target: l.target,
        rel: l.rel,
        desc: l.desc,
      })),
      force: { repulsion: 220, edgeLength: [80, 150], gravity: 0.08, friction: 0.6 },
      lineStyle: { color: edgeColor, opacity: 0.45, width: 1.2 },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: 6,
      label: { show: true, position: 'right', color: labelColor, fontSize: 11, formatter: '{b}' },
      edgeLabel: { show: false },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3, opacity: 1 } },
      animationDuration: 500,
      animationEasingUpdate: 'quinticInOut',
    }],
  }

  chart.clear()
  chart.setOption(option)
}

const loadGraph = async (center, dep) => {
  try {
    const params = center ? { center, depth: dep } : {}
    const res = await request.get('/kg/graph', { params })
    if (res.code === 200) {
      const d = res.data
      if (center && d.nodes.length === 0) {
        ElMessage.warning(`未找到节点「${center}」`)
        return
      }
      renderGraph(d.nodes, d.links)
    }
  } catch (e) {
    // 请求拦截器已统一提示
  }
}

const searchGraph = () => {
  const kw = keyword.value.trim()
  if (!kw) { loadFullGraph(); return }
  loadGraph(kw, depth.value)
}

const loadFullGraph = () => {
  keyword.value = ''
  loadGraph('', depth.value)
}

const onResize = () => chart && chart.resize()

onMounted(async () => {
  chart = echarts.init(chartRef.value)

  // 点击节点 → 以其为中心向外展开
  chart.on('click', (params) => {
    if (params.dataType === 'node' && params.data && params.data.label) {
      keyword.value = params.data.label
      loadGraph(params.data.label, depth.value)
    }
  })

  // 监听日夜主题切换，更新文字颜色（不重置布局）
  observer = new MutationObserver(updateThemeColors)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

  window.addEventListener('resize', onResize)
  await loadFullGraph()
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  observer && observer.disconnect()
  chart && chart.dispose()
  chart = null
})
</script>

<style scoped>
.kg-page { padding: 0; }
.toolbar { margin-bottom: 16px; }
.toolbar-inner {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
}
.kg-title { margin: 0; font-size: 16px; font-weight: 600; }
.toolbar-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.stat { font-size: 12px; color: var(--text-secondary); margin-left: 4px; }
.graph-card :deep(.el-card__body) { padding: 8px; }
.graph-container { width: 100%; height: calc(100vh - 230px); min-height: 400px; }
</style>
