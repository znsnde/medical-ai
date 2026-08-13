<template>
  <div class="paper-wrap">
    <h2>医学文献PDF上传与AI解析</h2>
    <el-card style="margin:20px 0;">
      <el-form :model="formData" label-width="120px">
        <el-form-item label="文献标题">
          <el-input v-model="formData.paper_name" placeholder="输入文献名称"></el-input>
        </el-form-item>
        <el-form-item label="上传PDF文件">
          <!-- 拖拽上传区域 -->
          <div
            class="drop-zone"
            @dragover.prevent="dragOver = true"
            @dragleave.prevent="dragOver = false"
            @drop.prevent="handleDrop"
            :class="{ 'drag-over': dragOver, 'has-file': selectedFile }"
          >
            <template v-if="!selectedFile">
              <div class="drop-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#007AFF" stroke-width="1.5" stroke-linecap="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </div>
              <p class="drop-text">拖拽 PDF 文件到此处，或<span class="drop-link" @click="fileInput?.click()">点击选择</span></p>
              <p class="drop-hint">支持 PDF 格式，系统将自动提取文字进行 AI 摘要</p>
            </template>
            <template v-else>
              <div class="file-selected">
                <span class="file-icon">📄</span>
                <div class="file-info">
                  <span class="file-name">{{ selectedFile.name }}</span>
                  <span class="file-size">{{ (selectedFile.size / 1024).toFixed(1) }}KB</span>
                </div>
                <el-button text type="danger" size="small" @click.stop="selectedFile=null; dragOver=false">清除</el-button>
              </div>
            </template>
          </div>
          <input ref="fileInput" type="file" accept=".pdf" style="display:none" @change="handleFileChange" />
        </el-form-item>
        <el-form-item>
          <el-button type="success" @click="submitPaper" :loading="submitting" size="large" :disabled="!selectedFile" style="width:100%;">
            {{ submitting ? 'AI解析中，请稍候...' : '🚀 上传并AI解析' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- AI解析结果弹窗 -->
    <el-dialog v-model="resultVisible" title="🧠 AI文献解析结果" width="650px" :close-on-click-modal="false">
      <template v-if="resultData">
        <div style="margin-bottom:16px;">
          <label style="font-size:12px;color:var(--text-secondary);">文献标题</label>
          <p class="result-title">{{ resultData.paper_name }}</p>
        </div>
        <el-divider style="margin:12px 0;" />
        <div style="margin-bottom:16px;">
          <label style="font-size:12px;color:var(--text-secondary);">📝 AI 摘要</label>
          <p class="result-body result-summary-bg">{{ resultData.ai_summary }}</p>
        </div>
        <div style="margin-bottom:16px;">
          <label style="font-size:12px;color:var(--text-secondary);">🎯 核心结论</label>
          <p class="result-body result-conclusion-bg">{{ resultData.core_conclusion }}</p>
        </div>
      </template>
      <template #footer>
        <el-button @click="resultVisible=false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 搜索栏 -->
    <div style="display:flex;gap:10px;margin-bottom:16px;align-items:center;">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索文献关键词（标题/摘要/结论）..."
        style="max-width:360px;"
        clearable
        @clear="loadPaperList"
        @keyup.enter="searchPapers"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button @click="searchPapers" type="primary">搜索</el-button>
    </div>

    <h3>{{ searchKeyword ? '搜索结果' : '已上传文献列表' }}</h3>
    <el-table :data="paperList" border style="width:100%" v-loading="loading">
      <el-table-column label="ID" prop="id" width="80"/>
      <el-table-column label="文献标题" prop="paper_name" min-width="180"/>
      <el-table-column label="AI摘要" prop="ai_summary" min-width="250" show-overflow-tooltip/>
      <el-table-column label="核心结论" prop="core_conclusion" min-width="200" show-overflow-tooltip/>
      <el-table-column label="上传时间" prop="create_time" width="160"/>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="viewFullText(scope.row)">全文</el-button>
          <el-button type="danger" size="small" @click="delPaper(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 全文查看弹窗 -->
    <el-dialog v-model="fullTextVisible" :title="'📄 ' + fullTextTitle" width="750px" top="3vh">
      <div style="max-height:65vh;overflow-y:auto;white-space:pre-wrap;font-size:13px;line-height:1.8;padding:4px;">{{ fullTextContent || '暂无全文内容' }}</div>
      <template #footer>
        <el-button @click="fullTextVisible=false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import request from '../utils/request'

const fileInput = ref(null)
const selectedFile = ref(null)
const submitting = ref(false)
const loading = ref(false)
const dragOver = ref(false)
const resultVisible = ref(false)
const resultData = ref(null)
const searchKeyword = ref('')
const fullTextVisible = ref(false)
const fullTextTitle = ref('')
const fullTextContent = ref('')

const formData = ref({
  paper_name: ''
})
const paperList = ref([])

// 搜索文献
const searchPapers = async () => {
  if (!searchKeyword.value) return loadPaperList()
  loading.value = true
  try {
    const res = await request.get('/paper/search', { params: { keyword: searchKeyword.value } })
    if (res.code === 200) paperList.value = res.data
  } catch (e) {
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}

// 查看全文
const viewFullText = async (row) => {
  fullTextTitle.value = row.paper_name
  fullTextContent.value = '加载中...'
  fullTextVisible.value = true
  try {
    const res = await request.get(`/paper/${row.id}`)
    if (res.code === 200) {
      fullTextContent.value = res.data.full_text || '（该文献没有保存全文内容）'
    } else {
      fullTextContent.value = '获取失败'
    }
  } catch (e) {
    fullTextContent.value = '加载失败'
  }
}

// 加载文献列表
const loadPaperList = async () => {
  loading.value = true
  try {
    const res = await request.get('/paper/list/all')
    if (res.code === 200) paperList.value = res.data
  } catch (e) {
    ElMessage.error('获取文献列表失败')
  } finally {
    loading.value = false
  }
}

// 拖拽上传
const handleDrop = (e) => {
  dragOver.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    const file = files[0]
    if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
      selectedFile.value = file
    } else {
      ElMessage.warning('仅支持 PDF 格式')
    }
  }
}

// 选择文件时保存
const handleFileChange = (e) => {
  const files = e.target.files || e.dataTransfer?.files
  if (files && files.length > 0) {
    selectedFile.value = files[0]
  }
  // 清空input值，允许再次选择同一文件
  e.target.value = ''
}

// 提交上传（PDF → 自动提取文字 → AI摘要）
const submitPaper = async () => {
  if (!formData.value.paper_name) {
    return ElMessage.warning('请输入文献标题')
  }
  if (!selectedFile.value) {
    return ElMessage.warning('请选择PDF文件')
  }
  submitting.value = true
  try {
    const form = new FormData()
    form.append('paper_name', formData.value.paper_name)
    form.append('file', selectedFile.value)
    const res = await request.post('/paper/upload', form)
    if (res.code === 200) {
      resultData.value = res.data
      resultVisible.value = true
      selectedFile.value = null
      formData.value = { paper_name: '' }
      loadPaperList()
    } else {
      ElMessage.error(res.msg || '提交失败')
    }
  } catch (e) {
    ElMessage.error('上传或解析失败，请检查PDF文件是否可读')
  } finally {
    submitting.value = false
  }
}

// 删除文献
const delPaper = async (pid) => {
  try {
    await request.delete(`/paper/${pid}`)
    ElMessage.success('删除成功')
    loadPaperList()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => loadPaperList())
</script>

<style scoped>
.paper-wrap {
  padding: 20px;
}

/* ── 拖拽上传区域 ── */
.drop-zone {
  width: 100%;
  min-height: 160px;
  border: 2px dashed rgba(0, 122, 255, 0.3);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(0, 122, 255, 0.03);
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: #007AFF;
  background: rgba(0, 122, 255, 0.08);
}

.drop-zone.has-file {
  border-style: solid;
  border-color: #67C23A;
  background: rgba(103, 194, 58, 0.05);
  min-height: 80px;
}

.drop-icon {
  text-align: center;
  margin-bottom: 8px;
}

.drop-text {
  color: #94A3B8;
  font-size: 14px;
  margin: 0;
}

.drop-link {
  color: #007AFF;
  cursor: pointer;
}

.drop-hint {
  color: var(--text-secondary);
  font-size: 12px;
  margin: 6px 0 0;
}

.file-selected {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
}

.file-icon {
  font-size: 32px;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-weight: 500;
  font-size: 14px;
  color: #E2E8F0;
}

.file-size {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 暗色适配 */
html.theme-day .drop-text,
html.theme-dawn .drop-text {
  color: #64748B;
}
html.theme-day .file-name {
  color: #1E293B;
}

/* ── AI解析结果弹窗 ── */
.result-title {
  font-size: 15px;
  font-weight: 600;
  margin: 4px 0 0;
}

.result-body {
  font-size: 13px;
  line-height: 1.7;
  margin: 6px 0 0;
  padding: 12px;
  border-radius: 8px;
}

.result-summary-bg {
  background: rgba(0, 122, 255, 0.06);
}

.result-conclusion-bg {
  background: rgba(103, 194, 58, 0.06);
}

html.theme-night .result-title,
html.theme-dusk .result-title,
html.theme-night .result-body,
html.theme-dusk .result-body {
  color: #E2E8F0;
}

html.theme-day .result-title,
html.theme-dawn .result-title,
html.theme-day .result-body,
html.theme-dawn .result-body {
  color: #1E293B;
}
</style>
