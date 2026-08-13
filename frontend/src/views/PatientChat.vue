<template>
  <div class="consult-wrap">
    <!-- 左侧：历史会话列表 -->
    <div class="history-sidebar" v-if="inProgress || sessions.length > 0">
      <div class="history-header">
        <h4>📋 对话历史</h4>
        <el-button size="small" @click="newChat" :type="!currentSessionId ? 'primary' : ''">新对话</el-button>
      </div>
      <div class="session-list">
        <div v-for="s in sessions" :key="s.id" class="session-item"
             :class="{ active: s.id === currentSessionId }"
             @click="loadSession(s.id)">
          <div class="session-title">{{ s.title || '新对话' }}</div>
          <div class="session-meta">{{ s.department }} · {{ s.message_count }}条</div>
          <el-button v-if="s.id === currentSessionId" text type="danger" size="small"
                     class="del-btn" @click.stop="deleteSession(s.id)">✕</el-button>
        </div>
      </div>
    </div>

    <!-- 右侧：对话区 -->
    <div class="chat-main">
      <div class="consult-header">
        <h2>🏥 AI 智能问诊</h2>
        <p class="subtitle" v-if="!inProgress">选择科室开始模拟问诊</p>
        <div v-else class="session-info">
          <el-tag type="success">{{ currentDept }}</el-tag>
          <el-button text size="small" @click="endConsultation">结束问诊</el-button>
        </div>
      </div>

      <!-- 科室选择 -->
      <div v-if="!inProgress && !currentSessionId" class="dept-select">
        <el-row :gutter="16">
          <el-col :span="6" v-for="dept in departments" :key="dept.name">
            <el-card shadow="hover" class="dept-card" @click="startConsultation(dept)">
              <div class="dept-icon">{{ dept.icon }}</div>
              <div class="dept-name">{{ dept.name }}</div>
              <div class="dept-desc">{{ dept.desc }}</div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 对话区 -->
      <div v-if="inProgress || currentSessionId" class="chat-area">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="AI 智能问诊为模拟问诊，由大模型自动回复，仅供参考，不构成医疗诊断或治疗建议；如有不适请及时前往医院就诊。"
          style="margin-bottom:12px;"
        />
        <div class="chat-box" ref="chatBoxRef">
          <div v-for="(item, index) in chatList" :key="index"
               :class="['chat-item', item.role === 'user' ? 'user-item' : 'ai-item']">
            <div class="chat-avatar">{{ item.role === 'user' ? '🧑' : '🩺' }}</div>
            <div class="chat-content">
              <div class="chat-bubble">{{ item.content }}</div>
              <div v-if="item.role === 'assistant' && item.suggestions && item.suggestions.length && index === chatList.length - 1"
                   class="suggestion-buttons">
                <el-button v-for="(sug, si) in item.suggestions" :key="si"
                  size="small" plain @click="sendQuickReply(sug)" :disabled="loading" class="sug-btn">{{ sug }}</el-button>
              </div>
            </div>
          </div>
          <div v-if="loading" class="chat-item ai-item">
            <div class="chat-avatar">🩺</div>
            <div class="chat-bubble thinking">AI 医生正在思考...</div>
          </div>
        </div>
        <div class="chat-input-bar">
          <el-input v-model="userInput" placeholder="输入你的症状描述..." @keyup.enter="sendMessage"
            :disabled="loading" size="large">
            <template #append><el-button @click="sendMessage" :loading="loading" type="primary">发送</el-button></template>
          </el-input>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const departments = [
  { name: '内科', icon: '🫁', desc: '头痛发热、咳嗽、高血压等' },
  { name: '外科', icon: '🦴', desc: '骨折、外伤、腰腿疼痛等' },
  { name: '神经内科', icon: '🧠', desc: '头痛、眩晕、失眠、中风等' },
  { name: '骨科', icon: '🦵', desc: '颈椎病、腰椎间盘突出等' },
  { name: '妇产科', icon: '👶', desc: '妇科炎症、孕期保健、产后康复等' },
  { name: '儿科', icon: '🍼', desc: '小儿发热、咳嗽、腹泻、生长发育等' },
  { name: '皮肤科', icon: '🔬', desc: '皮疹、过敏、痤疮、真菌感染等' },
  { name: '眼科', icon: '👁️', desc: '视力下降、结膜炎、干眼症等' },
]

const inProgress = ref(false)
const currentDept = ref('')
const loading = ref(false)
const userInput = ref('')
const chatList = ref([])
const chatBoxRef = ref(null)
const sessions = ref([])
const currentSessionId = ref(null)

// 加载历史会话列表
const loadSessions = async () => {
  try {
    const res = await request.get('/consultation/sessions')
    if (res.code === 200) sessions.value = res.data || []
  } catch { /* ignore */ }
}

// 加载某次会话
const loadSession = async (id) => {
  currentSessionId.value = id
  loading.value = true
  try {
    const res = await request.get(`/consultation/session/${id}`)
    if (res.code === 200) {
      chatList.value = (res.data || []).map((m, i) => ({
        ...m,
        role: m.role,
        content: m.content,
        suggestions: m.role === 'assistant' && i === res.data.length - 1 ? [] : undefined
      }))
      inProgress.value = true
      // 找到对应的会话获取科室
      const s = sessions.value.find(s => s.id === id)
      if (s) currentDept.value = s.department
    }
  } catch { ElMessage.error('加载对话失败') }
  finally { loading.value = false; scrollToBottom() }
}

// 删除会话
const deleteSession = async (id) => {
  try {
    await ElMessageBox.confirm('删除此对话？', '确认')
    await request.delete(`/consultation/session/${id}`)
    if (currentSessionId.value === id) { newChat() }
    loadSessions()
  } catch { /* cancel */ }
}

// 新对话
const newChat = () => {
  inProgress.value = false
  currentSessionId.value = null
  chatList.value = []
  currentDept.value = ''
}

// 开始问诊
const startConsultation = async (dept) => {
  currentDept.value = dept.name
  currentSessionId.value = null
  inProgress.value = true
  loading.value = true
  chatList.value = [{ role: 'assistant', content: `你好！我是${dept.name}AI医生。请描述一下你哪里不舒服？`, suggestions: [] }]
  try {
    const msgs = chatList.value.map(m => ({ role: m.role, content: m.content }))
    const res = await request.post('/consultation/chat', { messages: msgs, department: dept.name })
    if (res.code === 200 && res.data) {
      chatList.value = [{ role: 'assistant', content: res.data.reply, suggestions: res.data.suggestions || [] }]
      currentSessionId.value = res.data.session_id
      loadSessions()
    }
  } catch { /* ignore */ }
  finally { loading.value = false; scrollToBottom() }
}

// 发送消息
const sendMessage = async () => {
  const text = userInput.value.trim()
  if (!text) return
  userInput.value = ''
  await doSend(text)
}

const sendQuickReply = async (text) => { await doSend(text) }

const doSend = async (text) => {
  chatList.value.push({ role: 'user', content: text })
  loading.value = true
  scrollToBottom()
  try {
    const msgs = chatList.value.map(m => ({ role: m.role, content: m.content }))
    const res = await request.post('/consultation/chat', {
      messages: msgs,
      session_id: currentSessionId.value,
      department: currentDept.value
    })
    if (res.code === 200 && res.data) {
      chatList.value.push({ role: 'assistant', content: res.data.reply, suggestions: res.data.suggestions || [] })
      if (res.data.session_id && !currentSessionId.value) {
        currentSessionId.value = res.data.session_id
        loadSessions()
      }
    }
  } catch {
    chatList.value.push({ role: 'assistant', content: '网络连接失败，请检查后端服务。', suggestions: ['重试'] })
  } finally {
    loading.value = false; scrollToBottom()
  }
}

const endConsultation = () => { newChat() }

const scrollToBottom = () => { nextTick(() => { if (chatBoxRef.value) chatBoxRef.value.scrollTop = chatBoxRef.value.scrollHeight }) }

onMounted(loadSessions)
</script>

<style scoped>
.consult-wrap { display: flex; gap: 16px; height: calc(100vh - 100px); }

/* ── 历史侧栏 ── */
.history-sidebar { width: 240px; flex-shrink: 0; display: flex; flex-direction: column; }
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.history-header h4 { margin: 0; font-size: 14px; }
.session-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.session-item {
  padding: 10px 12px; border-radius: 8px; cursor: pointer; position: relative;
  background: rgba(255,255,255,0.03); transition: all 0.2s;
}
.session-item:hover { background: rgba(0,122,255,0.06); }
.session-item.active { background: rgba(0,122,255,0.1); }
.session-title { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 20px; }
.session-meta { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
.del-btn { position: absolute; top: 4px; right: 4px; }

/* ── 对话主区 ── */
.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.consult-header { margin-bottom: 16px; }
.consult-header h2 { margin: 0; font-size: 18px; }
.subtitle { color: var(--text-secondary); font-size: 13px; margin: 4px 0 0; }
.session-info { display: flex; align-items: center; gap: 8px; margin-top: 4px; }

.dept-card { cursor: pointer; text-align: center; border-radius: 12px; transition: transform 0.2s; }
.dept-card:hover { transform: translateY(-4px); }
.dept-icon { font-size: 36px; margin-bottom: 6px; }
.dept-name { font-size: 14px; font-weight: 600; }
.dept-desc { font-size: 11px; color: var(--text-secondary); margin-top: 4px; }

.chat-area { flex: 1; display: flex; flex-direction: column; }
.chat-box { flex: 1; overflow-y: auto; padding: 16px; background: rgba(255,255,255,0.03); border-radius: 12px; margin-bottom: 12px; }
.chat-item { display: flex; gap: 10px; margin-bottom: 16px; }
.user-item { flex-direction: row-reverse; }
.chat-avatar { font-size: 24px; flex-shrink: 0; line-height: 36px; }
.chat-content { max-width: 70%; }
.chat-bubble { padding: 10px 14px; border-radius: 12px; line-height: 1.6; font-size: 14px; white-space: pre-wrap; }
.ai-item .chat-bubble { background: rgba(255,255,255,0.06); }
.user-item .chat-bubble { background: #007AFF; color: #fff; border-top-right-radius: 4px; }
.thinking { color: var(--text-secondary); font-style: italic; }

.suggestion-buttons { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.sug-btn { font-size: 12px; border-radius: 16px; }

.chat-input-bar { margin-top: 4px; }

/* 暗色主题适配 */
html.theme-day .session-item { background: rgba(0,0,0,0.02); }
html.theme-day .session-item:hover { background: rgba(0,122,255,0.04); }
html.theme-day .session-item.active { background: rgba(0,122,255,0.08); }
html.theme-day .chat-box { background: rgba(0,0,0,0.02); }
html.theme-day .ai-item .chat-bubble { background: #f0f0f0; color: #1E293B; }
</style>
