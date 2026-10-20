<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '../api'
import AppIcon from './AppIcon.vue'

const emit = defineEmits(['toast'])

const tabs = [
  { key: 'overview', label: '概览', icon: 'grid' },
  { key: 'verifications', label: '认证审核', icon: 'shield' },
  { key: 'reports', label: '举报处理', icon: 'message' },
  { key: 'listings', label: '内容管理', icon: 'file' },
  { key: 'users', label: '用户管理', icon: 'user' },
  { key: 'categories', label: '分类管理', icon: 'box' },
  { key: 'logs', label: '操作日志', icon: 'clock' },
]

const activeTab = ref('overview')
const loading = ref(false)
const stats = ref(null)
const recentLogs = ref([])

const verifications = ref([])
const verificationStatus = ref('pending')
const reviewNotes = reactive({})

const reports = ref([])
const reportStatus = ref('all')
const selectedReport = ref(null)
const reportDetail = ref(null)
const reportBusy = ref(false)
const reportForm = reactive({ resolution: '', score_delta: 0, score_user_id: '' })

const listings = ref([])
const listingTotal = ref(0)
const listingPage = ref(1)
const listingPageSize = 10
const listingFilters = reactive({ keyword: '', status: 'all', type: '', featured: 'all', category_id: '' })
const selectedListing = ref(null)
const listingStatusDialog = reactive({ open: false, target: null, status: 'offline', reason: '' })
const featureDialog = reactive({ open: false, target: null, reason: '' })

const users = ref([])
const userTotal = ref(0)
const userPage = ref(1)
const userPageSize = 12
const userFilters = reactive({ q: '', status: 'all', verification_status: 'all' })
const selectedUser = ref(null)
const userStatusDialog = reactive({ open: false, target: null, action: 'disable', reason: '', offline_listings: true })

const categories = ref([])
const categoryForm = reactive({ open: false, id: null, name: '', listing_type: 'both', is_active: true, sort_order: 0 })

const logs = ref([])
const logTotal = ref(0)
const logPage = ref(1)
const logPageSize = 25
const logFilters = reactive({ action: '', target_type: '' })

const statCards = computed(() => {
  const data = stats.value || {}
  return [
    { label: '待审核认证', value: data.pending_verifications ?? '—', hint: '学生材料等待核验', tab: 'verifications', tone: 'amber' },
    { label: '待处理举报', value: data.pending_reports ?? '—', hint: '需要管理员核查', tab: 'reports', tone: 'coral' },
    { label: '公开帖子', value: data.listings_published ?? '—', hint: '正在广场展示', tab: 'listings', tone: 'teal' },
    { label: '精华帖', value: data.listings_featured ?? '—', hint: '被管理员推荐', tab: 'listings', tone: 'gold' },
    { label: '用户总数', value: data.users_total ?? '—', hint: '含管理员账号', tab: 'users', tone: 'blue' },
    { label: '已认证学生', value: data.users_verified ?? '—', hint: '已完成身份核验', tab: 'users', tone: 'green' },
    { label: '禁用账号', value: data.users_disabled ?? '—', hint: '需关注治理状态', tab: 'users', tone: 'muted' },
    { label: '进行中交易', value: data.transactions_active ?? '—', hint: '协议或交付阶段', tab: '', tone: 'peach' },
  ]
})

const categoryOptions = computed(() => categories.value.filter((item) => item.is_active))
const verificationLabel = (status) => ({ pending: '待审核', approved: '已通过', rejected: '已驳回' }[status] || status)
const listingStatusLabel = (status) => ({ published: '公开', offline: '已下架', reserved: '交易中', completed: '已完成', deleted: '已删除' }[status] || status)
const userStatusLabel = (status) => (status === 'active' ? '正常' : status === 'disabled' ? '已禁用' : status)
const reportStatusLabel = (status) => (status === 'pending' ? '待处理' : status === 'resolved' ? '已处理' : status)
const typeLabel = (type) => (type === 'resource' ? '资源' : type === 'skill' ? '技能' : type)
const verificationStatusLabel = (status) => ({ unverified: '未认证', pending: '审核中', verified: '已认证', rejected: '已驳回' }[status] || status)
const actionLabel = (action) => ({
  verification_approve: '通过认证',
  verification_reject: '驳回认证',
  listing_offline: '下架帖子',
  listing_restore: '恢复帖子',
  listing_feature: '加精',
  listing_unfeature: '取消精华',
  user_disable: '禁用用户',
  user_enable: '恢复用户',
  category_create: '新增分类',
  category_update: '更新分类',
  report_resolve: '处理举报',
}[action] || action)
const logTargetLabel = (target) => ({ listing: '帖子', user: '用户', verification: '认证', category: '分类', report: '举报' }[target] || target)

function toast(message, error = false) {
  emit('toast', message, error)
}

function errorMessage(error, fallback = '操作失败，请稍后再试') {
  return error?.response?.data?.detail || error?.message || fallback
}

function asDate(value) {
  if (!value) return null
  const text = String(value)
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text)
  return new Date(hasZone ? text : `${text}Z`)
}

function formatTime(value) {
  const date = asDate(value)
  if (!date) return '—'
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatDate(value) {
  const date = asDate(value)
  if (!date) return '—'
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function imageUrl(path) {
  return path || ''
}

async function loadStats() {
  const { data } = await api.get('/admin/stats')
  stats.value = data
}

async function loadRecentLogs() {
  const { data } = await api.get('/admin/logs', { params: { page: 1, page_size: 6 } })
  recentLogs.value = data.items
}

async function loadCategories() {
  try {
    const { data } = await api.get('/admin/categories')
    categories.value = data
  } catch (error) {
    console.warn('categories load failed', error)
  }
}

async function loadVerifications() {
  const { data } = await api.get('/admin/verifications', { params: { status: verificationStatus.value } })
  verifications.value = data
}

async function loadReports() {
  const { data } = await api.get('/admin/reports', { params: { status: reportStatus.value } })
  reports.value = data
}

async function loadListings() {
  const params = {
    page: listingPage.value,
    page_size: listingPageSize,
    status: listingFilters.status,
    keyword: listingFilters.keyword || undefined,
    type: listingFilters.type || undefined,
    category_id: listingFilters.category_id || undefined,
  }
  if (listingFilters.featured !== 'all') params.featured = listingFilters.featured === 'true'
  const { data } = await api.get('/admin/listings', { params })
  listings.value = data.items
  listingTotal.value = data.total
}

async function loadUsers() {
  const { data } = await api.get('/admin/users', {
    params: {
      page: userPage.value,
      page_size: userPageSize,
      q: userFilters.q || undefined,
      status: userFilters.status,
      verification_status: userFilters.verification_status,
    },
  })
  users.value = data.items
  userTotal.value = data.total
}

async function loadLogs(page = 1) {
  logPage.value = page
  const { data } = await api.get('/admin/logs', {
    params: {
      page: logPage.value,
      page_size: logPageSize,
      action: logFilters.action || undefined,
      target_type: logFilters.target_type || undefined,
    },
  })
  logs.value = data.items
  logTotal.value = data.total
}

async function loadOverview() {
  await Promise.all([loadStats(), loadRecentLogs()])
}

async function loadTab(tab = activeTab.value) {
  loading.value = true
  try {
    if (tab === 'overview') await loadOverview()
    else if (tab === 'verifications') await loadVerifications()
    else if (tab === 'reports') await loadReports()
    else if (tab === 'listings') await loadListings()
    else if (tab === 'users') await loadUsers()
    else if (tab === 'categories') await loadCategories()
    else if (tab === 'logs') await loadLogs(logPage.value)
  } catch (error) {
    toast(errorMessage(error, '管理数据加载失败'), true)
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await loadCategories()
  await loadTab()
  toast('管理数据已刷新')
}

function tabBadge(key) {
  if (!stats.value) return 0
  if (key === 'verifications') return stats.value.pending_verifications
  if (key === 'reports') return stats.value.pending_reports
  return 0
}

function switchTab(tab, event = null) {
  activeTab.value = tab
  const target = event?.currentTarget
  if (target) {
    requestAnimationFrame(() => target.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' }))
  }
}

watch(activeTab, (tab) => { loadTab(tab) })

onMounted(async () => {
  await loadCategories()
  await loadTab('overview')
})

async function changeVerificationStatus(status) {
  verificationStatus.value = status
  await loadTab('verifications')
}

async function viewEvidence(item) {
  if (!item.evidence_url) return
  try {
    const response = await api.get(item.evidence_url.replace(/^\/api\/v1/, ''), { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    window.open(url, '_blank', 'noopener')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (error) {
    toast(errorMessage(error, '认证材料打开失败'), true)
  }
}

async function reviewVerification(item, action) {
  if (action === 'reject' && !window.confirm(`确认驳回 ${item.user_name} 的认证申请？`)) return
  const note = (reviewNotes[item.id] || '').trim()
  try {
    await api.post(`/admin/verifications/${item.id}/${action}`, null, { params: { review_note: note || undefined } })
    delete reviewNotes[item.id]
    toast(action === 'approve' ? '认证已通过' : '认证已驳回')
    await Promise.all([loadVerifications(), loadStats(), loadRecentLogs()])
  } catch (error) {
    toast(errorMessage(error, '认证处理失败'), true)
  }
}

async function openReport(report) {
  selectedReport.value = report
  reportDetail.value = null
  try {
    const { data } = await api.get(`/admin/reports/${report.id}`)
    reportDetail.value = data
    reportForm.resolution = data.resolution || ''
    reportForm.score_delta = 0
    reportForm.score_user_id = data.target_user_id || ''
  } catch (error) {
    toast(errorMessage(error, '举报详情加载失败'), true)
    closeReport()
  }
}

function closeReport() {
  selectedReport.value = null
  reportDetail.value = null
}

async function reloadReport() {
  if (!selectedReport.value) return
  await openReport(selectedReport.value)
  await loadReports()
  await loadStats()
  await loadRecentLogs()
}

async function resolveSelectedReport() {
  if (!selectedReport.value) return
  const resolution = reportForm.resolution.trim()
  if (resolution.length < 2) {
    toast('请填写至少 2 个字的处理结论', true)
    return
  }
  if (Number(reportForm.score_delta) && !reportForm.score_user_id) {
    toast('调整信用分时必须指定目标用户', true)
    return
  }
  reportBusy.value = true
  try {
    await api.post(`/admin/reports/${selectedReport.value.id}/resolve`, {
      resolution,
      score_delta: Number(reportForm.score_delta) || 0,
      score_user_id: reportForm.score_user_id ? Number(reportForm.score_user_id) : null,
    })
    toast('举报已处理')
    await reloadReport()
  } catch (error) {
    toast(errorMessage(error, '举报处理失败'), true)
  } finally {
    reportBusy.value = false
  }
}

async function reportOfflineTarget() {
  if (!reportDetail.value?.target_id || reportDetail.value.target_type !== 'listing') return
  if (!window.confirm('确认下架这条被举报的帖子？')) return
  reportBusy.value = true
  try {
    await api.post(`/admin/listings/${reportDetail.value.target_id}/status`, {
      status: 'offline',
      reason: reportForm.resolution.trim() || '举报核查后下架',
    })
    toast('帖子已下架')
    await reloadReport()
  } catch (error) {
    toast(errorMessage(error, '下架失败'), true)
  } finally {
    reportBusy.value = false
  }
}

async function reportDisableTarget() {
  if (!reportDetail.value?.target_user_id) return
  if (!window.confirm('确认禁用该用户，并下架其公开帖子？')) return
  reportBusy.value = true
  try {
    await api.post(`/admin/users/${reportDetail.value.target_user_id}/disable`, {
      reason: reportForm.resolution.trim() || '举报核查后禁用账号',
      offline_listings: true,
    })
    toast('用户已禁用')
    await reloadReport()
  } catch (error) {
    toast(errorMessage(error, '禁用失败'), true)
  } finally {
    reportBusy.value = false
  }
}

function resetListingFilters() {
  listingFilters.keyword = ''
  listingFilters.status = 'all'
  listingFilters.type = ''
  listingFilters.featured = 'all'
  listingFilters.category_id = ''
  listingPage.value = 1
  loadTab('listings')
}

function searchListings() {
  listingPage.value = 1
  loadTab('listings')
}

function setListingPage(page) {
  listingPage.value = Math.max(1, page)
  loadTab('listings')
}

function openListingModal(item) {
  selectedListing.value = item
}

function openStatusDialog(item, status) {
  listingStatusDialog.open = true
  listingStatusDialog.target = item
  listingStatusDialog.status = status
  listingStatusDialog.reason = status === 'offline' ? '管理员核查后下架' : '管理员核查后恢复'
}

function closeStatusDialog() {
  listingStatusDialog.open = false
  listingStatusDialog.target = null
}

async function submitListingStatus() {
  const item = listingStatusDialog.target
  const reason = listingStatusDialog.reason.trim()
  if (!item || reason.length < 2) {
    toast('请填写至少 2 个字的原因', true)
    return
  }
  try {
    await api.post(`/admin/listings/${item.id}/status`, { status: listingStatusDialog.status, reason })
    toast(listingStatusDialog.status === 'offline' ? '帖子已下架' : '帖子已恢复')
    closeStatusDialog()
    await Promise.all([loadListings(), loadStats(), loadRecentLogs()])
  } catch (error) {
    toast(errorMessage(error, '帖子状态更新失败'), true)
  }
}

function openFeatureDialog(item) {
  featureDialog.open = true
  featureDialog.target = item
  featureDialog.reason = '内容有参考价值，推荐给更多同学'
}

function closeFeatureDialog() {
  featureDialog.open = false
  featureDialog.target = null
}

async function submitFeature() {
  const item = featureDialog.target
  const reason = featureDialog.reason.trim()
  if (!item || reason.length < 2) {
    toast('请填写至少 2 个字的加精理由', true)
    return
  }
  try {
    await api.post(`/admin/listings/${item.id}/feature`, { reason })
    toast('已标记为精华帖')
    closeFeatureDialog()
    await Promise.all([loadListings(), loadStats(), loadRecentLogs()])
  } catch (error) {
    toast(errorMessage(error, '加精失败'), true)
  }
}

async function removeFeature(item) {
  if (!window.confirm(`确认取消《${item.title}》的精华标记？`)) return
  try {
    await api.delete(`/admin/listings/${item.id}/feature`)
    toast('已取消精华')
    await Promise.all([loadListings(), loadStats(), loadRecentLogs()])
  } catch (error) {
    toast(errorMessage(error, '取消精华失败'), true)
  }
}

function resetUserFilters() {
  userFilters.q = ''
  userFilters.status = 'all'
  userFilters.verification_status = 'all'
  userPage.value = 1
  loadTab('users')
}

function searchUsers() {
  userPage.value = 1
  loadTab('users')
}

function setUserPage(page) {
  userPage.value = Math.max(1, page)
  loadTab('users')
}

async function openUser(user) {
  selectedUser.value = user
  try {
    const { data } = await api.get(`/admin/users/${user.id}`)
    selectedUser.value = data
  } catch (error) {
    toast(errorMessage(error, '用户详情加载失败'), true)
  }
}

function closeUser() {
  selectedUser.value = null
}

function openUserStatusDialog(user, action) {
  userStatusDialog.open = true
  userStatusDialog.target = user
  userStatusDialog.action = action
  userStatusDialog.reason = action === 'disable' ? '违反平台使用规范' : '账号恢复使用'
  userStatusDialog.offline_listings = true
}

function closeUserStatusDialog() {
  userStatusDialog.open = false
  userStatusDialog.target = null
}

async function submitUserStatus() {
  const user = userStatusDialog.target
  const reason = userStatusDialog.reason.trim()
  if (!user || reason.length < 2) {
    toast('请填写至少 2 个字的原因', true)
    return
  }
  try {
    if (userStatusDialog.action === 'disable') {
      await api.post(`/admin/users/${user.id}/disable`, {
        reason,
        offline_listings: userStatusDialog.offline_listings,
      })
      toast('用户已禁用')
    } else {
      await api.post(`/admin/users/${user.id}/enable`, { reason })
      toast('用户已恢复')
    }
    closeUserStatusDialog()
    if (selectedUser.value?.id === user.id) await openUser(user)
    await Promise.all([loadUsers(), loadStats(), loadRecentLogs()])
  } catch (error) {
    toast(errorMessage(error, '用户状态更新失败'), true)
  }
}

function openCategory(item = null) {
  categoryForm.open = true
  categoryForm.id = item?.id || null
  categoryForm.name = item?.name || ''
  categoryForm.listing_type = item?.listing_type || 'both'
  categoryForm.is_active = item?.is_active ?? true
  categoryForm.sort_order = item?.sort_order ?? (categories.value.length * 10)
}

function closeCategory() {
  categoryForm.open = false
}

async function saveCategory() {
  const name = categoryForm.name.trim()
  if (name.length < 2) {
    toast('分类名称至少 2 个字', true)
    return
  }
  const payload = {
    name,
    listing_type: categoryForm.listing_type,
    is_active: categoryForm.is_active,
    sort_order: Number(categoryForm.sort_order) || 0,
  }
  try {
    if (categoryForm.id) await api.patch(`/admin/categories/${categoryForm.id}`, payload)
    else await api.post('/admin/categories', payload)
    toast(categoryForm.id ? '分类已更新' : '分类已创建')
    closeCategory()
    await Promise.all([loadCategories(), loadStats(), loadRecentLogs()])
  } catch (error) {
    toast(errorMessage(error, '分类保存失败'), true)
  }
}

function resetLogFilters() {
  logFilters.action = ''
  logFilters.target_type = ''
  loadLogs(1)
}

function searchLogs() {
  loadLogs(1)
}
</script>

<template>
  <section class="page narrow-page admin-workspace">
    <header class="page-heading admin-heading">
      <div>
        <p class="admin-eyebrow">ADMIN CONTROL</p>
        <h1>管理工作台</h1>
        <p>认证、举报、内容、用户和分类都集中在这里；所有处理动作都会留下记录。</p>
      </div>
      <button class="outline-btn" @click="refresh">刷新数据</button>
    </header>

    <nav class="admin-tabs" aria-label="管理功能">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key, $event)"
      >
        <AppIcon :name="tab.icon" />
        <span>{{ tab.label }}</span>
        <b v-if="tabBadge(tab.key)" class="admin-tab-badge">{{ tabBadge(tab.key) }}</b>
      </button>
    </nav>

    <div v-if="loading" class="admin-loading">
      <span></span>
      正在加载管理数据…
    </div>

    <template v-else>
      <section v-if="activeTab === 'overview'" class="admin-panel">
        <div class="admin-stat-grid">
          <button
            v-for="card in statCards"
            :key="card.label"
            class="admin-stat-card"
            :class="`is-${card.tone}`"
            @click="card.tab && switchTab(card.tab)"
          >
            <span>{{ card.label }}</span>
            <b>{{ card.value }}</b>
            <small>{{ card.hint }}</small>
          </button>
        </div>

        <div class="admin-section-head">
          <div>
            <p class="admin-eyebrow">RECENT ACTIVITY</p>
            <h2>最近管理动作</h2>
          </div>
          <button class="text-btn" @click="switchTab('logs')">查看全部日志 <AppIcon name="arrow" /></button>
        </div>
        <div v-if="!recentLogs.length" class="admin-empty">还没有管理动作。处理认证或举报后会出现在这里。</div>
        <div v-else class="admin-log-list">
          <article v-for="item in recentLogs" :key="item.id" class="admin-log-row">
            <span class="admin-log-dot"></span>
            <div><b>{{ actionLabel(item.action) }}</b><p>{{ item.summary }}</p></div>
            <time>{{ formatTime(item.created_at) }}</time>
          </article>
        </div>
      </section>

      <section v-else-if="activeTab === 'verifications'" class="admin-panel">
        <div class="admin-section-head">
          <div>
            <p class="admin-eyebrow">STUDENT VERIFICATION</p>
            <h2>认证审核</h2>
          </div>
          <span class="admin-count">{{ verifications.length }} 条</span>
        </div>
        <div class="admin-segmented">
          <button v-for="status in ['pending', 'approved', 'rejected', 'all']" :key="status" :class="{ active: verificationStatus === status }" @click="changeVerificationStatus(status)">
            {{ status === 'all' ? '全部' : verificationLabel(status) }}
          </button>
        </div>
        <div v-if="!verifications.length" class="admin-empty">当前筛选下没有认证申请。</div>
        <div v-else class="admin-card-list">
          <article v-for="item in verifications" :key="item.id" class="admin-verification-card">
            <div class="admin-verification-main">
              <div class="admin-avatar">{{ item.user_name.slice(0, 1) }}</div>
              <div>
                <div class="admin-card-title">
                  <h3>{{ item.user_name }}</h3>
                  <span class="admin-status" :class="`status-${item.status}`">{{ verificationLabel(item.status) }}</span>
                </div>
                <p>{{ item.phone_masked }} · {{ item.college || '学院待补充' }} · {{ item.grade || '年级待补充' }}</p>
                <p class="admin-muted">学号 {{ item.student_no_masked || '未提供' }} · 提交于 {{ formatTime(item.submitted_at) }}</p>
                <p v-if="item.review_note" class="admin-note">审核意见：{{ item.review_note }}</p>
                <p v-if="item.reviewer_name" class="admin-muted">审核人：{{ item.reviewer_name }} · {{ formatTime(item.reviewed_at) }}</p>
              </div>
            </div>
            <div v-if="item.status === 'pending'" class="admin-verification-actions">
              <input v-model="reviewNotes[item.id]" placeholder="审核意见（可选）" />
              <button v-if="item.evidence_url" class="outline-btn" @click="viewEvidence(item)">查看材料</button>
              <button class="ghost-btn danger" @click="reviewVerification(item, 'reject')">驳回</button>
              <button class="primary-btn" @click="reviewVerification(item, 'approve')">通过</button>
            </div>
          </article>
        </div>
      </section>

      <section v-else-if="activeTab === 'reports'" class="admin-panel">
        <div class="admin-section-head">
          <div>
            <p class="admin-eyebrow">REPORT & DISPUTE</p>
            <h2>举报处理</h2>
          </div>
          <span class="admin-count">{{ reports.length }} 条</span>
        </div>
        <div class="admin-segmented">
          <button v-for="status in ['pending', 'resolved', 'all']" :key="status" :class="{ active: reportStatus === status }" @click="reportStatus = status; loadTab('reports')">
            {{ status === 'all' ? '全部' : reportStatusLabel(status) }}
          </button>
        </div>
        <div v-if="!reports.length" class="admin-empty">当前筛选下没有举报记录。</div>
        <div v-else class="admin-card-list">
          <article v-for="item in reports" :key="item.id" class="admin-report-card">
            <div class="admin-report-top">
              <div>
                <div class="admin-card-title">
                  <h3>举报 #{{ item.id }} · {{ item.target_label || `${item.target_type} #${item.target_id}` }}</h3>
                  <span class="admin-status" :class="`status-${item.status}`">{{ reportStatusLabel(item.status) }}</span>
                </div>
                <p>{{ item.reason }} · 举报人 {{ item.reporter_name || '未知' }} · {{ formatTime(item.created_at) }}</p>
              </div>
              <button class="outline-btn" @click="openReport(item)">查看处理</button>
            </div>
            <p class="admin-report-desc">{{ item.description }}</p>
            <p v-if="item.resolution" class="admin-note">处理结论：{{ item.resolution }}</p>
          </article>
        </div>
      </section>

      <section v-else-if="activeTab === 'listings'" class="admin-panel">
        <div class="admin-section-head">
          <div>
            <p class="admin-eyebrow">CONTENT MODERATION</p>
            <h2>内容管理</h2>
          </div>
          <span class="admin-count">共 {{ listingTotal }} 条</span>
        </div>
        <div class="admin-toolbar">
          <input v-model="listingFilters.keyword" placeholder="搜索标题或描述" @keyup.enter="searchListings" />
          <select v-model="listingFilters.status" @change="searchListings">
            <option value="all">全部状态</option><option value="published">公开</option><option value="offline">已下架</option><option value="reserved">交易中</option><option value="completed">已完成</option><option value="deleted">已删除</option>
          </select>
          <select v-model="listingFilters.type" @change="searchListings">
            <option value="">全部类型</option><option value="resource">资源</option><option value="skill">技能</option>
          </select>
          <select v-model="listingFilters.category_id" @change="searchListings">
            <option value="">全部分类</option><option v-for="category in categories" :key="category.id" :value="String(category.id)">{{ category.name }}</option>
          </select>
          <select v-model="listingFilters.featured" @change="searchListings">
            <option value="all">精华状态</option><option value="true">只看精华</option><option value="false">非精华</option>
          </select>
          <button class="primary-btn" @click="searchListings">筛选</button>
          <button class="ghost-btn" @click="resetListingFilters">重置</button>
        </div>
        <div v-if="!listings.length" class="admin-empty">没有匹配的帖子。</div>
        <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>帖子</th><th>类型 / 分类</th><th>发布者</th><th>状态</th><th>数据</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in listings" :key="item.id">
                <td><button class="admin-link" @click="openListingModal(item)">{{ item.title }}</button><small>{{ formatDate(item.created_at) }}</small></td>
                <td>{{ typeLabel(item.type) }} · {{ item.category_name || '未分类' }}</td>
                <td>{{ item.owner_name || '未知' }}<small v-if="item.owner_status === 'disabled'">账号已禁用</small></td>
                <td><span class="admin-status" :class="`status-${item.status}`">{{ listingStatusLabel(item.status) }}</span><span v-if="item.is_featured" class="admin-feature-tag">✦ 精华</span></td>
                <td><span v-if="item.report_count" class="admin-report-count">{{ item.report_count }} 条举报</span><span v-else class="admin-muted">无举报</span></td>
                <td class="admin-actions">
                  <button class="text-btn" @click="openListingModal(item)">查看</button>
                  <button v-if="item.status === 'published'" class="text-btn danger" @click="openStatusDialog(item, 'offline')">下架</button>
                  <button v-if="item.status === 'offline'" class="text-btn" @click="openStatusDialog(item, 'published')">恢复</button>
                  <button v-if="item.status === 'published' && !item.is_featured" class="text-btn" @click="openFeatureDialog(item)">加精</button>
                  <button v-if="item.is_featured" class="text-btn danger" @click="removeFeature(item)">取消精华</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="admin-pagination">
          <button class="outline-btn" :disabled="listingPage <= 1" @click="setListingPage(listingPage - 1)">上一页</button>
          <span>第 {{ listingPage }} 页 · 共 {{ listingTotal }} 条</span>
          <button class="outline-btn" :disabled="listingPage * listingPageSize >= listingTotal" @click="setListingPage(listingPage + 1)">下一页</button>
        </div>
      </section>

      <section v-else-if="activeTab === 'users'" class="admin-panel">
        <div class="admin-section-head">
          <div>
            <p class="admin-eyebrow">USER GOVERNANCE</p>
            <h2>用户管理</h2>
          </div>
          <span class="admin-count">共 {{ userTotal }} 人</span>
        </div>
        <div class="admin-toolbar">
          <input v-model="userFilters.q" placeholder="搜索姓名、账号或用户 ID" @keyup.enter="searchUsers" />
          <select v-model="userFilters.status" @change="searchUsers"><option value="all">全部状态</option><option value="active">正常</option><option value="disabled">已禁用</option></select>
          <select v-model="userFilters.verification_status" @change="searchUsers"><option value="all">全部认证</option><option value="verified">已认证</option><option value="pending">审核中</option><option value="unverified">未认证</option><option value="rejected">已驳回</option></select>
          <button class="primary-btn" @click="searchUsers">搜索</button>
          <button class="ghost-btn" @click="resetUserFilters">重置</button>
        </div>
        <div v-if="!users.length" class="admin-empty">没有匹配的用户。</div>
        <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>用户</th><th>角色 / 认证</th><th>信用</th><th>状态</th><th>内容 / 交易</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in users" :key="item.id">
                <td><button class="admin-link" @click="openUser(item)">{{ item.name }}</button><small>{{ item.account_masked }} · #{{ item.id }}</small></td>
                <td>{{ item.role === 'admin' ? '管理员' : '学生' }}<small>{{ verificationStatusLabel(item.verification_status) }}</small></td>
                <td><b class="admin-credit">{{ item.credit_score }}</b></td>
                <td><span class="admin-status" :class="`status-${item.status}`">{{ userStatusLabel(item.status) }}</span></td>
                <td>{{ item.listing_count }} 条发布<small>{{ item.completed_transactions }} 笔完成交易</small></td>
                <td class="admin-actions">
                  <button class="text-btn" @click="openUser(item)">详情</button>
                  <button v-if="item.role !== 'admin' && item.status === 'active'" class="text-btn danger" @click="openUserStatusDialog(item, 'disable')">禁用</button>
                  <button v-if="item.status === 'disabled'" class="text-btn" @click="openUserStatusDialog(item, 'enable')">恢复</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="admin-pagination">
          <button class="outline-btn" :disabled="userPage <= 1" @click="setUserPage(userPage - 1)">上一页</button>
          <span>第 {{ userPage }} 页 · 共 {{ userTotal }} 人</span>
          <button class="outline-btn" :disabled="userPage * userPageSize >= userTotal" @click="setUserPage(userPage + 1)">下一页</button>
        </div>
      </section>

      <section v-else-if="activeTab === 'categories'" class="admin-panel">
        <div class="admin-section-head">
          <div>
            <p class="admin-eyebrow">CATEGORY SYSTEM</p>
            <h2>分类管理</h2>
          </div>
          <button class="primary-btn" @click="openCategory()">新增分类</button>
        </div>
        <div v-if="!categories.length" class="admin-empty">还没有分类。</div>
        <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>分类名称</th><th>适用类型</th><th>帖子数</th><th>排序</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in categories" :key="item.id">
                <td><b>{{ item.name }}</b></td>
                <td>{{ item.listing_type === 'both' ? '通用' : typeLabel(item.listing_type) }}</td>
                <td>{{ item.listing_count }}</td>
                <td>{{ item.sort_order }}</td>
                <td><span class="admin-status" :class="item.is_active ? 'status-published' : 'status-offline'">{{ item.is_active ? '启用' : '停用' }}</span></td>
                <td class="admin-actions"><button class="text-btn" @click="openCategory(item)">编辑</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-else-if="activeTab === 'logs'" class="admin-panel">
        <div class="admin-section-head">
          <div>
            <p class="admin-eyebrow">AUDIT TRAIL</p>
            <h2>操作日志</h2>
          </div>
          <span class="admin-count">共 {{ logTotal }} 条</span>
        </div>
        <div class="admin-toolbar">
          <select v-model="logFilters.action" @change="searchLogs">
            <option value="">全部动作</option>
            <option v-for="action in ['verification_approve', 'verification_reject', 'listing_offline', 'listing_restore', 'listing_feature', 'listing_unfeature', 'report_resolve', 'user_disable', 'user_enable', 'category_create', 'category_update']" :key="action" :value="action">{{ actionLabel(action) }}</option>
          </select>
          <select v-model="logFilters.target_type" @change="searchLogs">
            <option value="">全部对象</option><option value="listing">帖子</option><option value="user">用户</option><option value="verification">认证</option><option value="report">举报</option><option value="category">分类</option>
          </select>
          <button class="ghost-btn" @click="resetLogFilters">重置</button>
        </div>
        <div v-if="!logs.length" class="admin-empty">还没有操作记录。</div>
        <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>时间</th><th>管理员</th><th>动作</th><th>对象</th><th>摘要</th></tr></thead>
            <tbody>
              <tr v-for="item in logs" :key="item.id">
                <td>{{ formatTime(item.created_at) }}</td>
                <td>{{ item.admin_name }}</td>
                <td><span class="admin-action-tag">{{ actionLabel(item.action) }}</span></td>
                <td>{{ logTargetLabel(item.target_type) }}<small v-if="item.target_id"> #{{ item.target_id }}</small></td>
                <td>{{ item.summary }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="admin-pagination">
          <button class="outline-btn" :disabled="logPage <= 1" @click="loadLogs(logPage - 1)">上一页</button>
          <span>第 {{ logPage }} 页 · 共 {{ logTotal }} 条</span>
          <button class="outline-btn" :disabled="logPage * logPageSize >= logTotal" @click="loadLogs(logPage + 1)">下一页</button>
        </div>
      </section>
    </template>

    <Teleport to="body">
      <div v-if="selectedReport" class="admin-modal-backdrop" @click.self="closeReport">
        <div class="admin-modal admin-modal-wide">
          <header class="admin-modal-head">
            <div><p class="admin-eyebrow">REPORT DETAIL</p><h2>举报 #{{ selectedReport.id }}</h2></div>
            <button class="icon-btn" aria-label="关闭" @click="closeReport"><AppIcon name="close" /></button>
          </header>
          <div v-if="!reportDetail" class="admin-empty">正在加载举报上下文…</div>
          <div v-else class="admin-report-detail">
            <div class="admin-detail-grid">
              <div><span>举报人</span><b>{{ reportDetail.reporter_name || '未知' }}</b></div>
              <div><span>处理状态</span><b>{{ reportStatusLabel(reportDetail.status) }}</b></div>
              <div><span>举报对象</span><b>{{ reportDetail.target_label || `${reportDetail.target_type} #${reportDetail.target_id}` }}</b></div>
              <div><span>关联交易</span><b>{{ reportDetail.transaction_title || (reportDetail.transaction_id ? `交易 #${reportDetail.transaction_id}` : '无') }}</b></div>
            </div>
            <div class="admin-detail-block"><span>举报原因</span><p>{{ reportDetail.reason }}</p><span>补充说明</span><p>{{ reportDetail.description }}</p></div>
            <div v-if="reportDetail.transaction_id" class="admin-transaction-context">
              <div><span>交易状态</span><b>{{ reportDetail.transaction_status || '—' }}</b></div>
              <div><span>约定金额</span><b>¥{{ reportDetail.transaction_price ?? '—' }}</b></div>
              <div><span>约定时间</span><b>{{ reportDetail.transaction_time || '待协商' }}</b></div>
              <div><span>约定地点</span><b>{{ reportDetail.transaction_location || '待协商' }}</b></div>
            </div>
            <div v-if="reportDetail.messages?.length" class="admin-messages">
              <p class="admin-eyebrow">TRANSACTION MESSAGES</p>
              <div v-for="message in reportDetail.messages" :key="message.id" class="admin-message"><b>{{ message.sender_name }}</b><span>{{ message.content }}</span><time>{{ formatTime(message.created_at) }}</time></div>
            </div>
            <div v-if="reportDetail.status === 'pending'" class="admin-resolve-box">
              <label>处理结论<textarea v-model="reportForm.resolution" rows="3" placeholder="写明核查结果和处理依据"></textarea></label>
              <div class="admin-inline-fields">
                <label>信用调整<input v-model.number="reportForm.score_delta" type="number" min="-100" max="100" /></label>
                <label>信用目标用户 ID<input v-model="reportForm.score_user_id" type="number" placeholder="仅调整信用时填写" /></label>
              </div>
              <div class="admin-resolve-actions">
                <button v-if="reportDetail.target_type === 'listing'" class="outline-btn danger" :disabled="reportBusy" @click="reportOfflineTarget">下架目标帖子</button>
                <button v-if="reportDetail.target_user_id" class="outline-btn danger" :disabled="reportBusy" @click="reportDisableTarget">禁用目标用户</button>
                <button class="primary-btn" :disabled="reportBusy" @click="resolveSelectedReport">完成处理</button>
              </div>
            </div>
            <div v-else class="admin-resolved-box"><b>处理结论</b><p>{{ reportDetail.resolution }}</p><small>{{ reportDetail.handler_name }} · {{ formatTime(reportDetail.handled_at) }}</small></div>
          </div>
        </div>
      </div>

      <div v-if="selectedListing" class="admin-modal-backdrop" @click.self="selectedListing = null">
        <div class="admin-modal admin-modal-wide">
          <header class="admin-modal-head">
            <div><p class="admin-eyebrow">LISTING DETAIL</p><h2>{{ selectedListing.title }}</h2></div>
            <button class="icon-btn" aria-label="关闭" @click="selectedListing = null"><AppIcon name="close" /></button>
          </header>
          <div class="admin-listing-detail">
            <div class="admin-listing-meta">
              <span class="admin-status" :class="`status-${selectedListing.status}`">{{ listingStatusLabel(selectedListing.status) }}</span>
              <span v-if="selectedListing.is_featured" class="admin-feature-tag">✦ 精华</span>
              <span>{{ typeLabel(selectedListing.type) }} · {{ selectedListing.category_name || '未分类' }}</span>
              <span>¥{{ selectedListing.price }} / {{ selectedListing.price_unit }}</span>
            </div>
            <div v-if="selectedListing.image_urls?.length" class="admin-listing-images"><img v-for="url in selectedListing.image_urls" :key="url" :src="imageUrl(url)" :alt="selectedListing.title" /></div>
            <p class="admin-listing-desc">{{ selectedListing.description }}</p>
            <div class="admin-detail-grid">
              <div><span>发布者</span><b>{{ selectedListing.owner_name || '未知' }}</b></div>
              <div><span>地点</span><b>{{ selectedListing.location || '校内协商' }}</b></div>
              <div><span>举报数</span><b>{{ selectedListing.report_count }}</b></div>
              <div><span>发布时间</span><b>{{ formatTime(selectedListing.created_at) }}</b></div>
            </div>
            <p v-if="selectedListing.status_reason" class="admin-note">管理备注：{{ selectedListing.status_reason }}</p>
          </div>
        </div>
      </div>

      <div v-if="listingStatusDialog.open" class="admin-modal-backdrop" @click.self="closeStatusDialog">
        <div class="admin-modal">
          <header class="admin-modal-head"><div><p class="admin-eyebrow">MODERATION</p><h2>{{ listingStatusDialog.status === 'offline' ? '下架帖子' : '恢复帖子' }}</h2></div><button class="icon-btn" @click="closeStatusDialog"><AppIcon name="close" /></button></header>
          <p class="admin-muted">{{ listingStatusDialog.target?.title }}</p>
          <label class="admin-field">处理原因<textarea v-model="listingStatusDialog.reason" rows="3" placeholder="写明处理依据"></textarea></label>
          <div class="admin-modal-actions"><button class="ghost-btn" @click="closeStatusDialog">取消</button><button class="primary-btn" @click="submitListingStatus">确认{{ listingStatusDialog.status === 'offline' ? '下架' : '恢复' }}</button></div>
        </div>
      </div>

      <div v-if="featureDialog.open" class="admin-modal-backdrop" @click.self="closeFeatureDialog">
        <div class="admin-modal">
          <header class="admin-modal-head"><div><p class="admin-eyebrow">FEATURED CONTENT</p><h2>标记为精华</h2></div><button class="icon-btn" @click="closeFeatureDialog"><AppIcon name="close" /></button></header>
          <p class="admin-muted">{{ featureDialog.target?.title }}</p>
          <label class="admin-field">加精理由<textarea v-model="featureDialog.reason" rows="3" placeholder="例如：内容详实，对同学有参考价值"></textarea></label>
          <div class="admin-modal-actions"><button class="ghost-btn" @click="closeFeatureDialog">取消</button><button class="primary-btn" @click="submitFeature">确认加精</button></div>
        </div>
      </div>

      <div v-if="selectedUser" class="admin-modal-backdrop" @click.self="closeUser">
        <div class="admin-modal admin-modal-wide">
          <header class="admin-modal-head"><div><p class="admin-eyebrow">USER DETAIL</p><h2>{{ selectedUser.name }}</h2></div><button class="icon-btn" @click="closeUser"><AppIcon name="close" /></button></header>
          <div class="admin-user-summary">
            <div class="admin-avatar large-avatar">{{ selectedUser.name.slice(0, 1) }}</div>
            <div><p>{{ selectedUser.account_masked }} · #{{ selectedUser.id }}</p><p class="admin-muted">{{ selectedUser.role === 'admin' ? '管理员' : '学生' }} · {{ verificationStatusLabel(selectedUser.verification_status) }} · 信用 {{ selectedUser.credit_score }}</p></div>
            <span class="admin-status" :class="`status-${selectedUser.status}`">{{ userStatusLabel(selectedUser.status) }}</span>
          </div>
          <p v-if="selectedUser.status_reason" class="admin-note">状态说明：{{ selectedUser.status_reason }}</p>
          <div class="admin-detail-grid">
            <div><span>发布内容</span><b>{{ selectedUser.listing_count }} 条</b></div>
            <div><span>完成交易</span><b>{{ selectedUser.completed_transactions }} 笔</b></div>
            <div><span>发起举报</span><b>{{ selectedUser.reports_filed }} 条</b></div>
            <div><span>被举报</span><b>{{ selectedUser.reports_against }} 条</b></div>
          </div>
          <div class="admin-subsection"><h3>最近发布</h3><div v-if="!selectedUser.listings?.length" class="admin-muted">暂无发布。</div><div v-else class="admin-mini-list"><span v-for="item in selectedUser.listings" :key="item.id">{{ item.title }} <b>{{ listingStatusLabel(item.status) }}</b></span></div></div>
          <div class="admin-subsection"><h3>信用记录</h3><div v-if="!selectedUser.credit_events?.length" class="admin-muted">暂无信用记录。</div><div v-else class="admin-mini-list"><span v-for="event in selectedUser.credit_events" :key="event.id">{{ event.reason }} <b>{{ event.score_delta > 0 ? '+' : '' }}{{ event.score_delta }}</b></span></div></div>
          <div class="admin-modal-actions">
            <button v-if="selectedUser.role !== 'admin' && selectedUser.status === 'active'" class="outline-btn danger" @click="openUserStatusDialog(selectedUser, 'disable'); closeUser()">禁用账号</button>
            <button v-if="selectedUser.status === 'disabled'" class="primary-btn" @click="openUserStatusDialog(selectedUser, 'enable'); closeUser()">恢复账号</button>
          </div>
        </div>
      </div>

      <div v-if="userStatusDialog.open" class="admin-modal-backdrop" @click.self="closeUserStatusDialog">
        <div class="admin-modal">
          <header class="admin-modal-head"><div><p class="admin-eyebrow">ACCOUNT STATUS</p><h2>{{ userStatusDialog.action === 'disable' ? '禁用账号' : '恢复账号' }}</h2></div><button class="icon-btn" @click="closeUserStatusDialog"><AppIcon name="close" /></button></header>
          <p class="admin-muted">{{ userStatusDialog.target?.name }}</p>
          <label class="admin-field">原因<textarea v-model="userStatusDialog.reason" rows="3"></textarea></label>
          <label v-if="userStatusDialog.action === 'disable'" class="admin-check"><input v-model="userStatusDialog.offline_listings" type="checkbox" /> 同时下架该用户的公开帖子</label>
          <div class="admin-modal-actions"><button class="ghost-btn" @click="closeUserStatusDialog">取消</button><button class="primary-btn" @click="submitUserStatus">确认{{ userStatusDialog.action === 'disable' ? '禁用' : '恢复' }}</button></div>
        </div>
      </div>

      <div v-if="categoryForm.open" class="admin-modal-backdrop" @click.self="closeCategory">
        <div class="admin-modal">
          <header class="admin-modal-head"><div><p class="admin-eyebrow">CATEGORY</p><h2>{{ categoryForm.id ? '编辑分类' : '新增分类' }}</h2></div><button class="icon-btn" @click="closeCategory"><AppIcon name="close" /></button></header>
          <label class="admin-field">分类名称<input v-model="categoryForm.name" placeholder="例如：学习资料" /></label>
          <label class="admin-field">适用类型<select v-model="categoryForm.listing_type"><option value="both">通用</option><option value="resource">资源</option><option value="skill">技能</option></select></label>
          <label class="admin-field">排序数字<input v-model.number="categoryForm.sort_order" type="number" /></label>
          <label class="admin-check"><input v-model="categoryForm.is_active" type="checkbox" /> 启用该分类</label>
          <div class="admin-modal-actions"><button class="ghost-btn" @click="closeCategory">取消</button><button class="primary-btn" @click="saveCategory">保存</button></div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.admin-workspace { padding-bottom: 48px; }
.admin-heading { align-items: flex-start; }
.admin-eyebrow { margin: 0 0 5px; color: #a66b35; font-family: "Inter", "Segoe UI", sans-serif; font-size: 8px; font-weight: 800; letter-spacing: .18em; }
.admin-heading h1 { margin: 0 0 7px; font-size: clamp(30px, 4vw, 46px); }
.admin-heading p:not(.admin-eyebrow) { max-width: 620px; margin: 0; color: var(--muted); font-size: 12px; line-height: 1.65; }
.admin-tabs { display: flex; flex-wrap: wrap; gap: 4px; margin: 22px 0 20px; padding: 5px; border: 1px solid var(--line); border-radius: 15px; background: #fffdf8; box-shadow: 0 10px 30px rgba(63, 110, 120, .06); }
.admin-tabs button { position: relative; display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 0 12px; border: 0; border-radius: 10px; background: transparent; color: var(--muted); font-size: 10px; font-weight: 800; }
.admin-tabs button:hover { background: #f7f1e4; color: var(--ink); }
.admin-tabs button.active { background: var(--ink, #2c4f5a); color: #fffdf8; }
.admin-tabs .app-icon { width: 14px; height: 14px; }
.admin-tab-badge { display: grid; place-items: center; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 999px; background: var(--coral, #e5745f); color: white; font-size: 8px; }
.admin-loading, .admin-empty { display: flex; align-items: center; justify-content: center; gap: 9px; min-height: 150px; padding: 25px; border: 1px dashed var(--line); border-radius: 13px; background: #fffdf8; color: var(--muted); font-size: 11px; }
.admin-loading span { width: 15px; height: 15px; border: 2px solid #e3d5bf; border-top-color: var(--ink); border-radius: 50%; animation: admin-spin .8s linear infinite; }
@keyframes admin-spin { to { transform: rotate(360deg); } }
.admin-panel { animation: admin-in .2s ease both; }
@keyframes admin-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.admin-section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 15px; margin-bottom: 14px; }
.admin-section-head h2 { margin: 0; color: var(--ink); font-size: 22px; }
.admin-section-head .text-btn { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
.admin-section-head .text-btn .app-icon { width: 13px; height: 13px; }
.admin-count { color: var(--muted); font-size: 10px; font-weight: 700; }
.admin-stat-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 28px; }
.admin-stat-card { display: flex; flex-direction: column; align-items: flex-start; min-height: 118px; padding: 14px; border: 1px solid var(--line); border-radius: 12px; background: #fffdf8; text-align: left; transition: transform .18s ease, box-shadow .18s ease; }
.admin-stat-card:hover { transform: translateY(-2px); box-shadow: 4px 5px 0 rgba(44, 79, 90, .13); }
.admin-stat-card span { color: var(--muted); font-size: 10px; font-weight: 700; }
.admin-stat-card b { margin: 5px 0 2px; color: var(--ink); font-family: "Inter", "Segoe UI", sans-serif; font-size: 29px; line-height: 1; }
.admin-stat-card small { color: #948b7d; font-size: 8.5px; }
.admin-stat-card.is-amber { border-top: 3px solid #d8ad54; }
.admin-stat-card.is-coral { border-top: 3px solid #df816d; }
.admin-stat-card.is-teal { border-top: 3px solid #5599a3; }
.admin-stat-card.is-gold { border-top: 3px solid #c08a2c; }
.admin-stat-card.is-blue { border-top: 3px solid #6e9eb5; }
.admin-stat-card.is-green { border-top: 3px solid #7ba981; }
.admin-stat-card.is-muted { border-top: 3px solid #a9a195; }
.admin-stat-card.is-peach { border-top: 3px solid #e4b486; }
.admin-log-list { border: 1px solid var(--line); border-radius: 12px; background: #fffdf8; overflow: hidden; }
.admin-log-row { display: flex; align-items: flex-start; gap: 10px; padding: 11px 14px; border-bottom: 1px solid #f0e8d9; }
.admin-log-row:last-child { border-bottom: 0; }
.admin-log-dot { width: 6px; height: 6px; margin-top: 6px; border-radius: 50%; background: var(--coral); flex: 0 0 auto; }
.admin-log-row div { flex: 1; min-width: 0; }
.admin-log-row b { font-size: 10px; }
.admin-log-row p { margin: 2px 0 0; color: var(--muted); font-size: 9.5px; }
.admin-log-row time { color: #9a9185; font-size: 8.5px; white-space: nowrap; }
.admin-segmented { display: flex; gap: 3px; margin-bottom: 14px; padding: 3px; border: 1px solid var(--line); border-radius: 9px; background: #f7f0e3; width: fit-content; }
.admin-segmented button { min-height: 29px; padding: 0 11px; border: 0; border-radius: 6px; background: transparent; color: var(--muted); font-size: 9.5px; font-weight: 800; }
.admin-segmented button.active { background: #fffdf8; color: var(--ink); box-shadow: 0 1px 4px rgba(44,79,90,.12); }
.admin-card-list { display: grid; gap: 9px; }
.admin-verification-card, .admin-report-card { padding: 14px; border: 1px solid var(--line); border-radius: 12px; background: #fffdf8; }
.admin-verification-main, .admin-report-top { display: flex; align-items: flex-start; gap: 11px; }
.admin-avatar { display: grid; place-items: center; width: 38px; height: 38px; flex: 0 0 auto; border-radius: 50%; background: #f2d9bf; color: #704c2d; font-size: 15px; font-weight: 900; }
.admin-avatar.large-avatar { width: 48px; height: 48px; font-size: 19px; }
.admin-verification-main > div:last-child, .admin-report-top > div:first-child { flex: 1; min-width: 0; }
.admin-card-title { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.admin-card-title h3 { margin: 0; color: var(--ink); font-size: 13px; }
.admin-verification-main p, .admin-report-top p { margin: 3px 0 0; color: var(--muted); font-size: 9.5px; }
.admin-muted { color: #918879 !important; }
.admin-note { margin-top: 7px !important; padding: 7px 9px; border-left: 2px solid #e2cda6; background: #fbf6ea; color: #756b5b !important; font-size: 9.5px !important; }
.admin-status { display: inline-flex; align-items: center; padding: 3px 7px; border-radius: 999px; font-size: 8px; font-weight: 800; white-space: nowrap; }
.status-pending { background: #f8e4b8; color: #8b641d; }
.status-approved, .status-published, .status-active, .status-resolved { background: #dcebdd; color: #3d7048; }
.status-rejected, .status-offline, .status-disabled, .status-deleted { background: #f3ded7; color: #9b5349; }
.status-reserved { background: #dfeaf0; color: #497387; }
.status-completed { background: #e9e4f1; color: #675283; }
.admin-verification-actions { display: flex; align-items: center; gap: 6px; margin-top: 11px; padding-top: 10px; border-top: 1px solid #f0e8d9; flex-wrap: wrap; }
.admin-verification-actions input { flex: 1; min-width: 160px; height: 32px; padding: 0 9px; border: 1px solid var(--line); border-radius: 7px; background: #fffdf8; font-size: 10px; }
.admin-report-card .admin-report-top { justify-content: space-between; gap: 12px; }
.admin-report-desc { margin: 9px 0 0; color: var(--muted); font-size: 10px; line-height: 1.6; }
.admin-toolbar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 13px; padding: 9px; border: 1px solid var(--line); border-radius: 10px; background: #fffdf8; }
.admin-toolbar input, .admin-toolbar select { height: 32px; padding: 0 8px; border: 1px solid var(--line); border-radius: 6px; background: #fffdf8; color: var(--ink); font-size: 9.5px; }
.admin-toolbar input { min-width: 170px; }
.admin-toolbar .primary-btn, .admin-toolbar .ghost-btn { min-height: 32px; padding-inline: 11px; }
.admin-table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; background: #fffdf8; }
.admin-table { width: 100%; border-collapse: collapse; min-width: 760px; }
.admin-table th { padding: 10px 11px; border-bottom: 1px solid var(--line); background: #fbf5e9; color: #8b8273; font-size: 8px; font-weight: 800; letter-spacing: .08em; text-align: left; white-space: nowrap; }
.admin-table td { padding: 10px 11px; border-bottom: 1px solid #f2eadc; color: #5e665f; font-size: 9.5px; vertical-align: middle; }
.admin-table tr:last-child td { border-bottom: 0; }
.admin-table td small { display: block; margin-top: 3px; color: #a29a8d; font-size: 8px; }
.admin-table td b { color: var(--ink); }
.admin-link { padding: 0; border: 0; background: none; color: var(--ink); font-size: 10px; font-weight: 800; text-align: left; }
.admin-link:hover { color: var(--coral); }
.admin-actions { display: flex; gap: 7px; flex-wrap: wrap; }
.admin-actions .text-btn { font-size: 9px; }
.admin-feature-tag { display: inline-flex; margin-left: 5px; padding: 3px 6px; border-radius: 4px; background: #fbf0d8; color: #936a1e; font-size: 8px; font-weight: 800; }
.admin-report-count { color: #b05f4f; font-size: 8.5px; font-weight: 800; }
.admin-credit { font-family: "Inter", "Segoe UI", sans-serif; font-size: 15px; }
.admin-pagination { display: flex; align-items: center; justify-content: flex-end; gap: 9px; margin-top: 12px; color: var(--muted); font-size: 9px; }
.admin-pagination .outline-btn { min-height: 29px; padding-inline: 9px; font-size: 9px; }
.admin-pagination button:disabled { opacity: .42; cursor: not-allowed; }
.admin-modal-backdrop { position: fixed; z-index: 80; inset: 0; display: grid; place-items: center; padding: 20px; background: rgba(30, 49, 54, .42); backdrop-filter: blur(4px); }
.admin-modal { width: min(520px, 100%); max-height: 88vh; overflow-y: auto; padding: 20px; border: 1px solid var(--line); border-radius: 16px; background: #fffdf8; box-shadow: 0 24px 70px rgba(35, 54, 58, .24); }
.admin-modal-wide { width: min(760px, 100%); }
.admin-modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 15px; }
.admin-modal-head h2 { margin: 0; color: var(--ink); font-size: 22px; }
.admin-modal-head .icon-btn { display: grid; place-items: center; width: 30px; height: 30px; flex: 0 0 auto; border: 1px solid var(--line); border-radius: 50%; background: #fffdf8; color: var(--ink); }
.admin-modal-head .icon-btn .app-icon { width: 15px; height: 15px; }
.admin-detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.admin-detail-grid > div { padding: 9px 10px; border: 1px solid #eee4d5; border-radius: 8px; background: #fcf8ef; }
.admin-detail-grid span, .admin-detail-block > span, .admin-transaction-context span { display: block; color: #968b7b; font-size: 8px; font-weight: 700; }
.admin-detail-grid b, .admin-transaction-context b { display: block; margin-top: 3px; color: var(--ink); font-size: 10px; }
.admin-detail-block { margin-top: 10px; }
.admin-detail-block p { margin: 4px 0 9px; color: #5f675f; font-size: 10px; line-height: 1.6; }
.admin-transaction-context { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 7px; margin-top: 10px; padding: 10px; border-radius: 9px; background: #f1f7f5; }
.admin-transaction-context b { font-size: 9px; }
.admin-messages { margin-top: 13px; }
.admin-messages > .admin-eyebrow { margin-bottom: 7px; }
.admin-message { display: grid; grid-template-columns: 70px minmax(0, 1fr) auto; gap: 8px; padding: 7px 0; border-bottom: 1px solid #f0e8d9; font-size: 9.5px; }
.admin-message b { color: var(--ink); }
.admin-message span { color: var(--muted); }
.admin-message time { color: #a49b8e; font-size: 8px; white-space: nowrap; }
.admin-resolve-box { margin-top: 15px; padding-top: 13px; border-top: 1px solid var(--line); }
.admin-resolve-box label, .admin-field { display: block; margin-bottom: 9px; color: #756b5b; font-size: 9px; font-weight: 700; }
.admin-resolve-box textarea, .admin-field textarea, .admin-field input, .admin-field select { display: block; width: 100%; margin-top: 5px; padding: 9px; border: 1px solid var(--line); border-radius: 7px; background: #fffdf8; color: var(--ink); font-size: 10px; }
.admin-field textarea { resize: vertical; }
.admin-inline-fields { display: grid; grid-template-columns: 1fr 1.4fr; gap: 9px; }
.admin-inline-fields input { display: block; width: 100%; margin-top: 5px; padding: 8px; border: 1px solid var(--line); border-radius: 7px; background: #fffdf8; font-size: 10px; }
.admin-inline-fields label { color: #756b5b; font-size: 9px; font-weight: 700; }
.admin-resolve-actions, .admin-modal-actions { display: flex; justify-content: flex-end; gap: 7px; flex-wrap: wrap; margin-top: 13px; }
.admin-resolved-box { margin-top: 14px; padding: 11px; border-left: 2px solid #7ba981; background: #f2f8ef; }
.admin-resolved-box b { font-size: 9px; }
.admin-resolved-box p { margin: 4px 0; color: #52634d; font-size: 10px; }
.admin-resolved-box small { color: #8c9986; font-size: 8px; }
.admin-listing-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--muted); font-size: 9px; }
.admin-listing-images { display: flex; gap: 7px; margin-top: 12px; overflow-x: auto; }
.admin-listing-images img { width: 150px; height: 105px; object-fit: cover; border-radius: 8px; border: 1px solid var(--line); }
.admin-listing-desc { margin: 13px 0; color: #5f675f; font-size: 10.5px; line-height: 1.7; white-space: pre-wrap; }
.admin-user-summary { display: flex; align-items: center; gap: 11px; padding: 11px; border: 1px solid var(--line); border-radius: 10px; background: #fcf8ef; }
.admin-user-summary > div:nth-child(2) { flex: 1; min-width: 0; }
.admin-user-summary p { margin: 2px 0; color: var(--ink); font-size: 10px; }
.admin-subsection { margin-top: 15px; }
.admin-subsection h3 { margin: 0 0 6px; color: var(--ink); font-size: 11px; }
.admin-mini-list { display: grid; gap: 4px; }
.admin-mini-list span { display: flex; justify-content: space-between; gap: 10px; padding: 6px 8px; border-radius: 6px; background: #fbf6ea; color: var(--muted); font-size: 9px; }
.admin-mini-list b { color: var(--ink); }
.admin-check { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 9.5px; }
.admin-check input { width: auto; margin: 0; }
.admin-actions .danger, .danger { color: #b45b4d; }
@media (max-width: 760px) {
  .admin-stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .admin-tabs { flex-wrap: nowrap; overflow-x: auto; }
  .admin-tabs button { flex: 0 0 auto; }
  .admin-detail-grid, .admin-transaction-context { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .admin-inline-fields { grid-template-columns: 1fr; }
  .admin-verification-actions { align-items: stretch; }
  .admin-verification-actions input { flex-basis: 100%; }
  .admin-modal { padding: 16px; }
  .admin-user-summary { align-items: flex-start; flex-wrap: wrap; }
  .admin-user-summary > .admin-status { margin-left: 59px; }
  .admin-message { grid-template-columns: 60px minmax(0, 1fr); }
  .admin-message time { grid-column: 2; }
}
@media (max-width: 430px) {
  .admin-stat-grid { gap: 7px; }
  .admin-stat-card { min-height: 100px; padding: 11px; }
  .admin-stat-card b { font-size: 25px; }
  .admin-toolbar input { min-width: 100%; }
  .admin-toolbar select { flex: 1; }
  .admin-section-head { align-items: flex-start; flex-direction: column; }
}
</style>
