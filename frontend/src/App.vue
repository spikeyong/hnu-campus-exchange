<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import api from './api'

function storedUser() {
  try { return JSON.parse(localStorage.getItem('campus_user') || 'null') } catch { return null }
}

const tab = ref('discover')
const authMode = ref('phone-login')
const showAuth = ref(false)
const showPublish = ref(false)
const loading = ref(false)
const notice = ref('')
const error = ref('')
const listings = ref([])
const categories = ref([])
const transactions = ref([])
const myListings = ref([])
const favoriteListings = ref([])
const verifications = ref([])
const adminReports = ref([])
const selectedListing = ref(null)
const selectedTransaction = ref(null)
const messages = ref([])
const newMessage = ref('')
const cancelReason = ref('')
const publishFiles = ref([])
const verificationFile = ref(null)
const verificationChallenge = ref(null)
const currentUser = ref(storedUser())
const smsDebugCode = ref('')
const smsCountdown = ref(0)
const emailDebugCode = ref('')
const emailCountdown = ref(0)
const sceneFilter = ref('all')
const transactionRole = ref('all')
const transactionStatus = ref('active')
let smsTimer = null
let emailTimer = null

const authForm = reactive({ identifier: '', phone: '', sms_code: '', password: '', name: '' })
const filters = reactive({ keyword: '', category_id: '' })
const publishForm = reactive({ type: 'resource', category_id: '', title: '', description: '', price: 0, price_unit: '元', location: '', condition_level: '', service_mode: 'offline', available_time: '', expected_exchange: '' })
const requestForm = reactive({ proposed_price: 0, proposed_time: '', proposed_location: '', request_note: '' })
const reviewForm = reactive({ rating: 5, content: '' })
const reportForm = reactive({ reason: '', description: '' })
const verificationForm = reactive({ student_no: '', college: '', grade: '' })
const emailForm = reactive({ email: '', code: '' })
const reportResolution = reactive({})
const reviewNotes = reactive({})

const isLoggedIn = computed(() => Boolean(currentUser.value))
const isAdmin = computed(() => currentUser.value?.role === 'admin')
const isVerified = computed(() => currentUser.value?.verification_status === 'verified')
const resourceListings = computed(() => listings.value.filter((item) => item.type === 'resource'))
const skillListings = computed(() => listings.value.filter((item) => item.type === 'skill'))
const favoriteIds = computed(() => new Set(favoriteListings.value.map((item) => item.id)))
const filteredTransactions = computed(() => transactions.value.filter((item) => {
  const roleMatches = transactionRole.value === 'all'
    || (transactionRole.value === 'initiated' && item.initiator_id === currentUser.value?.id)
    || (transactionRole.value === 'received' && item.provider_id === currentUser.value?.id)
  const activeStatuses = ['pending_provider', 'pending_initiator', 'agreed', 'provider_confirmed', 'requester_confirmed']
  const statusMatches = transactionStatus.value === 'all'
    || (transactionStatus.value === 'active' && activeStatuses.includes(item.status))
    || (transactionStatus.value === 'completed' && item.status === 'completed')
    || (transactionStatus.value === 'closed' && ['cancelled', 'rejected'].includes(item.status))
  return roleMatches && statusMatches
}))
const visibleCategories = computed(() => categories.value.filter((item) => item.listing_type === 'both' || item.listing_type === publishForm.type))
const scenePresets = [
  { id: 'all', label: '全部', keyword: '', category: '' },
  { id: 'textbook', label: '教材', category: '教材与学习资料' },
  { id: 'digital', label: '数码', category: '数码设备' },
  { id: 'dorm', label: '宿舍', keyword: '宿舍' },
  { id: 'graduation', label: '毕业季', keyword: '毕业' },
  { id: 'freshman', label: '新生', keyword: '新生' },
]
const typeLabel = (type) => type === 'skill' ? '技能互助' : '资源置换'
const statusLabel = (status) => ({
  pending_provider: '等待发布者处理',
  pending_initiator: '等待发起者确认协议',
  agreed: '协议已达成',
  in_progress: '需求方已确认收到',
  provider_confirmed: '发布者已确认交付',
  requester_confirmed: '需求方已确认收到',
  completed: '交易已完成',
  cancelled: '已取消',
  rejected: '已拒绝',
}[status] || status)
const verificationLabel = (status) => ({
  unverified: '尚未认证',
  pending: '人工审核中',
  verified: currentUser.value?.verification_method === 'demo' ? '课程演示认证' : '平台人工认证',
  rejected: '认证未通过',
}[status] || '尚未认证')

function errorMessage(err, fallback) {
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join('；')
  return detail || fallback
}

function flash(message, isError = false) {
  if (isError) error.value = message
  else notice.value = message
  window.setTimeout(() => { notice.value = ''; error.value = '' }, 3600)
}

function saveUser(user) {
  currentUser.value = user
  if (user) localStorage.setItem('campus_user', JSON.stringify(user))
  else localStorage.removeItem('campus_user')
}

function mediaUrl(path) {
  if (!path || /^https?:\/\//.test(path)) return path
  const base = api.defaults.baseURL || ''
  if (/^https?:\/\//.test(base)) return new URL(path, new URL(base).origin).href
  return path
}

async function refreshCurrentUser() {
  if (!localStorage.getItem('campus_token')) return
  try {
    saveUser((await api.get('/auth/me')).data)
  } catch {
    localStorage.removeItem('campus_token')
    saveUser(null)
  }
}

async function loadCategories() {
  try { categories.value = (await api.get('/listings/categories')).data } catch { flash('服务暂时不可用，请确认后端已启动', true) }
}

async function loadListings() {
  loading.value = true
  try {
    const params = { keyword: filters.keyword || undefined, category_id: filters.category_id || undefined, page_size: 50 }
    listings.value = (await api.get('/listings', { params })).data.items
  } catch (err) {
    flash(errorMessage(err, '列表加载失败，请稍后重试'), true)
  } finally {
    loading.value = false
  }
}

async function loadTransactions() {
  if (!isLoggedIn.value) return
  try { transactions.value = (await api.get('/transactions')).data } catch (err) { flash(errorMessage(err, '交易记录加载失败'), true) }
}

async function loadMyListings() {
  if (!isLoggedIn.value || isAdmin.value) return
  try { myListings.value = (await api.get('/listings/mine')).data } catch (err) { flash(errorMessage(err, '我的发布加载失败'), true) }
}

async function loadFavorites() {
  if (!isLoggedIn.value || isAdmin.value) return
  try { favoriteListings.value = (await api.get('/listings/favorites/mine')).data } catch (err) { flash(errorMessage(err, '收藏加载失败'), true) }
}

async function applyScene(scene) {
  sceneFilter.value = scene.id
  filters.keyword = scene.keyword || ''
  const category = categories.value.find((item) => item.name === scene.category)
  filters.category_id = category?.id || ''
  await loadListings()
}

function switchAuth(mode) {
  authMode.value = mode
  smsDebugCode.value = ''
  error.value = ''
}

async function sendSms() {
  if (!/^1[3-9]\d{9}$/.test(authForm.phone)) {
    flash('请输入有效的 11 位手机号', true)
    return
  }
  try {
    const purpose = authMode.value === 'register' ? 'register' : 'login'
    const { data } = await api.post('/auth/sms/send', { phone: authForm.phone, purpose })
    smsDebugCode.value = data.debug_code || ''
    smsCountdown.value = data.retry_after
    window.clearInterval(smsTimer)
    smsTimer = window.setInterval(() => {
      smsCountdown.value -= 1
      if (smsCountdown.value <= 0) window.clearInterval(smsTimer)
    }, 1000)
    flash('验证码已发送')
  } catch (err) {
    flash(errorMessage(err, '验证码发送失败'), true)
  }
}

async function submitAuth() {
  loading.value = true
  try {
    const payload = authMode.value === 'admin-login'
      ? { identifier: authForm.identifier.trim(), password: authForm.password }
      : authMode.value === 'phone-login'
        ? { phone: authForm.phone, sms_code: authForm.sms_code }
        : { phone: authForm.phone, sms_code: authForm.sms_code, name: authForm.name.trim() }
    const endpoint = authMode.value === 'admin-login' ? '/auth/login' : authMode.value === 'phone-login' ? '/auth/sms/login' : '/auth/register'
    const { data } = await api.post(endpoint, payload)
    localStorage.setItem('campus_token', data.access_token)
    saveUser(data.user)
    showAuth.value = false
    if (authMode.value === 'register') {
      selectedListing.value = null
      tab.value = 'verification'
      flash('手机号注册完成，请继续完成学生认证')
    } else {
      flash('欢迎回来')
      if (data.user.role === 'admin') {
        selectedListing.value = null
        tab.value = 'admin'
        await loadAdmin()
      }
    }
    if (data.user.role !== 'admin') await loadTransactions()
  } catch (err) {
    flash(errorMessage(err, '操作失败，请检查输入'), true)
  } finally {
    loading.value = false
  }
}

function logout() {
  localStorage.removeItem('campus_token')
  saveUser(null)
  transactions.value = []
  myListings.value = []
  favoriteListings.value = []
  verifications.value = []
  adminReports.value = []
  selectedListing.value = null
  selectedTransaction.value = null
  tab.value = 'discover'
  flash('已退出登录')
}

function requireVerified() {
  if (!isLoggedIn.value) {
    showAuth.value = true
    return false
  }
  if (isAdmin.value) {
    tab.value = 'admin'
    flash('管理员账号不参与学生交易', true)
    return false
  }
  if (!isVerified.value) {
    tab.value = 'verification'
    flash('完成学生认证后才能进行此操作', true)
    return false
  }
  return true
}

function resetPublish(type = 'resource') {
  const firstCategory = categories.value.find((item) => item.listing_type === type || item.listing_type === 'both')
  Object.assign(publishForm, { type, category_id: firstCategory?.id || '', title: '', description: '', price: 0, price_unit: '元', location: '', condition_level: '', service_mode: 'offline', available_time: '', expected_exchange: '' })
  publishFiles.value = []
}

function openPublish(type = 'resource') {
  if (!requireVerified()) return
  resetPublish(type)
  showPublish.value = true
}

function selectPublishFiles(event) {
  publishFiles.value = Array.from(event.target.files || []).slice(0, 6)
}

async function createListing() {
  try {
    const { data } = await api.post('/listings', { ...publishForm, category_id: Number(publishForm.category_id), price: Number(publishForm.price) })
    for (const file of publishFiles.value) {
      const formData = new FormData()
      formData.append('file', file)
      await api.post('/listings/' + data.id + '/images', formData)
    }
    showPublish.value = false
    flash('发布成功，已进入双轨看板')
    await Promise.all([loadListings(), loadMyListings()])
  } catch (err) {
    flash(errorMessage(err, '发布失败'), true)
  }
}

function openListing(listing) {
  selectedListing.value = listing
  Object.assign(requestForm, { proposed_price: listing.price, proposed_time: '', proposed_location: listing.location || '', request_note: '' })
}

async function toggleFavorite(listing) {
  if (!isLoggedIn.value) {
    showAuth.value = true
    return
  }
  try {
    if (favoriteIds.value.has(listing.id)) await api.delete('/listings/' + listing.id + '/favorite')
    else await api.post('/listings/' + listing.id + '/favorite')
    await loadFavorites()
    flash(favoriteIds.value.has(listing.id) ? '已收藏' : '已取消收藏')
  } catch (err) {
    flash(errorMessage(err, '收藏操作失败'), true)
  }
}

async function changeListingStatus(item) {
  const nextStatus = item.status === 'published' ? 'offline' : 'published'
  try {
    await api.patch('/listings/mine/' + item.id + '/status', { status: nextStatus })
    flash(nextStatus === 'published' ? '发布已重新上架' : '发布已下架')
    await Promise.all([loadMyListings(), loadListings()])
  } catch (err) {
    flash(errorMessage(err, '状态更新失败'), true)
  }
}

function prepareListingRequest() {
  if (!isLoggedIn.value) {
    showAuth.value = true
    return
  }
  selectedListing.value = null
  tab.value = 'verification'
  flash('完成学生认证后才能发起交易', true)
}

async function submitRequest() {
  try {
    await api.post('/transactions?listing_id=' + selectedListing.value.id, { ...requestForm, proposed_price: Number(requestForm.proposed_price) })
    selectedListing.value = null
    flash('请求已发出，等待发布者回应')
    await loadTransactions()
  } catch (err) {
    flash(errorMessage(err, '请求发起失败'), true)
  }
}

async function transactionAction(id, action) {
  try {
    const { data } = await api.post('/transactions/' + id + '/' + action)
    if (selectedTransaction.value?.id === id) selectedTransaction.value = data
    flash('交易状态已更新')
    await loadTransactions()
  } catch (err) {
    flash(errorMessage(err, '操作失败'), true)
  }
}

async function simulatePayment(item) {
  try {
    const { data } = await api.post('/transactions/' + item.id + '/simulate-payment')
    if (selectedTransaction.value?.id === item.id) selectedTransaction.value = data
    flash('课程演示付款已记录，不会发生真实扣款')
    await loadTransactions()
  } catch (err) {
    flash(errorMessage(err, '模拟付款失败'), true)
  }
}

async function openTransaction(item) {
  selectedTransaction.value = item
  messages.value = []
  newMessage.value = ''
  cancelReason.value = ''
  Object.assign(reviewForm, { rating: 5, content: '' })
  Object.assign(reportForm, { reason: '', description: '' })
  try { messages.value = (await api.get('/transactions/' + item.id + '/messages')).data } catch (err) { flash(errorMessage(err, '消息加载失败'), true) }
}

function canCancelTransaction(item) {
  if (!item || !currentUser.value) return false
  if (['pending_provider', 'pending_initiator'].includes(item.status)) return item.initiator_id === currentUser.value.id
  return item.status === 'agreed'
}

async function cancelTransaction() {
  const reason = cancelReason.value.trim()
  if (reason.length < 2) {
    flash('请填写至少 2 个字的取消原因', true)
    return
  }
  try {
    const { data } = await api.post('/transactions/' + selectedTransaction.value.id + '/cancel', null, { params: { reason } })
    selectedTransaction.value = data
    cancelReason.value = ''
    flash('交易已取消')
    await loadTransactions()
    await loadListings()
  } catch (err) {
    flash(errorMessage(err, '取消失败'), true)
  }
}

async function sendMessage() {
  if (!newMessage.value.trim()) return
  try {
    const { data } = await api.post('/transactions/' + selectedTransaction.value.id + '/messages', { content: newMessage.value })
    messages.value.push(data)
    newMessage.value = ''
  } catch (err) {
    flash(errorMessage(err, '消息发送失败'), true)
  }
}

async function submitReview() {
  try {
    await api.post('/transactions/' + selectedTransaction.value.id + '/reviews', reviewForm)
    flash('评价已提交')
    reviewForm.content = ''
  } catch (err) {
    flash(errorMessage(err, '评价提交失败'), true)
  }
}

async function submitReport() {
  const item = selectedTransaction.value
  const targetId = currentUser.value.id === item.initiator_id ? item.provider_id : item.initiator_id
  try {
    await api.post('/reports', { target_type: 'user', target_id: targetId, transaction_id: item.id, ...reportForm })
    flash('举报已提交，管理员会结合协议和消息处理')
    Object.assign(reportForm, { reason: '', description: '' })
  } catch (err) {
    flash(errorMessage(err, '举报提交失败'), true)
  }
}

async function createVerificationChallenge() {
  try {
    verificationChallenge.value = (await api.post('/auth/verification/challenge')).data
  } catch (err) {
    flash(errorMessage(err, '挑战码生成失败'), true)
  }
}

function selectVerificationFile(event) {
  verificationFile.value = event.target.files?.[0] || null
}

async function submitVerification() {
  if (!verificationChallenge.value || !verificationFile.value) {
    flash('请先生成挑战码并选择认证照片', true)
    return
  }
  const formData = new FormData()
  formData.append('challenge_id', verificationChallenge.value.id)
  formData.append('student_no', verificationForm.student_no)
  formData.append('college', verificationForm.college)
  formData.append('grade', verificationForm.grade)
  formData.append('evidence', verificationFile.value)
  loading.value = true
  try {
    await api.post('/auth/verification/submit', formData)
    verificationChallenge.value = null
    verificationFile.value = null
    await refreshCurrentUser()
    flash('认证材料已提交，等待管理员人工审核')
  } catch (err) {
    flash(errorMessage(err, '认证材料提交失败'), true)
  } finally {
    loading.value = false
  }
}

async function submitDemoVerification() {
  loading.value = true
  try {
    const { data } = await api.post('/auth/verification/demo', { ...verificationForm })
    saveUser(data)
    flash('课程演示认证已通过；未连接学校或学信网')
  } catch (err) {
    flash(errorMessage(err, '演示认证失败'), true)
  } finally {
    loading.value = false
  }
}

async function sendEmailCode() {
  if (!/^\S+@\S+\.\S+$/.test(emailForm.email)) {
    flash('请输入有效的邮箱地址', true)
    return
  }
  try {
    const { data } = await api.post('/auth/email/send', { email: emailForm.email })
    emailDebugCode.value = data.debug_code || ''
    emailCountdown.value = data.retry_after
    window.clearInterval(emailTimer)
    emailTimer = window.setInterval(() => {
      emailCountdown.value -= 1
      if (emailCountdown.value <= 0) window.clearInterval(emailTimer)
    }, 1000)
    flash('邮箱验证码已发送')
  } catch (err) {
    flash(errorMessage(err, '邮箱验证码发送失败'), true)
  }
}

async function bindEmail() {
  try {
    const { data } = await api.post('/auth/email/bind', { email: emailForm.email, code: emailForm.code })
    saveUser(data)
    emailForm.code = ''
    emailDebugCode.value = ''
    flash('邮箱绑定完成；邮箱不作为学生身份证明')
  } catch (err) {
    flash(errorMessage(err, '邮箱绑定失败'), true)
  }
}

async function unbindEmail() {
  if (!window.confirm('确定解绑当前邮箱？手机号登录和学生认证状态不会改变。')) return
  try {
    await api.delete('/auth/email')
    await refreshCurrentUser()
    emailForm.email = ''
    flash('邮箱已解绑')
  } catch (err) {
    flash(errorMessage(err, '邮箱解绑失败'), true)
  }
}

async function loadAdmin() {
  if (!isAdmin.value) return
  try {
    const [verificationResponse, reportResponse] = await Promise.all([api.get('/admin/verifications'), api.get('/admin/reports')])
    verifications.value = verificationResponse.data
    adminReports.value = reportResponse.data
  } catch (err) {
    flash(errorMessage(err, '管理员数据加载失败'), true)
  }
}

async function viewEvidence(item) {
  try {
    const response = await api.get('/admin/verifications/' + item.id + '/evidence', { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (err) {
    flash(errorMessage(err, '认证材料读取失败'), true)
  }
}

async function reviewVerification(item, action) {
  const fallback = action === 'approve' ? '材料核验通过' : '材料无法证明在校学生身份'
  try {
    await api.post('/admin/verifications/' + item.id + '/' + action, null, { params: { review_note: reviewNotes[item.id]?.trim() || fallback } })
    flash(action === 'approve' ? '学生认证已通过' : '认证申请已驳回')
    await loadAdmin()
  } catch (err) {
    flash(errorMessage(err, '认证处理失败'), true)
  }
}

async function resolveReport(report) {
  const resolution = reportResolution[report.id]?.trim()
  if (!resolution) {
    flash('请先填写处理结论', true)
    return
  }
  try {
    await api.post('/admin/reports/' + report.id + '/resolve', { resolution, score_delta: 0 })
    flash('举报已处理')
    await loadAdmin()
  } catch (err) {
    flash(errorMessage(err, '处理失败'), true)
  }
}

function navigate(nextTab) {
  tab.value = nextTab
  if (nextTab === 'transactions') loadTransactions()
  if (nextTab === 'my-listings') loadMyListings()
  if (nextTab === 'favorites') loadFavorites()
  if (nextTab === 'admin') loadAdmin()
}

onMounted(async () => {
  await refreshCurrentUser()
  await Promise.all([loadCategories(), loadListings()])
  if (isAdmin.value) {
    tab.value = 'admin'
    await loadAdmin()
  } else {
    await Promise.all([loadTransactions(), loadMyListings(), loadFavorites()])
  }
})

onBeforeUnmount(() => {
  window.clearInterval(smsTimer)
  window.clearInterval(emailTimer)
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <button class="brand" @click="navigate('discover')">
        <span class="brand-mark">环</span>
        <span><b>海大互助</b><small>Campus Loop</small></span>
      </button>
      <nav aria-label="主导航">
        <button :class="{ active: tab === 'discover' }" @click="navigate('discover')"><span>⌂</span>双轨广场</button>
        <button v-if="!isAdmin" :class="{ active: tab === 'transactions' }" @click="navigate('transactions')"><span>⇄</span>我的交易</button>
        <button v-if="isLoggedIn && !isAdmin" :class="{ active: tab === 'my-listings' }" @click="navigate('my-listings')"><span>▤</span>我的发布</button>
        <button v-if="isLoggedIn && !isAdmin" :class="{ active: tab === 'favorites' }" @click="navigate('favorites')"><span>☆</span>我的收藏</button>
        <button v-if="isLoggedIn && !isAdmin" :class="{ active: tab === 'verification' }" @click="navigate('verification')"><span>✓</span>学生认证</button>
        <button v-if="isAdmin" :class="{ active: tab === 'admin' }" @click="navigate('admin')"><span>◇</span>管理工作台</button>
      </nav>
      <div class="sidebar-note">
        <b>交易边界</b>
        平台记录协议与双方确认，不托管资金，也不核验线下付款。
      </div>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <span class="crumb">海南大学校园互助平台</span>
          <span class="environment">桌面端 Demo</span>
        </div>
        <div class="top-actions">
          <button v-if="isLoggedIn" class="account-button" @click="navigate(isAdmin ? 'admin' : 'profile')">
            <span class="avatar">{{ currentUser.name.slice(0, 1) }}</span>
            <span><b>{{ currentUser.name }}</b><small>{{ currentUser.account_masked }}</small></span>
          </button>
          <button v-if="isLoggedIn" class="ghost-btn" @click="logout">退出</button>
          <button v-else class="outline-btn" @click="showAuth = true">登录 / 注册</button>
          <button v-if="!isAdmin" class="primary-btn" @click="openPublish('resource')">＋ 发布</button>
        </div>
      </header>

      <main>
        <section v-if="tab === 'discover'" class="page discover-page">
          <header class="page-heading">
            <div>
              <p class="eyebrow">CAMPUS EXCHANGE BOARD</p>
              <h1>校园资源与技能</h1>
              <p>资源置换与技能互助并行展示，所有交易沿用同一套协议与双方确认规则。</p>
            </div>
            <div class="trust-summary">
              <span><b>{{ listings.length }}</b>公开信息</span>
              <span><b>双方</b>完成确认</span>
              <span><b>不</b>托管资金</span>
            </div>
          </header>

          <nav class="scene-strip" aria-label="校园场景快捷筛选">
            <span>场景直达</span>
            <button v-for="scene in scenePresets" :key="scene.id" :class="{ selected: sceneFilter === scene.id }" @click="applyScene(scene)">{{ scene.label }}</button>
          </nav>

          <div class="filter-bar">
            <label class="search-box"><span>⌕</span><input v-model="filters.keyword" placeholder="搜索教材、设备、辅导或技能" @keyup.enter="loadListings" /></label>
            <select v-model="filters.category_id" @change="loadListings">
              <option value="">全部分类</option>
              <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
            <button class="outline-btn" @click="loadListings">筛选</button>
          </div>

          <div v-if="loading" class="state-panel">正在整理广场信息...</div>
          <div v-else class="dual-board">
            <section class="lane resource-lane">
              <header class="lane-header">
                <div><span class="lane-dot"></span><h2>资源置换</h2><small>{{ resourceListings.length }} 条</small></div>
                <button v-if="!isAdmin" class="icon-action" title="发布资源" @click="openPublish('resource')">＋</button>
              </header>
              <div v-if="!resourceListings.length" class="lane-empty">
                <b>暂无匹配资源</b><span>教材、数码设备和生活用品会显示在这里。</span>
                <button v-if="!isAdmin" class="text-btn" @click="openPublish('resource')">发布第一条资源</button>
              </div>
              <article v-for="item in resourceListings" :key="item.id" class="board-item">
                <div class="item-media resource">
                  <img v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" />
                  <span v-else>资源</span>
                </div>
                <div class="item-body">
                  <div class="item-kicker"><span>{{ item.category_name }}</span><time>{{ new Date(item.created_at).toLocaleDateString('zh-CN') }}</time></div>
                  <h3>{{ item.title }}</h3>
                  <p>{{ item.description }}</p>
                  <div class="item-meta"><span>{{ item.location || '校内协商' }}</span><span>{{ item.owner_name }}</span></div>
                </div>
                <div class="item-action">
                  <strong>{{ item.price ? '¥' + item.price : '免费' }}</strong>
                  <small v-if="item.price">/ {{ item.price_unit }}</small>
                  <button class="small-action" @click="openListing(item)">查看详情</button>
                </div>
              </article>
            </section>

            <section class="lane skill-lane">
              <header class="lane-header">
                <div><span class="lane-dot"></span><h2>技能互助</h2><small>{{ skillListings.length }} 条</small></div>
                <button v-if="!isAdmin" class="icon-action" title="发布技能" @click="openPublish('skill')">＋</button>
              </header>
              <div v-if="!skillListings.length" class="lane-empty">
                <b>暂无匹配技能</b><span>学习辅导、设计协助和技术支持会显示在这里。</span>
                <button v-if="!isAdmin" class="text-btn" @click="openPublish('skill')">发布第一条技能</button>
              </div>
              <article v-for="item in skillListings" :key="item.id" class="board-item">
                <div class="item-media skill">
                  <img v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" />
                  <span v-else>技能</span>
                </div>
                <div class="item-body">
                  <div class="item-kicker"><span>{{ item.category_name }}</span><time>{{ new Date(item.created_at).toLocaleDateString('zh-CN') }}</time></div>
                  <h3>{{ item.title }}</h3>
                  <p>{{ item.description }}</p>
                  <div class="item-meta"><span>{{ item.service_mode === 'online' ? '线上' : item.service_mode === 'both' ? '线上 / 线下' : (item.location || '校内协商') }}</span><span>{{ item.owner_name }}</span></div>
                </div>
                <div class="item-action">
                  <strong>{{ item.price ? '¥' + item.price : '免费' }}</strong>
                  <small v-if="item.price">/ {{ item.price_unit }}</small>
                  <button class="small-action skill" @click="openListing(item)">查看详情</button>
                </div>
              </article>
            </section>
          </div>
        </section>

        <section v-else-if="tab === 'transactions'" class="page narrow-page">
          <header class="page-heading"><div><p class="eyebrow">TRANSACTION WORKSPACE</p><h1>我的交易</h1><p>协议、消息与双方完成确认集中处理。</p></div><button class="outline-btn" @click="loadTransactions">刷新</button></header>
          <div v-if="!isLoggedIn" class="state-panel"><strong>登录后查看你的交易</strong><button class="primary-btn" @click="showAuth = true">登录</button></div>
          <template v-else>
            <div class="workspace-filter">
              <div class="segmented compact-segmented"><button :class="{ selected: transactionRole === 'all' }" @click="transactionRole = 'all'">全部角色</button><button :class="{ selected: transactionRole === 'initiated' }" @click="transactionRole = 'initiated'">我发起的</button><button :class="{ selected: transactionRole === 'received' }" @click="transactionRole = 'received'">我收到的</button></div>
              <select v-model="transactionStatus" aria-label="交易状态筛选"><option value="active">进行中</option><option value="completed">已完成</option><option value="closed">已关闭</option><option value="all">全部状态</option></select>
            </div>
          </template>
          <div v-if="isLoggedIn && !transactions.length" class="state-panel"><strong>还没有交易记录</strong><span>从双轨广场发起一笔资源或技能交易。</span></div>
          <div v-else-if="isLoggedIn && !filteredTransactions.length" class="state-panel"><strong>没有符合当前条件的交易</strong><span>尝试切换角色或状态筛选。</span></div>
          <div v-else-if="isLoggedIn" class="transaction-list">
            <article v-for="item in filteredTransactions" :key="item.id" class="transaction-card">
              <div class="transaction-head"><div><span class="record-id">TRANSACTION / {{ item.id }}</span><h2>{{ item.listing_title }}</h2></div><span class="status-pill">{{ statusLabel(item.status) }}</span></div>
              <div class="agreement-row"><span>¥ {{ item.agreed_price || item.proposed_price }}</span><span>{{ item.proposed_time || '时间待协商' }}</span><span>{{ item.proposed_location || '地点待协商' }}</span></div>
              <p>{{ item.request_note }}</p>
              <p v-if="item.demo_payment_status === 'simulated_paid'" class="demo-payment-line">课程演示付款已记录，不代表真实资金支付</p>
              <div class="transaction-actions">
                <button class="outline-btn" @click="openTransaction(item)">消息与协议</button>
                <button v-if="item.status === 'pending_provider' && item.provider_id === currentUser.id" class="ghost-btn danger" @click="transactionAction(item.id, 'reject')">拒绝</button>
                <button v-if="item.status === 'pending_provider' && item.provider_id === currentUser.id" class="primary-btn" @click="transactionAction(item.id, 'accept')">接受请求</button>
                <button v-if="item.status === 'pending_initiator' && item.initiator_id === currentUser.id" class="primary-btn" @click="transactionAction(item.id, 'agree')">确认协议</button>
                <button v-if="currentUser.demo_features_enabled && item.initiator_id === currentUser.id && ['agreed','provider_confirmed','requester_confirmed'].includes(item.status) && item.demo_payment_status !== 'simulated_paid' && Number(item.agreed_price || item.proposed_price) > 0" class="outline-btn demo-action" @click="simulatePayment(item)">模拟付款</button>
                <button v-if="['agreed','in_progress','requester_confirmed'].includes(item.status) && item.provider_id === currentUser.id && !item.provider_completed_at" class="primary-btn" @click="transactionAction(item.id, 'provider-complete')">确认已交付</button>
                <button v-if="['agreed','provider_confirmed'].includes(item.status) && item.initiator_id === currentUser.id && !item.requester_completed_at" class="primary-btn" @click="transactionAction(item.id, 'requester-complete')">确认已收到</button>
              </div>
            </article>
          </div>
          <p class="boundary-note">线下付款由双方自行完成。平台不托管资金，也不验证微信或其他线下付款的真伪。</p>
        </section>

        <section v-else-if="tab === 'my-listings'" class="page narrow-page">
          <header class="page-heading"><div><p class="eyebrow">MY LISTINGS</p><h1>我的发布</h1><p>分别管理资源和技能，上下架不会改变已经达成的交易。</p></div><button class="primary-btn" @click="openPublish('resource')">＋ 新发布</button></header>
          <div v-if="!myListings.length" class="state-panel"><strong>还没有发布内容</strong><span>从资源或技能开始发布第一条信息。</span></div>
          <div v-else class="management-list">
            <article v-for="item in myListings" :key="item.id" class="management-row">
              <div class="item-media" :class="item.type"><img v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" /><span v-else>{{ item.type === 'skill' ? '技能' : '资源' }}</span></div>
              <div class="admin-info"><strong>{{ item.title }}</strong><span>{{ typeLabel(item.type) }} · {{ item.category_name }} · {{ item.location || '校内协商' }}</span><small>{{ item.status === 'published' ? '公开展示中' : item.status === 'offline' ? '已下架' : statusLabel(item.status) }}</small></div>
              <div class="admin-actions"><button class="outline-btn" @click="openListing(item)">查看</button><button v-if="['published','offline'].includes(item.status)" class="ghost-btn" @click="changeListingStatus(item)">{{ item.status === 'published' ? '下架' : '重新上架' }}</button></div>
            </article>
          </div>
        </section>

        <section v-else-if="tab === 'favorites'" class="page narrow-page">
          <header class="page-heading"><div><p class="eyebrow">SAVED ITEMS</p><h1>我的收藏</h1><p>回看感兴趣的资源和技能，不改变交易状态。</p></div><button class="outline-btn" @click="loadFavorites">刷新</button></header>
          <div v-if="!favoriteListings.length" class="state-panel"><strong>暂时没有收藏</strong><span>在详情页收藏后，会集中显示在这里。</span><button class="primary-btn" @click="navigate('discover')">去双轨广场</button></div>
          <div v-else class="management-list">
            <article v-for="item in favoriteListings" :key="item.id" class="management-row">
              <div class="item-media" :class="item.type"><img v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" /><span v-else>{{ item.type === 'skill' ? '技能' : '资源' }}</span></div>
              <div class="admin-info"><strong>{{ item.title }}</strong><span>{{ typeLabel(item.type) }} · {{ item.owner_name }} · ¥{{ item.price }}</span><small>{{ item.location || '校内协商' }}</small></div>
              <div class="admin-actions"><button class="outline-btn" @click="openListing(item)">查看详情</button><button class="ghost-btn danger" @click="toggleFavorite(item)">取消收藏</button></div>
            </article>
          </div>
        </section>

        <section v-else-if="tab === 'verification'" class="page narrow-page">
          <header class="page-heading"><div><p class="eyebrow">TRUST & IDENTITY</p><h1>学生认证</h1><p>课程演示认证和平台人工审核都会与手机号验证分开显示。</p></div><span class="status-pill">{{ verificationLabel(currentUser?.verification_status) }}</span></header>
          <div v-if="!isLoggedIn" class="state-panel"><strong>请先完成手机号注册</strong><button class="primary-btn" @click="showAuth = true">登录 / 注册</button></div>
          <template v-else>
            <section v-if="currentUser.demo_features_enabled && !isVerified && currentUser.verification_status !== 'pending'" class="demo-verification-panel">
              <div><span class="demo-badge">课程演示</span><h2>使用模拟学号快速体验完整流程</h2><p>只校验格式和唯一性，不连接海南大学、学信网或任何官方身份系统。</p></div>
              <form class="demo-verification-form" @submit.prevent="submitDemoVerification">
                <input v-model="verificationForm.student_no" required minlength="6" placeholder="演示学号，例如 DEMO20260001" />
                <input v-model="verificationForm.college" required minlength="2" placeholder="学院" />
                <input v-model="verificationForm.grade" required minlength="2" placeholder="年级" />
                <button class="outline-btn" :disabled="loading">模拟通过认证</button>
              </form>
            </section>
            <div class="verification-layout">
              <aside class="verification-steps">
                <div class="verification-step complete"><span>01</span><div><b>手机号已验证</b><p>{{ currentUser.account_masked }} 仅证明该号码由你控制，不是学生身份证明。</p></div></div>
                <div class="verification-step" :class="{ complete: isVerified, active: !isVerified }"><span>02</span><div><b>提交学生材料</b><p>学生证或海大 e 卡信息需与一次性挑战码出现在同一画面。</p></div></div>
                <div class="verification-step" :class="{ complete: isVerified }"><span>03</span><div><b>管理员人工审核</b><p>通过后显示“平台人工认证”，不代表学校官方背书。</p></div></div>
              </aside>
              <section class="verification-panel">
                <div v-if="isVerified" class="verification-result success"><b>{{ currentUser.verification_method === 'demo' ? '课程演示认证已通过' : '学生身份已通过平台人工认证' }}</b><p>{{ currentUser.verification_method === 'demo' ? '该状态仅用于展示课程项目完整流程，不是官方学生身份证明。' : '你现在可以发布资源或技能，并发起交易。' }}</p></div>
                <div v-else-if="currentUser.verification_status === 'pending'" class="verification-result pending"><b>认证材料正在人工审核</b><p>材料只对管理员可见，审核完成后状态会在下次进入页面时更新。</p><button class="outline-btn" @click="refreshCurrentUser">刷新状态</button></div>
                <form v-else @submit.prevent="submitVerification">
                  <h2>提交认证材料</h2>
                  <p class="form-intro">不采集自拍或人脸信息。请用照片证明材料属于本次申请，审核结束后原始文件会被删除。</p>
                  <div v-if="currentUser.verification_status === 'rejected'" class="inline-alert">上次申请未通过，请重新生成挑战码并提交清晰材料。</div>
                  <div class="challenge-box">
                    <div><small>15 分钟一次性挑战码</small><code>{{ verificationChallenge?.challenge_code || '尚未生成' }}</code></div>
                    <button type="button" class="outline-btn" @click="createVerificationChallenge">{{ verificationChallenge ? '重新获取' : '生成挑战码' }}</button>
                  </div>
                  <div class="form-grid">
                    <label>学号<input v-model="verificationForm.student_no" required minlength="6" placeholder="仅用于人工核验与防止重复认证" /></label>
                    <label>学院<input v-model="verificationForm.college" required minlength="2" placeholder="例如：信息科学技术学院" /></label>
                    <label>年级<input v-model="verificationForm.grade" required minlength="2" placeholder="例如：2024级" /></label>
                    <label>认证照片<input type="file" required accept="image/jpeg,image/png,image/webp" @change="selectVerificationFile" /><small>JPEG / PNG / WebP，最大 5 MB</small></label>
                  </div>
                  <button class="primary-btn" :disabled="loading || !verificationChallenge">提交管理员人工审核</button>
                </form>
              </section>
            </div>
          </template>
        </section>

        <section v-else-if="tab === 'admin'" class="page narrow-page">
          <header class="page-heading"><div><p class="eyebrow">OPERATIONS</p><h1>管理工作台</h1><p>认证材料与举报记录仅管理员可访问。</p></div><button class="outline-btn" @click="loadAdmin">刷新</button></header>
          <div class="section-title"><h2>认证审核</h2><span>{{ verifications.length }} 条待处理</span></div>
          <div v-if="!verifications.length" class="compact-state">当前没有待审核认证</div>
          <div v-else class="admin-list">
            <article v-for="item in verifications" :key="item.id" class="admin-row">
              <div class="avatar">{{ item.user_name.slice(0, 1) }}</div>
              <div class="admin-info">
                <strong>{{ item.user_name }}</strong>
                <span>{{ item.phone_masked }} · 学号 {{ item.student_no_masked }} · {{ item.college }} · {{ item.grade }}</span>
                <small>挑战码 {{ item.challenge_code }}</small>
                <input v-model="reviewNotes[item.id]" placeholder="审核意见（可选）" />
              </div>
              <div class="admin-actions">
                <button class="outline-btn" @click="viewEvidence(item)">查看材料</button>
                <button class="ghost-btn danger" @click="reviewVerification(item, 'reject')">驳回</button>
                <button class="primary-btn" @click="reviewVerification(item, 'approve')">通过</button>
              </div>
            </article>
          </div>

          <div class="section-title report-title"><h2>举报处理</h2><span>{{ adminReports.filter((item) => item.status !== 'resolved').length }} 条待处理</span></div>
          <div v-if="!adminReports.length" class="compact-state">当前没有举报记录</div>
          <div v-else class="admin-list">
            <article v-for="report in adminReports" :key="report.id" class="report-row">
              <div class="transaction-head"><div><span class="record-id">{{ report.reason }}</span><h3>举报 {{ report.target_type }} #{{ report.target_id }}</h3></div><span class="status-pill">{{ report.status }}</span></div>
              <p>{{ report.description }}</p>
              <template v-if="report.status !== 'resolved'"><textarea v-model="reportResolution[report.id]" rows="2" placeholder="填写核查结论和处理依据"></textarea><button class="primary-btn" @click="resolveReport(report)">完成处理</button></template>
              <p v-else class="resolution-text">处理结论：{{ report.resolution }}</p>
            </article>
          </div>
        </section>

        <section v-else-if="tab === 'profile'" class="page narrow-page">
          <header class="page-heading"><div><p class="eyebrow">ACCOUNT & SECURITY</p><h1>账号与安全</h1><p>手机号用于登录；邮箱绑定是独立联系方式，不代表学生身份。</p></div></header>
          <div class="profile-banner">
            <div class="avatar large-avatar">{{ currentUser.name.slice(0, 1) }}</div>
            <div><h2>{{ currentUser.name }}</h2><p>{{ currentUser.account_masked }} · {{ currentUser.college || '学院待认证' }}</p></div>
            <span class="status-pill">{{ verificationLabel(currentUser.verification_status) }}</span>
          </div>
          <div class="profile-grid">
            <div class="metric-box"><span>信用分</span><strong>{{ currentUser.credit_score }}</strong><small>由完成记录和信用事件形成</small></div>
            <div class="metric-box"><span>学生身份</span><strong class="metric-text">{{ verificationLabel(currentUser.verification_status) }}</strong><small>手机号和邮箱验证均不计入学生身份认证</small></div>
          </div>
          <button v-if="!isVerified && !isAdmin" class="primary-btn profile-action" @click="navigate('verification')">前往学生认证</button>
          <section class="account-security-panel">
            <div class="section-title"><div><h2>邮箱绑定</h2><p>用于接收平台通知和未来的账号恢复；不会被当作学生身份证明。</p></div><span class="status-pill">{{ currentUser.email_verified ? '已绑定' : '未绑定' }}</span></div>
            <div v-if="currentUser.email_verified" class="bound-account-row"><div><small>当前邮箱</small><strong>{{ currentUser.email_masked }}</strong></div><button class="ghost-btn danger" @click="unbindEmail">解绑</button></div>
            <form class="email-bind-form" @submit.prevent="bindEmail">
              <label>{{ currentUser.email_verified ? '更换邮箱' : '邮箱地址' }}<div class="input-action"><input v-model="emailForm.email" type="email" required maxlength="255" placeholder="支持常用个人邮箱" /><button type="button" :disabled="emailCountdown > 0" @click="sendEmailCode">{{ emailCountdown > 0 ? emailCountdown + 's' : '发送验证码' }}</button></div></label>
              <label>邮箱验证码<input v-model="emailForm.code" required inputmode="numeric" maxlength="6" placeholder="6 位验证码" /></label>
              <div v-if="emailDebugCode" class="debug-code">开发环境邮箱验证码：<b>{{ emailDebugCode }}</b></div>
              <button class="primary-btn">{{ currentUser.email_verified ? '验证并更换' : '验证并绑定' }}</button>
            </form>
          </section>
        </section>
      </main>
    </section>

    <div v-if="notice || error" class="toast" :class="{ error }" role="status">{{ notice || error }}</div>

    <div v-if="showAuth" class="modal-backdrop" @click.self="showAuth = false">
      <div class="modal auth-modal">
        <button class="modal-close" aria-label="关闭" @click="showAuth = false">×</button>
        <div class="segmented auth-segmented"><button :class="{ selected: authMode === 'phone-login' }" @click="switchAuth('phone-login')">手机号登录</button><button :class="{ selected: authMode === 'register' }" @click="switchAuth('register')">注册</button><button :class="{ selected: authMode === 'admin-login' }" @click="switchAuth('admin-login')">管理员</button></div>
        <h2>{{ authMode === 'register' ? '创建学生账号' : authMode === 'admin-login' ? '管理员登录' : '手机号登录' }}</h2>
        <p class="modal-subtitle">{{ authMode === 'register' ? '手机号只用于登录与账号安全，注册后还需完成学生认证。' : authMode === 'admin-login' ? '管理员使用独立后台账号和密码。' : '短信验证码用于登录，不代表学生身份。' }}</p>
        <form @submit.prevent="submitAuth">
          <label v-if="authMode === 'admin-login'">管理员账号<input v-model="authForm.identifier" required autocomplete="username" placeholder="管理员用户名" /></label>
          <template v-else>
            <label>手机号<div class="input-action"><input v-model="authForm.phone" required inputmode="tel" maxlength="11" placeholder="11 位手机号" /><button type="button" :disabled="smsCountdown > 0" @click="sendSms">{{ smsCountdown > 0 ? smsCountdown + 's' : '发送验证码' }}</button></div></label>
            <label>短信验证码<input v-model="authForm.sms_code" required inputmode="numeric" maxlength="6" placeholder="6 位验证码" /></label>
            <div v-if="smsDebugCode" class="debug-code">开发环境验证码：<b>{{ smsDebugCode }}</b></div>
            <label v-if="authMode === 'register'">姓名<input v-model="authForm.name" required minlength="2" placeholder="用于校内交易展示" /></label>
          </template>
          <label v-if="authMode === 'admin-login'">密码<input v-model="authForm.password" type="password" required minlength="8" autocomplete="current-password" placeholder="至少 8 位" /></label>
          <button class="primary-btn wide" :disabled="loading">{{ loading ? '处理中...' : authMode === 'register' ? '完成手机号注册' : '登录' }}</button>
        </form>
        <p v-if="authMode === 'admin-login'" class="demo-hint">开发管理员：admin / Admin123!</p>
      </div>
    </div>

    <div v-if="showPublish" class="modal-backdrop" @click.self="showPublish = false">
      <div class="modal wide-modal">
        <button class="modal-close" aria-label="关闭" @click="showPublish = false">×</button>
        <h2>发布{{ typeLabel(publishForm.type) }}</h2>
        <p class="modal-subtitle">先完成核心信息，再补充交付方式和图片；所有交易仍需双方确认。</p>
        <form @submit.prevent="createListing">
          <div class="segmented"><button type="button" :class="{ selected: publishForm.type === 'resource' }" @click="resetPublish('resource')">资源置换</button><button type="button" :class="{ selected: publishForm.type === 'skill' }" @click="resetPublish('skill')">技能互助</button></div>
          <section class="publish-section"><div class="publish-step"><span>01</span><div><h3>发布什么</h3><p>标题和说明会直接显示在双轨看板。</p></div></div><div class="form-grid">
            <label>分类<select v-model="publishForm.category_id" required><option v-for="item in visibleCategories" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
            <label>标题<input v-model="publishForm.title" required minlength="2" maxlength="160" placeholder="例如：高数同济七版，少量笔记" /></label>
            <label class="full">说明<textarea v-model="publishForm.description" required minlength="5" maxlength="4000" rows="4" placeholder="写清状态、范围、瑕疵和注意事项，减少重复沟通"></textarea><small>{{ publishForm.description.length }} / 4000</small></label>
          </div></section>
          <section class="publish-section"><div class="publish-step"><span>02</span><div><h3>价格与交付</h3><p>提前说清金额、时间和校内地点。</p></div></div><div class="form-grid">
            <label>金额<input v-model.number="publishForm.price" type="number" min="0" step="0.01" required /></label>
            <label>单位<input v-model="publishForm.price_unit" required placeholder="元 / 小时 / 次" /></label>
            <label>校内地点<input v-model="publishForm.location" placeholder="例如：海甸校区图书馆北门" /></label>
            <label v-if="publishForm.type === 'resource'">物品状态<input v-model="publishForm.condition_level" placeholder="例如：九成新，有少量划线" /></label>
            <label v-else>服务方式<select v-model="publishForm.service_mode"><option value="offline">线下</option><option value="online">线上</option><option value="both">线上 / 线下</option></select></label>
            <label v-if="publishForm.type === 'skill'" class="full">可服务时间<input v-model="publishForm.available_time" placeholder="例如：工作日晚 7 点后、周末下午" /></label>
            <label class="full">期望交换或补充条件<input v-model="publishForm.expected_exchange" maxlength="200" placeholder="选填，例如：价格可议，优先同校区" /></label>
          </div></section>
          <section class="publish-section"><div class="publish-step"><span>03</span><div><h3>实拍与展示</h3><p>图片只用于公开发布，不要上传证件或收款码。</p></div></div><div class="form-grid"><label class="full">图片<input type="file" multiple accept="image/jpeg,image/png,image/webp" @change="selectPublishFiles" /><small>最多 6 张，单张不超过 5 MB</small></label></div></section>
          <button class="primary-btn wide">发布到双轨看板</button>
        </form>
      </div>
    </div>

    <div v-if="selectedListing" class="modal-backdrop" @click.self="selectedListing = null">
      <div class="modal wide-modal">
        <button class="modal-close" aria-label="关闭" @click="selectedListing = null">×</button>
        <img v-if="selectedListing.image_urls?.length" class="detail-image" :src="mediaUrl(selectedListing.image_urls[0])" :alt="selectedListing.title" />
        <span class="type-tag" :class="selectedListing.type">{{ typeLabel(selectedListing.type) }}</span>
        <div class="detail-title-row"><h2>{{ selectedListing.title }}</h2><button v-if="isLoggedIn && !isAdmin && currentUser?.id !== selectedListing.owner_id" class="outline-btn" @click="toggleFavorite(selectedListing)">{{ favoriteIds.has(selectedListing.id) ? '取消收藏' : '☆ 收藏' }}</button></div>
        <p class="modal-description">{{ selectedListing.description }}</p>
        <div class="payment-note">平台不托管资金，也不验证线下微信付款。请在校内公共区域核验物品或服务。</div>
        <div v-if="currentUser?.id === selectedListing.owner_id" class="inline-alert detail-access-note">这是你的发布信息，不能向自己发起交易。</div>
        <div v-else-if="isAdmin" class="inline-alert detail-access-note">管理员账号只处理平台事务，不参与学生交易。</div>
        <div v-else-if="!isVerified" class="detail-access-note">
          <p>{{ isLoggedIn ? '完成学生认证后才能发起交易。' : '登录并完成学生认证后可以发起交易。' }}</p>
          <button class="primary-btn wide" @click="prepareListingRequest">{{ isLoggedIn ? '前往学生认证' : '登录后发起' }}</button>
        </div>
        <form v-else @submit.prevent="submitRequest">
          <div class="form-grid">
            <label>拟议金额<input v-model.number="requestForm.proposed_price" type="number" min="0" step="0.01" required /></label>
            <label>交付时间<input v-model="requestForm.proposed_time" placeholder="例如：周六 15:00" /></label>
            <label class="full">交付地点<input v-model="requestForm.proposed_location" placeholder="校内公共区域" /></label>
            <label class="full">请求说明<textarea v-model="requestForm.request_note" required minlength="2" rows="3"></textarea></label>
          </div>
          <button class="primary-btn wide">发起交易请求</button>
        </form>
      </div>
    </div>

    <div v-if="selectedTransaction" class="modal-backdrop" @click.self="selectedTransaction = null">
      <div class="modal wide-modal transaction-modal">
        <button class="modal-close" aria-label="关闭" @click="selectedTransaction = null">×</button>
        <div class="transaction-head"><div><span class="record-id">TRANSACTION / {{ selectedTransaction.id }}</span><h2>{{ selectedTransaction.listing_title }}</h2></div><span class="status-pill">{{ statusLabel(selectedTransaction.status) }}</span></div>
        <div class="agreement-summary"><div><span>协议金额</span><strong>¥ {{ selectedTransaction.agreed_price || selectedTransaction.proposed_price }}</strong></div><div><span>约定时间</span><strong>{{ selectedTransaction.proposed_time || '待协商' }}</strong></div><div><span>约定地点</span><strong>{{ selectedTransaction.proposed_location || '待协商' }}</strong></div></div>
        <div class="demo-payment-box" :class="{ paid: selectedTransaction.demo_payment_status === 'simulated_paid' }">
          <div><span class="demo-badge">课程演示</span><b>{{ selectedTransaction.demo_payment_status === 'simulated_paid' ? '模拟付款已记录' : '未记录模拟付款' }}</b><p>只演示订单状态，不调用微信、支付宝或任何真实资金接口。</p></div>
          <button v-if="currentUser.demo_features_enabled && selectedTransaction.initiator_id === currentUser.id && ['agreed','provider_confirmed','requester_confirmed'].includes(selectedTransaction.status) && selectedTransaction.demo_payment_status !== 'simulated_paid' && Number(selectedTransaction.agreed_price || selectedTransaction.proposed_price) > 0" class="outline-btn demo-action" @click="simulatePayment(selectedTransaction)">模拟付款</button>
        </div>
        <section class="dialog-section">
          <div class="dialog-heading"><b>交易消息</b><span>仅交易双方可见</span></div>
          <div class="message-list"><div v-if="!messages.length" class="message-empty">还没有消息</div><div v-for="message in messages" :key="message.id" class="message" :class="{ mine: message.sender_id === currentUser.id }"><small>{{ message.sender_name }}</small><span>{{ message.content }}</span></div></div>
          <form v-if="!['completed','cancelled','rejected'].includes(selectedTransaction.status)" class="message-form" @submit.prevent="sendMessage"><input v-model="newMessage" placeholder="输入交易消息" /><button class="primary-btn">发送</button></form>
        </section>
        <section v-if="selectedTransaction.status === 'completed'" class="dialog-section">
          <div class="dialog-heading"><b>交易评价</b><span>双方完成确认后开放</span></div>
          <form class="compact-form" @submit.prevent="submitReview"><label>评分<select v-model.number="reviewForm.rating"><option v-for="rating in 5" :key="rating" :value="rating">{{ rating }} 分</option></select></label><label>评价<textarea v-model="reviewForm.content" rows="2" maxlength="500"></textarea></label><button class="outline-btn">提交评价</button></form>
        </section>
        <details v-if="canCancelTransaction(selectedTransaction)" class="report-box cancellation-box">
          <summary>取消这笔交易</summary>
          <form class="compact-form" @submit.prevent="cancelTransaction"><label>取消原因<textarea v-model="cancelReason" required minlength="2" maxlength="255" rows="2" placeholder="协议达成后取消会保留原因，供争议处理参考"></textarea></label><button class="outline-btn danger">确认取消</button></form>
        </details>
        <details class="report-box"><summary>提交争议或举报</summary><form class="compact-form" @submit.prevent="submitReport"><label>原因<input v-model="reportForm.reason" required minlength="2" /></label><label>说明<textarea v-model="reportForm.description" required minlength="5" rows="3"></textarea></label><button class="outline-btn danger">提交举报</button></form></details>
      </div>
    </div>
  </div>
</template>
