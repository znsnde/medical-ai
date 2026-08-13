<template>
  <div class="report-wrap" style="padding:20px;">
    <h2>诊断报告PDF生成与预览</h2>

    <el-card style="margin:20px 0;">
      <el-row style="align-items:center;">
        <el-input v-model="reportId" placeholder="输入诊断报告ID" style="width:300px;"></el-input>
        <el-button type="primary" @click="generatePdf" style="margin-left:10px;" :loading="generating">
          {{ generating ? 'PDF生成中...' : '生成PDF报告' }}
        </el-button>
      </el-row>
    </el-card>

    <!-- 报告生成结果 -->
    <el-card v-if="pdfInfo" class="pdf-card" style="margin-top:20px;">
      <template #header>
        <span style="font-weight:bold;">报告生成结果</span>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="患者姓名">{{ pdfInfo.report_info.patient_name }}</el-descriptions-item>
        <el-descriptions-item label="影像分析">
          <pre style="margin:0;white-space:pre-wrap;">{{ pdfInfo.report_info.image_analysis }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="AI诊断建议">
          <pre style="margin:0;white-space:pre-wrap;">{{ pdfInfo.report_info.diagnosis_suggest }}</pre>
        </el-descriptions-item>
      </el-descriptions>
      <div style="margin-top:15px;">
        <el-button type="success" @click="openPdf" :disabled="!pdfInfo.pdf_file_path">
          在线打开PDF文件
        </el-button>
      </div>
    </el-card>

    <!-- 全部报告列表 -->
    <h3 style="margin-top:30px;">全部报告列表</h3>
    <el-table :data="reportList" border v-loading="loading" style="width:100%">
      <el-table-column label="报告ID" prop="id" width="80"/>
      <el-table-column label="关联病历ID" prop="record_id" width="100"/>
      <el-table-column label="诊断建议" prop="diagnosis_suggest" min-width="250" show-overflow-tooltip/>
      <el-table-column label="PDF路径" prop="pdf_path" min-width="200" show-overflow-tooltip/>
      <el-table-column label="创建时间" prop="create_time" width="170"/>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="getPdfUrl(scope.row.id)" type="primary">PDF链接</el-button>
          <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
          <el-button size="small" type="danger" @click="deleteReport(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const route = useRoute()

const reportId = ref('')
const pdfInfo = ref(null)
const reportList = ref([])
const generating = ref(false)
const loading = ref(false)

// 生成PDF
const generatePdf = async () => {
  if (!reportId.value) return ElMessage.warning('请输入报告ID')
  generating.value = true
  try {
    const res = await request.post(`/report/pdf/generate?report_id=${reportId.value}`)
    if (res.code === 200) {
      pdfInfo.value = res.data
      ElMessage.success('PDF报告生成成功')
      loadReportList()
    } else {
      ElMessage.error(res.msg)
    }
  } catch (e) {
    ElMessage.error('PDF生成请求失败')
  } finally {
    generating.value = false
  }
}

// 打开PDF新窗口（优先用HTTP URL，兼容旧版返回的本地路径）
const openPdf = () => {
  const url = pdfInfo.value?.pdf_url || pdfInfo.value?.pdf_file_path
  if (url) {
    window.open(url)
  }
}

// 获取单条报告PDF链接
const getPdfUrl = async (rid) => {
  try {
    const res = await request.get(`/report/pdf/${rid}`)
    if (res.code === 200) {
      window.open(res.data.pdf_url)
    } else {
      ElMessage.warning(res.msg)
    }
  } catch (e) {
    ElMessage.error('获取PDF链接失败')
  }
}

// 查看报告详情
const viewDetail = async (row) => {
  try {
    const res = await request.get(`/diagnosis/${row.id}`)
    if (res.code === 200) {
      const pdfPath = res.data.pdf_path || ""
      pdfInfo.value = {
        report_info: res.data,
        pdf_file_path: pdfPath,
        pdf_url: pdfPath ? `/${pdfPath.replace(/\\/g, "/")}` : ""
      }
    }
  } catch (e) {
    ElMessage.error('获取报告详情失败')
  }
}

// 删除报告
const deleteReport = async (id) => {
  try {
    await ElMessageBox.confirm(`确定删除报告 #${id} 吗？此操作不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })
    const res = await request.delete(`/diagnosis/${id}`)
    if (res.code === 200) {
      ElMessage.success('报告已删除')
      if (pdfInfo.value?.report_info?.id === id) pdfInfo.value = null
      loadReportList()
    } else {
      ElMessage.error(res.msg || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除请求失败')
    }
  }
}

// 加载全部报告
const loadReportList = async () => {
  loading.value = true
  try {
    const res = await request.get('/diagnosis/list/all')
    if (res.code === 200) reportList.value = res.data
  } catch (e) {
    ElMessage.error('获取报告列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadReportList()
  // 支持从路由参数传入 report_id 和 action
  if (route.query.report_id) {
    reportId.value = route.query.report_id
    if (route.query.action === 'generate') {
      // 延迟一下等列表加载完再触发生成
      setTimeout(() => generatePdf(), 300)
    }
  }
})
</script>
