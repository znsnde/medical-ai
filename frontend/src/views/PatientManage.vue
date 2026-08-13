<template>
  <div>
    <h2>患者管理</h2>
    <div style="margin:15px 0;display:flex;gap:10px;">
      <el-button type="primary" @click="openAddDialog">新增患者</el-button>
      <el-input v-model="searchKeyword" placeholder="搜索患者姓名" style="width:200px;" clearable @clear="loadList" @keyup.enter="searchPatient"/>
      <el-button @click="searchPatient">搜索</el-button>
    </div>
    <el-table :data="patientList" border style="margin-top:10px" v-loading="loading">
      <el-table-column label="ID" prop="id" width="80"/>
      <el-table-column label="姓名" prop="name" width="120"/>
      <el-table-column label="年龄" prop="age" width="80"/>
      <el-table-column label="性别" prop="gender" width="80"/>
      <el-table-column label="手机号" prop="phone" width="150"/>
      <el-table-column label="创建时间" prop="create_time" width="170"/>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="openEditDialog(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="delPatient(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="addVisible" :title="isEdit ? '编辑患者' : '新增患者'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="姓名">
          <el-input v-model="form.name"></el-input>
        </el-form-item>
        <el-form-item label="年龄">
          <el-input v-model.number="form.age" type="number"></el-input>
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender">
            <el-radio value="男">男</el-radio>
            <el-radio value="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible=false">取消</el-button>
        <el-button type="primary" @click="submitPatient" :loading="saving">{{ isEdit ? '保存修改' : '提交' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const patientList = ref([])
const addVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const loading = ref(false)
const saving = ref(false)
const searchKeyword = ref('')

const form = ref({
  name: '', age: '', gender: '男', phone: ''
})

// 加载患者列表
const loadList = async () => {
  loading.value = true
  try {
    const res = await request.get('/patient/list/all')
    if (res.code === 200) patientList.value = res.data
  } catch (e) {
    ElMessage.error('获取患者列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索患者
const searchPatient = async () => {
  if (!searchKeyword.value) return loadList()
  loading.value = true
  try {
    const res = await request.get('/patient/list/all', { params: { skip: 0, limit: 100 } })
    if (res.code === 200) {
      patientList.value = res.data.filter(p => p.name.includes(searchKeyword.value))
    }
  } finally {
    loading.value = false
  }
}

// 打开新增弹窗
const openAddDialog = () => {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', age: '', gender: '男', phone: '' }
  addVisible.value = true
}

// 打开编辑弹窗
const openEditDialog = (row) => {
  isEdit.value = true
  editId.value = row.id
  form.value = { name: row.name, age: row.age, gender: row.gender, phone: row.phone }
  addVisible.value = true
}

// 提交新增/编辑
const submitPatient = async () => {
  if (!form.value.name) return ElMessage.warning('请输入姓名')
  if (!form.value.age) return ElMessage.warning('请输入年龄')

  saving.value = true
  try {
    if (isEdit.value) {
      const params = new URLSearchParams()
      Object.entries(form.value).forEach(([k, v]) => params.append(k, v))
      await request.put(`/patient/update/${editId.value}`, params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      ElMessage.success('修改成功')
    } else {
      const params = new URLSearchParams()
      Object.entries(form.value).forEach(([k, v]) => params.append(k, v))
      await request.post('/patient/add', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      ElMessage.success('新增成功')
    }
    addVisible.value = false
    loadList()
  } catch (e) {
    const detail = e.response?.data?.detail || e.message || '未知错误'
    ElMessage.error(`${isEdit.value ? '修改' : '新增'}失败：${detail}`)
  } finally {
    saving.value = false
  }
}

// 删除患者
const delPatient = async (id) => {
  try {
    await request.delete(`/patient/${id}`)
    ElMessage.success('删除成功')
    loadList()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => loadList())
</script>
