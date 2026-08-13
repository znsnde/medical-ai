<template>
  <div>
    <h2>AI辅助诊断生成</h2>
    <el-card style="margin:20px 0;">
      <el-form :inline="true">
        <el-form-item label="病历ID">
          <el-input v-model="recordId" placeholder="输入病历ID" style="width:200px;"></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="genDiagnosis" :loading="generating" size="large">
            {{ generating ? '诊断分析中...' : '生成诊断报告' }}
          </el-button>
        </el-form-item>
        <el-form-item v-if="recentRecords.length">
          <el-select v-model="recordId" placeholder="选择最近病历" style="width:200px;" @change="genDiagnosis">
            <el-option
              v-for="r in recentRecords"
              :key="r.id"
              :label="`病历 #${r.id} (患者ID:${r.patient_id})`"
              :value="r.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 诊断结果 -->
    <el-card v-if="report" style="margin-top:20px;">
      <template #header>
        <span style="font-weight:bold;font-size:16px;">
          🧠 诊断报告 #{{ report.id }}
          <el-tag style="margin-left:10px;" type="success" v-if="report.patient_name">
            {{ report.patient_name }}
          </el-tag>
        </span>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="关联病历ID">
          {{ report.record_id }}
        </el-descriptions-item>
        <el-descriptions-item label="患者姓名" v-if="report.patient_name">
          {{ report.patient_name }}
        </el-descriptions-item>
        <el-descriptions-item label="影像分析">
          <pre style="margin:0;white-space:pre-wrap;">{{ report.image_analysis }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="AI诊断建议">
          <pre style="margin:0;white-space:pre-wrap;background:#f0f9eb;padding:8px;border-radius:4px;">{{ report.diagnosis_suggest }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="生成时间">
          {{ report.create_time }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 操作按钮组 -->
      <div style="margin-top:16px;display:flex;gap:10px;">
        <el-button type="success" @click="goToPdfReport" size="large">
          📄 生成PDF报告
        </el-button>
        <el-button @click="viewDicom" size="large" v-if="report.dicom_file_path">
          🖼️ 查看DICOM影像
        </el-button>
      </div>
    </el-card>

    <!-- 关联医学知识（知识图谱辅助决策） -->
    <el-card v-if="hasKnowledge" shadow="never" style="margin-top:20px;border-left:3px solid #409EFF;">
      <template #header>
        <span style="font-weight:bold;font-size:16px;">🧬 关联医学知识</span>
        <span style="color:var(--text-muted);font-size:12px;margin-left:8px;">来源：医学知识图谱</span>
      </template>

      <!-- 相关疾病 -->
      <div v-if="knowledge.related_info?.length">
        <h4 style="margin:0 0 10px;">相关疾病</h4>
        <el-collapse accordion>
          <el-collapse-item
            v-for="d in knowledge.related_info"
            :key="d.disease"
            :title="d.disease"
            :name="d.disease"
          >
            <div style="line-height:1.9;">
              <div v-if="d.symptoms?.length">
                症状：
                <el-tag v-for="s in d.symptoms" :key="s" size="small" type="info" style="margin-right:6px;">
                  {{ s }}
                </el-tag>
              </div>
              <div v-if="d.medications?.length" style="margin-top:4px;">常用药：{{ d.medications.join('、') }}</div>
              <div v-if="d.treatments?.length" style="margin-top:4px;">治疗：{{ d.treatments.join('、') }}</div>
              <div v-if="d.departments?.length" style="margin-top:4px;">所属科室：{{ d.departments.join('、') }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 用药相互作用预警 -->
      <div v-if="knowledge.drug_warnings?.length" style="margin-top:16px;">
        <h4 style="margin:0 0 10px;color:#E6A23C;">⚠️ 用药相互作用预警</h4>
        <el-alert
          v-for="w in knowledge.drug_warnings"
          :key="w.drug + w.interacts_with"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom:8px;"
        >
          <template #title>{{ w.drug }} ↔ {{ w.interacts_with }}</template>
          {{ w.description }}
        </el-alert>
      </div>

      <!-- 并发症风险 -->
      <div v-if="knowledge.complications?.length" style="margin-top:16px;">
        <h4 style="margin:0 0 10px;">并发症风险</h4>
        <el-tag
          v-for="c in knowledge.complications"
          :key="c.disease + c.related_disease"
          type="danger"
          effect="light"
          style="margin-right:8px;margin-bottom:6px;"
        >{{ c.disease }} → {{ c.related_disease }}</el-tag>
      </div>
    </el-card>

    <!-- 历史诊断报告列表 -->
    <h3 style="margin-top:30px;">历史诊断报告</h3>
    <el-table :data="reportList" border v-loading="loading" style="width:100%">
      <el-table-column label="报告ID" prop="id" width="80"/>
      <el-table-column label="病历ID" prop="record_id" width="80"/>
      <el-table-column label="诊断建议" prop="diagnosis_suggest" min-width="300" show-overflow-tooltip/>
      <el-table-column label="生成时间" prop="create_time" width="170"/>
      <el-table-column label="操作" width="120">
        <template #default="scope">
          <el-button size="small" @click="viewReport(scope.row)">详情</el-button>
          <el-button size="small" type="primary" @click="goToPdfWithId(scope.row.id)">PDF</el-button>
          <el-button size="small" type="danger" @click="deleteReport(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const route = useRoute()
const router = useRouter()

const recordId = ref('')
const report = ref(null)
const generating = ref(false)
const loading = ref(false)
const reportList = ref([])
const recentRecords = ref([])

// ── 关联医学知识（知识图谱） ──
const knowledge = computed(() => report.value?.knowledge || {})
const hasKnowledge = computed(() => {
  const k = knowledge.value
  return !!(k.related_info?.length || k.drug_warnings?.length || k.complications?.length)
})

// ── 支持从路由参数传入 record_id ──
watch(() => route.query.record_id, (val) => {
  if (val) {
    recordId.value = val
    genDiagnosis()
  }
})

// ── 生成诊断 ──
const genDiagnosis = async () => {
  if (!recordId.value) return ElMessage.warning('请输入病历ID')
  generating.value = true
  report.value = null
  try {
    const res = await request.post(`/diagnosis/generate?record_id=${recordId.value}`)
    if (res.code === 200) {
      report.value = res.data
      ElMessage.success(res.msg || '诊断生成成功')
      loadReportList()
    } else {
      ElMessage.error(res.msg)
    }
  } catch (e) {
    ElMessage.error('诊断生成请求失败')
  } finally {
    generating.value = false
  }
}

// ── 查看报告详情 ──
const viewReport = async (row) => {
  try {
    const res = await request.get(`/diagnosis/${row.id}`)
    if (res.code === 200) report.value = res.data
  } catch (e) {
    ElMessage.error('获取报告详情失败')
  }
}

// ── 删除报告 ──
const deleteReport = async (id) => {
  try {
    await request.delete(`/diagnosis/${id}`)
    ElMessage.success('删除成功')
    if (report.value?.id === id) report.value = null
    loadReportList()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// ── 跳转到PDF报告 ──
const goToPdfReport = () => {
  if (report.value?.id) {
    router.push({ path: '/report', query: { report_id: report.value.id, action: 'generate' } })
  }
}

const goToPdfWithId = (id) => {
  router.push({ path: '/report', query: { report_id: id, action: 'generate' } })
}

// ── 查看DICOM影像 ──
const viewDicom = () => {
  if (report.value?.record_id) {
    router.push(`/dicom/${report.value.record_id}`)
  }
}

// ── 加载报告列表 ──
const loadReportList = async () => {
  loading.value = true
  try {
    const res = await request.get('/diagnosis/list/all')
    if (res.code === 200) reportList.value = res.data
  } finally {
    loading.value = false
  }
}

// ── 加载最近病历（供下拉选择） ──
const loadRecentRecords = async () => {
  try {
    const res = await request.get('/record/list/all', { params: { skip: 0, limit: 20 } })
    if (res.code === 200) recentRecords.value = res.data
  } catch (e) {
    // 静默失败
  }
}

onMounted(() => {
  loadReportList()
  loadRecentRecords()
  // 如果路由已有 record_id，自动触发
  if (route.query.record_id) {
    recordId.value = route.query.record_id
    genDiagnosis()
  }
})
</script>
