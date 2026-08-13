<template>
  <div>
    <h2>我的病历</h2>
    <p style="color:var(--text-secondary);margin:4px 0 20px;">查看自己的病历和诊断报告</p>

    <!-- 未绑定档案：提示 + 手机号认领 -->
    <el-card v-if="!bound" shadow="never" style="max-width:560px;margin-bottom:20px;">
      <p style="margin:0 0 12px;font-size:14px;line-height:1.6;">
        绑定您的就诊档案后可查看病历和诊断报告。<br>
        请填写建档时预留的手机号：
      </p>
      <div style="display:flex;gap:8px;">
        <el-input v-model="phone" placeholder="请输入手机号" maxlength="11" clearable style="width:260px"/>
        <el-button type="primary" :loading="binding" @click="doBind">绑定</el-button>
      </div>
    </el-card>

    <template v-else>
      <el-table :data="records" border v-loading="loading" style="width:100%">
        <el-table-column label="病历ID" prop="id" width="80"/>
        <el-table-column label="病历内容" min-width="280">
          <template #default="scope">
            <span v-if="scope.row.raw_text" style="font-size:13px;">{{ scope.row.raw_text.slice(0, 100) }}...</span>
            <span v-else style="color:var(--text-muted);">无内容</span>
          </template>
        </el-table-column>
        <el-table-column label="诊断" min-width="180">
          <template #default="scope">
            <el-tag v-if="scope.row.structured_data?.diagnosis?.length" type="success" size="small">
              {{ scope.row.structured_data.diagnosis.join('、') }}
            </el-tag>
            <span v-else style="color:var(--text-muted);">待诊断</span>
          </template>
        </el-table-column>
        <el-table-column label="诊断报告" min-width="240">
          <template #default="scope">
            <template v-if="reportOf(scope.row.id)">
              <div style="font-size:13px;color:var(--text-primary);">
                {{ reportOf(scope.row.id).diagnosis_suggest?.slice(0, 60) || '—' }}
              </div>
              <el-button
                v-if="reportOf(scope.row.id).pdf_status"
                type="primary" link size="small"
                @click="openPdf(reportOf(scope.row.id).report_id)"
              >查看PDF报告</el-button>
              <span v-else style="color:var(--text-muted);font-size:12px;">PDF待生成</span>
            </template>
            <span v-else style="color:var(--text-muted);">暂无报告</span>
          </template>
        </el-table-column>
        <el-table-column label="日期" prop="create_time" width="170"/>
      </el-table>

      <el-empty v-if="!loading && records.length === 0" description="暂无病历记录" />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const records = ref([])
const reports = ref([])
const loading = ref(false)
const bound = ref(false)
const phone = ref('')
const binding = ref(false)

const reportOf = (recordId) => reports.value.find(r => r.record_id === recordId)

const loadData = async () => {
  loading.value = true
  try {
    const [recRes, repRes] = await Promise.all([
      request.get('/patient/my-records'),
      request.get('/patient/my-reports'),
    ])
    if (recRes.code === 200) records.value = recRes.data || []
    if (repRes.code === 200) reports.value = repRes.data || []
  } catch (e) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const doBind = async () => {
  if (!/^1\d{10}$/.test(phone.value)) {
    ElMessage.warning('请输入正确的11位手机号')
    return
  }
  binding.value = true
  try {
    const res = await request.post('/patient/bind', new URLSearchParams({ phone: phone.value }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    if (res.code === 200) {
      ElMessage.success('绑定成功')
      bound.value = true
      loadData()
    } else {
      ElMessage.error(res.msg || '绑定失败')
    }
  } catch (e) {
    // request 拦截器已统一提示
  } finally {
    binding.value = false
  }
}

const openPdf = async (rid) => {
  if (!rid) return ElMessage.warning('缺少报告ID')
  try {
    const blob = await request.get(`/report/pdf/download/${rid}`, { responseType: 'blob' })
    if (!blob || blob.size === 0) return ElMessage.error('PDF文件为空')
    const url = URL.createObjectURL(blob)
    window.open(url)
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (e) {
    ElMessage.error('打开PDF失败')
  }
}

onMounted(async () => {
  try {
    const res = await request.get('/patient/my-profile')
    if (res.code === 200 && res.data) {
      bound.value = true
      loadData()
    }
  } catch (e) {
    ElMessage.error('加载失败')
  }
})
</script>
