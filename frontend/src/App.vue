<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import ExchangeHome from './components/ExchangeHome.vue'
import AppIcon from './components/AppIcon.vue'
import api from './api'
import {
  demoComments,
  demoMyListing,
  demoNotifications,
  demoProfiles,
  demoStories,
  demoTransactionMessages,
  demoTransactionSeed,
  seasonalThemes,
} from './demo-engagement'

const NOTIFICATION_READ_KEY = 'campus_notification_read_v1'
const VIEW_BOOST_KEY = 'campus_listing_view_boost_v1'
const VIEWED_SESSION_KEY = 'campus_listing_viewed_session_v1'
const LOCAL_COMMENTS_KEY = 'campus_listing_comments_v1'
const SAVED_FILTER_KEY = 'campus_saved_filter_v1'
const PROFILE_PRIVACY_KEY = 'campus_profile_privacy_v1'

function loadStoredJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function saveStoredJson(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* storage can be unavailable */ }
}

function loadNotificationReadIds() {
  const stored = loadStoredJson(NOTIFICATION_READ_KEY, null)
  if (Array.isArray(stored)) return stored
  return demoNotifications.filter((item) => item.readByDefault).map((item) => item.id)
}

function storedUser() {
  try { return JSON.parse(localStorage.getItem('campus_user') || 'null') } catch { return null }
}

const tab = ref('home')
const listingType = ref('all')
const mobileMenuOpen = ref(false)
const accountMenuOpen = ref(false)
const pendingNavigation = ref(null)
const pendingPublishType = ref(null)
const pendingListing = ref(null)
const marketplaceTitle = computed(() => ({ all: '校园互助广场', resource: '资源置换', skill: '技能互助' }[listingType.value]))
const marketplaceDescription = computed(() => ({ all: '教材、设备、技能和时间，在校园里找到彼此需要的那一份。', resource: '让用过的好东西，开启下一段校园生活。', skill: '分享你的拿手好戏，也找到需要的那份帮助。' }[listingType.value]))
const navigationItems = computed(() => [
  { key: 'home', label: '首页', type: 'all' },
  { key: 'discover', label: '互助广场', type: 'all' },
  ...(isAdmin.value
    ? [{ key: 'admin', label: '管理工作台', type: 'all' }]
    : [
        { key: 'my-listings', label: '我的发布', type: 'all' },
        { key: 'favorites', label: '我的收藏', type: 'all' },
        { key: 'transactions', label: '我的交易', type: 'all' },
      ]),
])
let listingsRequestId = 0
let previousDialogFocus = null
const authMode = ref('phone-login')
const showAuth = ref(false)
const showPublish = ref(false)
const notificationPanelOpen = ref(false)
const selectedNotification = ref(null)
const readNotificationIds = ref(loadNotificationReadIds())
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
const selectedProfile = ref(null)
const ownerBubble = ref(null)
const messages = ref([])
const newMessage = ref('')
const cancelReason = ref('')
const publishFiles = ref([])
const verificationFile = ref(null)
const verificationChallenge = ref(null)
const currentUser = ref(storedUser())
const demoTransaction = reactive({ ...demoTransactionSeed, initiator_id: null, initiator_name: '我' })
const storedProfilePrivacy = loadStoredJson(PROFILE_PRIVACY_KEY, {})
const profilePrivacy = ref({
  showCollege: storedProfilePrivacy?.showCollege !== false,
  showStats: storedProfilePrivacy?.showStats !== false,
  showPosts: storedProfilePrivacy?.showPosts !== false,
  showHonors: storedProfilePrivacy?.showHonors !== false,
})
const demoMyListingStatus = ref('published')
watch(currentUser, (user) => {
  demoTransaction.initiator_id = user?.id ?? null
  demoTransaction.initiator_name = user?.name || '我'
  if (!user || user.role === 'admin') {
    notificationPanelOpen.value = false
    selectedNotification.value = null
    selectedProfile.value = null
    ownerBubble.value = null
  }
}, { immediate: true })
watch(profilePrivacy, (value) => saveStoredJson(PROFILE_PRIVACY_KEY, value), { deep: true })
const smsDebugCode = ref('')
const smsCountdown = ref(0)
const emailDebugCode = ref('')
const emailCountdown = ref(0)
const sceneFilter = ref('all')
const activeSeason = ref('all')
const freeOnly = ref(false)
const sortMode = ref('latest')
const advancedFiltersOpen = ref(false)
const storedSavedFilter = loadStoredJson(SAVED_FILTER_KEY, null)
const savedFilter = ref(storedSavedFilter && typeof storedSavedFilter === 'object' && !Array.isArray(storedSavedFilter) ? storedSavedFilter : null)
const storedViewBoost = loadStoredJson(VIEW_BOOST_KEY, {})
const storedLocalComments = loadStoredJson(LOCAL_COMMENTS_KEY, {})
const viewBoost = ref(storedViewBoost && typeof storedViewBoost === 'object' && !Array.isArray(storedViewBoost) ? storedViewBoost : {})
const localComments = ref(storedLocalComments && typeof storedLocalComments === 'object' && !Array.isArray(storedLocalComments) ? storedLocalComments : {})
const commentDraft = ref('')
const commentAsThanks = ref(true)
const listingsLoaded = ref(false)
const listingsError = ref(false)
const hasRealContent = ref(false)
const transactionRole = ref('all')
const transactionStatus = ref('active')
let smsTimer = null
let emailTimer = null
const statTotal = ref(0)
const statResource = ref(0)
const statSkill = ref(0)
const statCredit = ref(0)
const statTweens = new Map()
let plazaObserver = null

const authForm = reactive({ identifier: '', phone: '', sms_code: '', password: '', name: '' })
const filters = reactive({
  keyword: '',
  category_id: '',
  min_price: '',
  max_price: '',
  condition: 'all',
  service_mode: 'all',
  campus: 'all',
  story_only: false,
})
const publishForm = reactive({ type: 'resource', category_id: '', title: '', description: '', price: 0, price_unit: '元', location: '', condition_level: '', service_mode: 'offline', available_time: '', expected_exchange: '' })
const requestForm = reactive({ proposed_price: 0, proposed_time: '', proposed_location: '', request_note: '' })
const reviewForm = reactive({ rating: 5, content: '' })
const reportForm = reactive({ reason: '', description: '' })
const verificationForm = reactive({ student_no: '', college: '', grade: '' })
const emailForm = reactive({ email: '', code: '' })
const reportResolution = reactive({})
const reviewNotes = reactive({})
const isFreeListing = (item) => Number(item?.price || 0) === 0
const listingCredit = (item) => item?.owner_credit_score == null ? '信用未公开' : `信用 ${item.owner_credit_score}`
const listingCreditLabel = (item) => {
  const profile = profileForListing(item)
  if (profile && !canShowProfileField(profile, 'showStats')) return '数据未公开'
  return listingCredit(item)
}
const listingPrice = (item) => isFreeListing(item) ? '免费' : `¥${item.price}`
const listingTime = (value) => value ? new Date(value).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) : '刚刚'
const listingViewCount = (item) => Number(item?.view_count || 0) + Number(viewBoost.value?.[item?.id] || 0)
const listingViewText = (item, fallback = '新发布') => {
  const count = listingViewCount(item)
  return count > 0 ? `${count.toLocaleString('zh-CN')} 浏览` : fallback
}
const hasListingStory = (item) => Boolean(demoStories[item?.id] || item?.has_story)

function listingCampus(item) {
  if (item?.campus_area) return item.campus_area
  const location = String(item?.location || '')
  if (location.includes('城西')) return '城西校区'
  if (location.includes('儋州')) return '儋州校区'
  if (item?.type === 'skill' && item?.service_mode === 'online') return '线上'
  return '海甸校区'
}

function markListingViewed(item) {
  const listingId = String(item?.id || '')
  if (!listingId) return
  if (currentUser.value?.id && item?.owner_id === currentUser.value.id) return
  let viewed = []
  try { viewed = JSON.parse(sessionStorage.getItem(VIEWED_SESSION_KEY) || '[]') } catch { viewed = [] }
  if (!Array.isArray(viewed)) viewed = []
  if (viewed.includes(listingId)) return
  viewed.push(listingId)
  try { sessionStorage.setItem(VIEWED_SESSION_KEY, JSON.stringify(viewed)) } catch { /* ignore */ }
  viewBoost.value = { ...viewBoost.value, [listingId]: Number(viewBoost.value?.[listingId] || 0) + 1 }
  saveStoredJson(VIEW_BOOST_KEY, viewBoost.value)
}

const posterPalette = ['plum', 'blue', 'mango', 'orange']
function posterTone(item) {
  const seed = String(item?.id || item?.title || '')
  let hash = 0
  for (let index = 0; index < seed.length; index += 1) hash = (hash * 31 + seed.charCodeAt(index)) >>> 0
  return `tone-${posterPalette[hash % posterPalette.length]}`
}

function posterGlyph(item) {
  const category = item?.category_name || ''
  if (category.includes('教材')) return '书'
  if (category.includes('数码')) return '声'
  if (category.includes('生活')) return '行'
  if (category.includes('辅导')) return '学'
  if (category.includes('设计')) return '影'
  return item?.type === 'skill' ? '技' : '物'
}

function prefersReducedMotion() {
  return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
}

function tweenStat(target, value) {
  const end = Math.max(0, Math.round(value))
  if (prefersReducedMotion()) {
    target.value = end
    return
  }
  const from = Number(target.value) || 0
  if (from === end) return
  const running = statTweens.get(target)
  if (running) window.cancelAnimationFrame(running)
  const startedAt = performance.now()
  const tick = (now) => {
    const progress = Math.min(1, (now - startedAt) / 620)
    const eased = 1 - Math.pow(1 - progress, 3)
    target.value = Math.round(from + (end - from) * eased)
    if (progress < 1) statTweens.set(target, window.requestAnimationFrame(tick))
    else statTweens.delete(target)
  }
  statTweens.set(target, window.requestAnimationFrame(tick))
}

function trackPlazaSpotlight(event) {
  if (event.pointerType === 'touch') return
  const surface = event.currentTarget
  const rect = surface.getBoundingClientRect()
  surface.style.setProperty('--spot-x', `${event.clientX - rect.left}px`)
  surface.style.setProperty('--spot-y', `${event.clientY - rect.top}px`)
}

function setupPlazaReveals() {
  plazaObserver?.disconnect()
  plazaObserver = null
  if (tab.value !== 'discover') return
  const targets = document.querySelectorAll('.plaza-page [data-reveal]')
  if (!targets.length) return
  if (prefersReducedMotion() || !('IntersectionObserver' in window)) {
    targets.forEach((element) => element.classList.add('is-in'))
    return
  }
  plazaObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return
      entry.target.classList.add('is-in')
      observer.unobserve(entry.target)
    })
  }, { threshold: 0.12, rootMargin: '0px 0px -36px 0px' })
  targets.forEach((element) => {
    if (!element.classList.contains('is-in')) plazaObserver.observe(element)
  })
}

const isLoggedIn = computed(() => Boolean(currentUser.value))
const isAdmin = computed(() => currentUser.value?.role === 'admin')
const isVerified = computed(() => currentUser.value?.verification_status === 'verified')
const readNotificationSet = computed(() => new Set(readNotificationIds.value))
const unreadNotifications = computed(() => demoNotifications.filter((item) => !readNotificationSet.value.has(item.id)))
const unreadNotificationCount = computed(() => unreadNotifications.value.length)
const hasUrgentNotification = computed(() => unreadNotifications.value.some((item) => item.urgent))
const selectedStory = computed(() => selectedListing.value ? demoStories[selectedListing.value.id] || null : null)
const selectedOwnerProfile = computed(() => selectedListing.value ? profileForListing(selectedListing.value) : null)
const selectedOwnerStats = computed(() => profileStats(selectedOwnerProfile.value))
const selectedComments = computed(() => {
  const listingId = selectedListing.value?.id
  if (!listingId) return []
  return [...(demoComments[listingId] || []), ...(localComments.value[listingId] || [])]
})
const demoListings = [
  { id: 'demo-book', demo: true, type: 'resource', category_name: '教材与学习资料', title: '英文诗集《Milk and Honey》', description: '书页完整，有少量阅读标记，可在紫荆操场附近自取。', price: 28, price_unit: '本', location: '海甸校区 · 图书馆北门', campus_area: '海甸校区', condition_level: '九成新', service_mode: 'offline', view_count: 1286, owner_id: 'demo-user-lin', owner_name: '林小满', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 104, image_urls: ['https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-headphones', demo: true, type: 'resource', category_name: '数码设备', title: '头戴式降噪耳机', description: '功能正常，耳罩已更换，附收纳袋，支持当面试听。', price: 96, price_unit: '件', location: '海甸校区 · 二食堂门口', campus_area: '海甸校区', condition_level: '八成新', service_mode: 'offline', view_count: 864, owner_id: 'demo-user-zhou', owner_name: '周予安', owner_college: '信息科学技术学院', owner_verified: true, owner_credit_score: 112, image_urls: ['https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-bicycle', demo: true, type: 'resource', category_name: '生活用品', title: '通勤自行车，可试骑', description: '刹车和车灯正常，毕业离校转让，仅限校内当面交易。', price: 180, price_unit: '辆', location: '海甸校区 · 东坡湖旁', campus_area: '海甸校区', condition_level: '有使用痕迹', service_mode: 'offline', view_count: 512, owner_id: 'demo-user-xu', owner_name: '许知行', owner_college: '国际商学院', owner_verified: true, owner_credit_score: 101, image_urls: ['https://images.unsplash.com/photo-1529422643029-d4585747aaf2?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-python', demo: true, type: 'skill', category_name: '技能辅导', title: 'Python 作业思路梳理', description: '讲解基础语法和调试思路，不代写作业，可线上或图书馆。', price: 25, price_unit: '小时', location: '海甸校区 · 图书馆三楼', campus_area: '海甸校区', service_mode: 'both', view_count: 733, owner_id: 'demo-user-zhou', owner_name: '周予安', owner_college: '信息科学技术学院', owner_verified: true, owner_credit_score: 112, image_urls: ['https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-english', demo: true, type: 'skill', category_name: '技能辅导', title: '英语口语搭子 · 四六级', description: '每周两次情景对话，互相纠音，首次可免费体验 30 分钟。', price: 0, price_unit: '次', location: '海甸校区 · 社科楼', campus_area: '海甸校区', service_mode: 'offline', view_count: 958, owner_id: 'demo-user-lin', owner_name: '林小满', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 104, image_urls: ['https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-photo', demo: true, type: 'skill', category_name: '设计与媒体', title: '社团活动摄影协助', description: '可拍活动纪实与合照，交付基础调色照片，时间需提前约定。', price: 80, price_unit: '场', location: '城西校区 · 教学楼大厅', campus_area: '城西校区', service_mode: 'offline', view_count: 421, owner_id: 'demo-user-chen', owner_name: '陈一禾', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 103, image_urls: ['https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-finals-notes', demo: true, type: 'resource', category_name: '教材与学习资料', title: '宏观经济学复习笔记（含题型整理）', description: '期末周整理的重点框架和计算题题型，附一份空白自测卷，图书馆自取。', price: 15, price_unit: '份', location: '海甸校区 · 图书馆二楼', campus_area: '海甸校区', condition_level: '九成新', service_mode: 'offline', view_count: 642, season: 'finals', owner_id: 'demo-user-lin', owner_name: '林小满', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 104, image_urls: ['https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-freshman-guide', demo: true, type: 'skill', category_name: '技能辅导', title: '新生校园半日向导', description: '带新生认教学楼、食堂、快递点和校医院，可顺路帮忙搬一次行李。', price: 0, price_unit: '次', location: '海甸校区 · 校门口', campus_area: '海甸校区', service_mode: 'offline', view_count: 388, season: 'freshman', owner_id: 'demo-user-xu', owner_name: '许知行', owner_college: '国际商学院', owner_verified: true, owner_credit_score: 101, image_urls: ['https://images.unsplash.com/photo-1523050854058-8df90110c9f1?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-graduation-box', demo: true, type: 'resource', category_name: '生活用品', title: '毕业季清仓：台灯和收纳盒', description: '台灯亮度正常，收纳盒有轻微使用痕迹，毕业前在宿舍楼下自取。', price: 30, price_unit: '套', location: '海甸校区 · 宿舍区', campus_area: '海甸校区', condition_level: '有使用痕迹', service_mode: 'offline', view_count: 517, season: 'graduation', owner_id: 'demo-user-chen', owner_name: '陈一禾', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 103, image_urls: ['https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=80'] },
]
const demoMode = computed(() => listingsLoaded.value && !hasRealContent.value)
const displayListings = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  const category = categories.value.find((item) => item.id === Number(filters.category_id))
  const items = demoMode.value
    ? demoListings.filter((item) => (!keyword || [item.title, item.description, item.location].some((value) => value?.toLowerCase().includes(keyword))) && (!category || item.category_name === category.name))
    : listings.value
  const minPrice = filters.min_price === '' ? null : Number(filters.min_price)
  const maxPrice = filters.max_price === '' ? null : Number(filters.max_price)
  const filtered = items.filter((item) => {
    if (listingType.value !== 'all' && item.type !== listingType.value) return false
    if (freeOnly.value && !isFreeListing(item)) return false
    const price = Number(item.price || 0)
    if (minPrice != null && Number.isFinite(minPrice) && price < minPrice) return false
    if (maxPrice != null && Number.isFinite(maxPrice) && price > maxPrice) return false
    if (filters.condition !== 'all' && item.type === 'resource') {
      if (!String(item.condition_level || '').includes(filters.condition)) return false
    }
    if (filters.service_mode !== 'all') {
      const mode = item.service_mode || (item.type === 'resource' ? 'offline' : 'both')
      const matches = filters.service_mode === 'both'
        ? mode === 'both'
        : filters.service_mode === 'online'
          ? ['online', 'both'].includes(mode)
          : ['offline', 'both'].includes(mode)
      if (!matches) return false
    }
    if (filters.campus !== 'all' && listingCampus(item) !== filters.campus) return false
    if (filters.story_only && !hasListingStory(item)) return false
    if (activeSeason.value !== 'all' && item.season !== activeSeason.value) return false
    return true
  })
  if (sortMode.value === 'credit') {
    return [...filtered].sort((a, b) => (b.owner_credit_score ?? -1) - (a.owner_credit_score ?? -1))
  }
  if (sortMode.value === 'views') {
    return [...filtered].sort((a, b) => listingViewCount(b) - listingViewCount(a))
  }
  return filtered
})
const CONDITION_LABELS = { '全新': '全新', '九成新': '九成新', '八成新': '八成新', '有使用痕迹': '有使用痕迹' }
const SERVICE_MODE_LABELS = { offline: '线下交付', online: '线上服务', both: '线上 / 线下' }
const CAMPUS_LABELS = { '海甸校区': '海甸校区', '城西校区': '城西校区', '儋州校区': '儋州校区', '线上': '线上' }
const advancedFilterCount = computed(() => {
  let count = 0
  if (filters.min_price !== '' || filters.max_price !== '') count += 1
  if (filters.condition !== 'all' && listingType.value !== 'skill') count += 1
  if (filters.service_mode !== 'all') count += 1
  if (filters.campus !== 'all') count += 1
  if (filters.story_only) count += 1
  return count
})
const activeFilterLabels = computed(() => {
  const labels = []
  if (filters.min_price !== '' || filters.max_price !== '') {
    const label = filters.min_price !== '' && filters.max_price !== ''
      ? `¥${filters.min_price} – ¥${filters.max_price}`
      : filters.min_price !== ''
        ? `≥ ¥${filters.min_price}`
        : `≤ ¥${filters.max_price}`
    labels.push({ key: 'price', label })
  }
  if (filters.condition !== 'all' && listingType.value !== 'skill') {
    labels.push({ key: 'condition', label: CONDITION_LABELS[filters.condition] || filters.condition })
  }
  if (filters.service_mode !== 'all') labels.push({ key: 'service_mode', label: SERVICE_MODE_LABELS[filters.service_mode] || filters.service_mode })
  if (filters.campus !== 'all') labels.push({ key: 'campus', label: CAMPUS_LABELS[filters.campus] || filters.campus })
  if (filters.story_only) labels.push({ key: 'story_only', label: '有互助故事' })
  return labels
})
const savedFilterSummary = computed(() => {
  const value = savedFilter.value
  if (!value || typeof value !== 'object') return ''
  const bits = []
  if (value.keyword) bits.push(`“${value.keyword}”`)
  if (value.min_price !== '' && value.min_price != null) bits.push(`最低 ¥${value.min_price}`)
  if (value.max_price !== '' && value.max_price != null) bits.push(`最高 ¥${value.max_price}`)
  if (value.condition && value.condition !== 'all') bits.push(CONDITION_LABELS[value.condition] || value.condition)
  if (value.service_mode && value.service_mode !== 'all') bits.push(SERVICE_MODE_LABELS[value.service_mode] || value.service_mode)
  if (value.campus && value.campus !== 'all') bits.push(CAMPUS_LABELS[value.campus] || value.campus)
  if (value.story_only) bits.push('有故事')
  return bits.length ? bits.join(' · ') : '全部互助'
})

function resetAdvancedFilters(closePanel = false) {
  Object.assign(filters, { min_price: '', max_price: '', condition: 'all', service_mode: 'all', campus: 'all', story_only: false })
  if (closePanel) advancedFiltersOpen.value = false
}

function clearAdvancedFilter(key) {
  if (key === 'price') Object.assign(filters, { min_price: '', max_price: '' })
  else if (key === 'condition') filters.condition = 'all'
  else if (key === 'service_mode') filters.service_mode = 'all'
  else if (key === 'campus') filters.campus = 'all'
  else if (key === 'story_only') filters.story_only = false
}

function applyAdvancedFilters() {
  const min = filters.min_price === '' ? null : Number(filters.min_price)
  const max = filters.max_price === '' ? null : Number(filters.max_price)
  if (min != null && max != null && min > max) {
    flash('最低价格不能高于最高价格', true)
    return
  }
  advancedFiltersOpen.value = false
  flash(advancedFilterCount.value ? `已应用 ${advancedFilterCount.value} 个筛选条件` : '已清空高级筛选')
}

function saveCurrentFilter() {
  savedFilter.value = {
    keyword: filters.keyword,
    category_id: filters.category_id,
    min_price: filters.min_price,
    max_price: filters.max_price,
    condition: filters.condition,
    service_mode: filters.service_mode,
    campus: filters.campus,
    story_only: filters.story_only,
  }
  saveStoredJson(SAVED_FILTER_KEY, savedFilter.value)
  flash('当前筛选条件已保存到本机')
}

async function applySavedFilter() {
  if (!savedFilter.value) return
  activeSeason.value = 'all'
  Object.assign(filters, {
    keyword: savedFilter.value.keyword || '',
    category_id: savedFilter.value.category_id || '',
    min_price: savedFilter.value.min_price ?? '',
    max_price: savedFilter.value.max_price ?? '',
    condition: savedFilter.value.condition || 'all',
    service_mode: savedFilter.value.service_mode || 'all',
    campus: savedFilter.value.campus || 'all',
    story_only: Boolean(savedFilter.value.story_only),
  })
  advancedFiltersOpen.value = false
  if (filters.keyword || filters.category_id) await loadListings()
  flash('已恢复保存的筛选条件')
}

function removeSavedFilter() {
  savedFilter.value = null
  try { localStorage.removeItem(SAVED_FILTER_KEY) } catch { /* ignore */ }
  flash('已删除常用筛选')
}

const resourceListings = computed(() => displayListings.value.filter((item) => item.type === 'resource'))
const skillListings = computed(() => displayListings.value.filter((item) => item.type === 'skill'))
const averageCredit = computed(() => {
  const scores = displayListings.value
    .filter((item) => canShowProfileField(profileForListing(item), 'showStats'))
    .filter((item) => item.owner_credit_score != null)
    .map((item) => Number(item.owner_credit_score))
    .filter(Number.isFinite)
  return scores.length ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length) : 0
})
const catalogCounts = computed(() => {
  const items = demoMode.value ? demoListings : listings.value
  return {
    all: items.length,
    resource: items.filter((item) => item.type === 'resource').length,
    skill: items.filter((item) => item.type === 'skill').length,
  }
})
const activeSeasonTheme = computed(() => seasonalThemes.find((theme) => theme.id === activeSeason.value) || null)

function seasonalCount(seasonId) {
  const items = demoMode.value ? demoListings : listings.value
  return items.filter((item) => item.season === seasonId).length
}

async function applySeason(theme) {
  activeSeason.value = theme.id
  if (listingType.value !== 'all') listingType.value = 'all'
  filters.keyword = ''
  filters.category_id = ''
  sceneFilter.value = 'all'
  freeOnly.value = false
  advancedFiltersOpen.value = false
  resetAdvancedFilters()
  await loadListings()
  flash(`已进入「${theme.title}」季节限定`)
  await nextTick()
  document.querySelector('.plaza-board')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function clearSeason() {
  activeSeason.value = 'all'
  flash('已退出季节限定，查看全部互助')
  await nextTick()
  document.querySelector('.plaza-console')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
watch(
  () => [displayListings.value.length, resourceListings.value.length, skillListings.value.length, averageCredit.value],
  ([total, resource, skill, credit]) => {
    tweenStat(statTotal, total)
    tweenStat(statResource, resource)
    tweenStat(statSkill, skill)
    tweenStat(statCredit, credit)
  },
  { immediate: true },
)
const favoriteIds = computed(() => new Set(favoriteListings.value.map((item) => item.id)))
const showDemoMyListings = computed(() => isLoggedIn.value && !isAdmin.value && myListings.value.length === 0)
const demoMyListingForMe = computed(() => ({
  ...demoMyListing,
  status: demoMyListingStatus.value,
  owner_id: currentUser.value?.id,
  owner_name: currentUser.value?.name || '我',
  owner_college: currentUser.value?.college || '',
  owner_verified: isVerified.value,
  owner_credit_score: currentUser.value?.credit_score ?? 100,
}))
const displayMyListings = computed(() => showDemoMyListings.value ? [demoMyListingForMe.value, ...myListings.value] : myListings.value)
const selectedProfileListings = computed(() => profileListingsFor(selectedProfile.value))
const selectedProfileStats = computed(() => profileStats(selectedProfile.value))
const showDemoTransaction = computed(() => isLoggedIn.value && !isAdmin.value && transactions.value.length === 0)
const displayTransactions = computed(() => showDemoTransaction.value ? [demoTransaction, ...transactions.value] : transactions.value)
const filteredTransactions = computed(() => displayTransactions.value.filter((item) => {
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
const marketplaceScenePresets = computed(() => listingType.value === 'skill'
  ? [{ id: 'all', label: '全部', keyword: '', category: '' }, { id: 'tutoring', label: '辅导', keyword: '辅导' }, { id: 'language', label: '口语', keyword: '口语' }, { id: 'design', label: '设计', keyword: '设计' }, { id: 'photo', label: '摄影', keyword: '摄影' }]
  : scenePresets)
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

function toggleNotifications() {
  if (!isLoggedIn.value || isAdmin.value) return
  notificationPanelOpen.value = !notificationPanelOpen.value
  accountMenuOpen.value = false
  mobileMenuOpen.value = false
}

function markNotificationRead(item) {
  if (!item?.id || readNotificationSet.value.has(item.id)) return
  readNotificationIds.value = [...readNotificationIds.value, item.id]
  saveStoredJson(NOTIFICATION_READ_KEY, readNotificationIds.value)
}

function openNotification(item) {
  if (!isLoggedIn.value || isAdmin.value) return
  notificationPanelOpen.value = false
  selectedNotification.value = item
}

async function confirmNotification() {
  const item = selectedNotification.value
  if (!item) return
  markNotificationRead(item)
  selectedNotification.value = null
  if (item.action?.tab) {
    const actionLabel = item.action.label || '相关页面'
    flash(`已查看通知，正在前往${actionLabel.replace(/^查看|^去|^返回/, '')}`)
    navigate(item.action.tab, item.action.type || 'all')
    if (item.action.listingId) {
      await nextTick()
      const target = item.action.tab === 'my-listings'
        ? (displayMyListings.value.find((listing) => listing.id === item.action.listingId) || (item.action.listingId === 'demo-my-notes' ? demoMyListingForMe.value : null))
        : demoListings.find((listing) => listing.id === item.action.listingId)
      if (target) {
        openListing(target)
        if (item.action.focus === 'comments') {
          await nextTick()
          document.querySelector('.detail-comments')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }
    }
  } else {
    flash('已查看这条通知')
  }
}

function markAllNotificationsRead() {
  if (!unreadNotificationCount.value) return
  readNotificationIds.value = [...new Set([...readNotificationIds.value, ...demoNotifications.map((item) => item.id)])]
  saveStoredJson(NOTIFICATION_READ_KEY, readNotificationIds.value)
  flash('所有通知已标为已读')
}

function addListingComment() {
  const content = commentDraft.value.trim()
  if (!selectedListing.value?.id) return
  if (content.length < 2) {
    flash('留言至少写 2 个字', true)
    return
  }
  const listingId = selectedListing.value.id
  const comment = {
    id: `local-${Date.now()}`,
    author: currentUser.value?.name || '校园访客',
    college: currentUser.value?.college || '未认证访客',
    content,
    time: '刚刚',
    thanks: commentAsThanks.value,
    local: true,
  }
  const next = [...(localComments.value[listingId] || []), comment].slice(-20)
  localComments.value = { ...localComments.value, [listingId]: next }
  saveStoredJson(LOCAL_COMMENTS_KEY, localComments.value)
  commentDraft.value = ''
  flash(commentAsThanks.value ? '感谢卡已留在帖子下' : '留言已留在帖子下')
}

function defaultProfilePrivacy() {
  return { showCollege: true, showStats: true, showPosts: true, showHonors: true }
}

function selfProfile() {
  if (!currentUser.value) return null
  const honors = []
  if (isVerified.value) honors.push('平台认证')
  if (Number(currentUser.value.credit_score) >= 105) honors.push('信用之星')
  if (!honors.length) honors.push('初来乍到')
  return {
    id: currentUser.value.id,
    name: currentUser.value.name,
    handle: '@me',
    college: currentUser.value.college || '',
    grade: currentUser.value.grade || '',
    verified: isVerified.value,
    credit: currentUser.value.credit_score,
    completed: transactions.value.filter((item) => item.status === 'completed').length,
    joined: '当前账号',
    bio: '这是我的校园互助主页，可以在账号与安全中调整公开范围。',
    honors,
    privacy: profilePrivacy.value,
    isSelf: true,
    isDemo: false,
  }
}

function profileForListing(item) {
  if (!item) return null
  if (currentUser.value && item.owner_id === currentUser.value.id) return selfProfile()
  const demoProfile = demoProfiles[item.owner_id]
  if (demoProfile) return demoProfile
  return {
    id: item.owner_id || `owner-${item.owner_name || 'campus'}`,
    name: item.owner_name || '校园用户',
    handle: '',
    college: item.owner_college || '',
    grade: '',
    verified: Boolean(item.owner_verified),
    credit: item.owner_credit_score ?? null,
    completed: null,
    joined: '',
    bio: '',
    honors: [],
    privacy: defaultProfilePrivacy(),
    isSelf: false,
    isDemo: Boolean(item.demo),
  }
}

function profileListingsFor(profile) {
  if (!profile) return []
  if (profile.isSelf) return displayMyListings.value
  if (profile.isDemo) return demoListings.filter((item) => item.owner_id === profile.id)
  return [...myListings.value, ...listings.value].filter((item) => item.owner_id === profile.id)
}

function profileStats(profile) {
  if (!profile) return { posts: 0, totalViews: 0, completed: 0 }
  const items = profileListingsFor(profile)
  return {
    posts: items.length,
    totalViews: items.reduce((sum, item) => sum + listingViewCount(item), 0),
    completed: profile.isSelf
      ? transactions.value.filter((item) => item.status === 'completed').length
      : Number(profile.completed || 0),
  }
}

function canShowProfileField(profile, field) {
  return profile?.privacy?.[field] !== false
}

function ownerInitial(item) {
  return (item?.owner_name || '校园用户').slice(0, 1)
}

function ownerVerified(item) {
  return Boolean(profileForListing(item)?.verified)
}

function openOwnerBubble(item, event) {
  const profile = profileForListing(item)
  if (!profile) return
  if (ownerBubble.value?.item?.id === item.id) {
    ownerBubble.value = null
    return
  }
  const rect = event.currentTarget.getBoundingClientRect()
  const bubbleWidth = 292
  const bubbleHeight = 260
  const left = Math.min(Math.max(12, rect.left), Math.max(12, window.innerWidth - bubbleWidth - 12))
  const below = rect.bottom + 10
  const top = below + bubbleHeight > window.innerHeight ? Math.max(12, rect.top - bubbleHeight - 10) : below
  ownerBubble.value = { profile, item, left, top }
}

function closeOwnerBubble() {
  ownerBubble.value = null
}

function openOwnerProfileFromBubble() {
  if (!ownerBubble.value) return
  selectedProfile.value = ownerBubble.value.profile
  ownerBubble.value = null
}

function openSelfProfile() {
  selectedProfile.value = selfProfile()
}

function openListingFromProfile(item) {
  selectedProfile.value = null
  openListing(item)
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
  const requestId = ++listingsRequestId
  loading.value = true
  try {
    const params = { keyword: filters.keyword || undefined, category_id: filters.category_id || undefined, type: listingType.value === 'all' ? undefined : listingType.value, page_size: 50 }
    const { data } = await api.get('/listings', { params })
    if (requestId !== listingsRequestId) return
    listings.value = data.items
    if (data.total > 0) hasRealContent.value = true
    listingsLoaded.value = true
    listingsError.value = false
  } catch (err) {
    if (requestId !== listingsRequestId) return
    listingsLoaded.value = true
    listingsError.value = true
    flash(errorMessage(err, '列表加载失败，请稍后重试'), true)
  } finally {
    if (requestId === listingsRequestId) loading.value = false
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
  activeSeason.value = 'all'
  freeOnly.value = scene.id === 'free'
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
    if (data.user.role !== 'admin') {
      await Promise.all([loadTransactions(), loadMyListings(), loadFavorites()])
      if (authMode.value !== 'register' && pendingNavigation.value) {
        const destination = pendingNavigation.value
        navigate(destination.tab, destination.type)
      }
      if (authMode.value !== 'register' && pendingListing.value) openListing(pendingListing.value)
      if (pendingPublishType.value) openPublish(pendingPublishType.value)
    }
    pendingNavigation.value = null
    pendingPublishType.value = null
    pendingListing.value = null
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
  selectedNotification.value = null
  selectedProfile.value = null
  ownerBubble.value = null
  notificationPanelOpen.value = false
  accountMenuOpen.value = false
  tab.value = 'home'
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
  mobileMenuOpen.value = false
  accountMenuOpen.value = false
  if (!isLoggedIn.value) {
    pendingPublishType.value = type
    showAuth.value = true
    return
  }
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
  commentDraft.value = ''
  commentAsThanks.value = true
  markListingViewed(listing)
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
  if (item.demo) {
    demoMyListingStatus.value = nextStatus
    flash(nextStatus === 'published' ? '演示发布已重新上架' : '演示发布已下架')
    return
  }
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
    pendingListing.value = selectedListing.value
    selectedListing.value = null
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

function demoTransactionAction(action) {
  if (action === 'agree') {
    demoTransaction.status = 'agreed'
    flash('演示交易：协议已确认')
  } else if (action === 'requester-complete') {
    demoTransaction.status = 'completed'
    flash('演示交易：已确认收到，交易完成')
  } else if (action === 'simulate-payment') {
    demoTransaction.demo_payment_status = 'simulated_paid'
    flash('演示付款已记录，不会发生真实扣款')
  }
}

async function simulatePayment(item) {
  if (item.demo) {
    demoTransactionAction('simulate-payment')
    return
  }
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
  if (item.demo) {
    messages.value = demoTransactionMessages.map((message) => ({
      ...message,
      sender_id: message.sender_id === 'me' ? currentUser.value?.id : message.sender_id,
      sender_name: message.sender_id === 'me' ? currentUser.value?.name || '我' : message.sender_name,
    }))
    return
  }
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
  if (selectedTransaction.value?.demo) {
    demoTransaction.status = 'cancelled'
    cancelReason.value = ''
    flash('演示交易已取消')
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
  if (selectedTransaction.value?.demo) {
    messages.value.push({
      id: `demo-local-${Date.now()}`,
      sender_id: currentUser.value?.id,
      sender_name: currentUser.value?.name || '我',
      content: newMessage.value.trim(),
    })
    newMessage.value = ''
    flash('演示消息已发送到本地会话')
    return
  }
  try {
    const { data } = await api.post('/transactions/' + selectedTransaction.value.id + '/messages', { content: newMessage.value })
    messages.value.push(data)
    newMessage.value = ''
  } catch (err) {
    flash(errorMessage(err, '消息发送失败'), true)
  }
}

async function submitReview() {
  if (selectedTransaction.value?.demo) {
    flash('演示评价已记录，不会上传服务器')
    reviewForm.content = ''
    return
  }
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

const availableTabs = new Set(['home', 'discover', 'transactions', 'my-listings', 'favorites', 'verification', 'admin', 'profile'])

function beginLogin() {
  pendingNavigation.value = null
  pendingPublishType.value = null
  pendingListing.value = null
  mobileMenuOpen.value = false
  accountMenuOpen.value = false
  showAuth.value = true
}

function navigate(nextTab, nextType = 'all') {
  if (!availableTabs.has(nextTab)) nextTab = 'home'
  mobileMenuOpen.value = false
  accountMenuOpen.value = false
  notificationPanelOpen.value = false
  ownerBubble.value = null
  if (!['home', 'discover'].includes(nextTab) && !isLoggedIn.value) {
    pendingNavigation.value = { tab: nextTab, type: nextType }
    showAuth.value = true
    if (window.location.hash && tab.value === 'home') window.history.replaceState(null, '', '#home')
    return
  }
  if (nextTab === 'admin' && !isAdmin.value) nextTab = 'home'
  if (isAdmin.value && ['transactions', 'my-listings', 'favorites', 'verification'].includes(nextTab)) nextTab = 'admin'
  const nextListingType = nextTab === 'discover' && ['resource', 'skill'].includes(nextType) ? nextType : 'all'
  const typeChanged = nextListingType !== listingType.value
  listingType.value = nextListingType
  if (typeChanged) {
    filters.category_id = ''
    filters.keyword = ''
    sceneFilter.value = 'all'
    activeSeason.value = 'all'
    freeOnly.value = false
    resetAdvancedFilters()
  }
  tab.value = nextTab
  if (nextTab === 'discover') loadListings()
  if (nextTab === 'transactions') loadTransactions()
  if (nextTab === 'my-listings') loadMyListings()
  if (nextTab === 'favorites') loadFavorites()
  if (nextTab === 'verification') refreshCurrentUser()
  if (nextTab === 'admin') loadAdmin()
}

function openMarketplace(type = 'all') { navigate('discover', type) }

function skipToContent() { document.getElementById('page-content')?.focus() }

function readLocation() {
  const [nextTab, query] = window.location.hash.slice(1).split('?')
  navigate(nextTab || 'home', new URLSearchParams(query).get('type') || 'all')
}

watch([tab, listingType], async () => {
  const hash = `#${tab.value}${tab.value === 'discover' && listingType.value !== 'all' ? '?type=' + listingType.value : ''}`
  if (window.location.hash !== hash) window.history.pushState(null, '', hash)
  const title = tab.value === 'discover' ? marketplaceTitle.value : ({ home: 'EXCHANGE', transactions: '我的交易', 'my-listings': '我的发布', favorites: '我的收藏', verification: '学生认证', admin: '管理工作台', profile: '账号与安全' }[tab.value])
  document.title = `${title} · 海大互助`
  await nextTick()
  window.scrollTo({ top: 0, behavior: 'instant' })
})

watch(
  [tab, listingType, listingsLoaded, () => displayListings.value.map((item) => item.id).join('|')],
  async () => {
    await nextTick()
    setupPlazaReveals()
  },
)

watch([showAuth, showPublish, selectedListing, selectedTransaction, selectedNotification, selectedProfile], async (values, previous) => {
  if (values.some(Boolean)) {
    if (!previous.some(Boolean)) previousDialogFocus = document.activeElement
    document.body.style.overflow = 'hidden'
    await nextTick()
    const dialogs = document.querySelectorAll('.modal-backdrop .modal')
    const dialog = dialogs[dialogs.length - 1]
    const target = dialog?.querySelector('input:not([type="file"]), select, textarea, button')
    target?.focus({ preventScroll: true })
  } else {
    document.body.style.overflow = ''
    if (previousDialogFocus?.isConnected) previousDialogFocus.focus({ preventScroll: true })
  }
})

function handleDocumentClick(event) {
  if (!event.target.closest('.account-menu-wrap')) accountMenuOpen.value = false
  if (!event.target.closest('.notification-wrap')) notificationPanelOpen.value = false
  if (!event.target.closest('.owner-chip') && !event.target.closest('.detail-owner-chip') && !event.target.closest('.owner-bubble')) ownerBubble.value = null
  if (!event.target.closest('.site-header')) mobileMenuOpen.value = false
}

function handleWindowScroll() {
  if (ownerBubble.value) ownerBubble.value = null
}

function handleKeydown(event) {
  if (event.key === 'Escape') {
    if (ownerBubble.value) { ownerBubble.value = null; return }
    if (selectedProfile.value) { selectedProfile.value = null; return }
    if (selectedNotification.value) { selectedNotification.value = null; return }
    showAuth.value = false
    showPublish.value = false
    selectedListing.value = null
    selectedTransaction.value = null
    notificationPanelOpen.value = false
    advancedFiltersOpen.value = false
    mobileMenuOpen.value = false
    accountMenuOpen.value = false
  }
  if (event.key !== 'Tab') return
  const dialogs = document.querySelectorAll('.modal-backdrop .modal')
  const dialog = dialogs[dialogs.length - 1]
  if (!dialog) return
  const focusable = [...dialog.querySelectorAll('button, input, select, textarea, a[href], [tabindex="0"]')].filter((element) => !element.disabled && element.getClientRects().length)
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}

onMounted(async () => {
  window.addEventListener('hashchange', readLocation)
  window.addEventListener('scroll', handleWindowScroll, { passive: true })
  window.addEventListener('resize', handleWindowScroll)
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleKeydown)
  await refreshCurrentUser()
  await Promise.all([loadCategories(), loadListings()])
  readLocation()
  document.title = `${tab.value === 'home' ? 'EXCHANGE' : document.title.split(' · ')[0]} · 海大互助`
})

onBeforeUnmount(() => {
  window.clearInterval(smsTimer)
  window.clearInterval(emailTimer)
  plazaObserver?.disconnect()
  plazaObserver = null
  statTweens.forEach((frame) => window.cancelAnimationFrame(frame))
  statTweens.clear()
  window.removeEventListener('hashchange', readLocation)
  window.removeEventListener('scroll', handleWindowScroll)
  window.removeEventListener('resize', handleWindowScroll)
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="app-shell" :class="{ 'is-home': tab === 'home', 'is-plaza': tab === 'discover' }">
    <a href="#page-content" class="skip-link" @click.prevent="skipToContent">跳到主要内容</a>
    <header class="site-header">
      <button class="brand" aria-label="海大互助首页" @click="navigate('home')">
        <span class="brand-mark"><AppIcon name="exchange" /></span>
        <span><b>海大互助</b><small>CAMPUS EXCHANGE</small></span>
      </button>
      <nav id="site-navigation" class="site-nav" :class="{ 'is-open': mobileMenuOpen }" aria-label="主导航">
        <button v-for="item in navigationItems" :key="item.key + item.type" :class="{ active: tab === item.key }" :aria-current="tab === item.key ? 'page' : undefined" @click="navigate(item.key, item.type)">{{ item.label }}</button>
      </nav>
      <div class="site-actions">
        <div v-if="isLoggedIn && !isAdmin" class="notification-wrap">
          <button class="notification-bell" :class="{ 'has-unread': unreadNotificationCount, 'has-urgent': hasUrgentNotification }" :aria-label="unreadNotificationCount ? `通知中心，${unreadNotificationCount} 条未读` : '通知中心'" :aria-expanded="notificationPanelOpen" aria-controls="notification-panel" @click="toggleNotifications">
            <AppIcon name="bell" />
            <span v-if="unreadNotificationCount" class="notification-dot" aria-hidden="true">{{ unreadNotificationCount > 9 ? '9+' : unreadNotificationCount }}</span>
          </button>
          <section v-if="notificationPanelOpen" id="notification-panel" class="notification-panel" role="dialog" aria-label="通知中心">
            <header class="notification-panel-head">
              <div><span class="notification-eyebrow">INBOX</span><h2>通知中心</h2></div>
              <button class="notification-read-all" :disabled="!unreadNotificationCount" @click="markAllNotificationsRead">全部已读</button>
            </header>
            <div class="notification-summary-line">
              <b>{{ unreadNotificationCount ? `${unreadNotificationCount} 条未读` : '没有未读通知' }}</b>
              <span v-if="hasUrgentNotification" class="notification-summary-urgent">含紧急消息</span>
              <span v-else>内含审核、交易与留言动态</span>
              <em>演示</em>
            </div>
            <div class="notification-list">
              <button v-for="item in demoNotifications" :key="item.id" class="notification-item" :class="{ 'is-unread': !readNotificationSet.has(item.id), 'is-urgent': item.urgent }" @click="openNotification(item)">
                <span class="notification-icon" :class="'is-' + item.type"><AppIcon :name="item.icon" /></span>
                <span class="notification-copy">
                  <span class="notification-line"><b>{{ item.title }}</b><em v-if="item.urgent" class="notification-urgent">紧急</em><time>{{ item.time }}</time></span>
                  <small>{{ item.summary }}</small>
                  <span class="notification-type">{{ item.typeLabel }}</span>
                </span>
                <i v-if="!readNotificationSet.has(item.id)" class="notification-unread-dot" aria-label="未读"></i>
              </button>
            </div>
            <footer class="notification-panel-foot"><AppIcon name="bell" /><span>内置演示通知，只保存在本机浏览器，不会发送短信或推送。</span></footer>
          </section>
        </div>
        <div v-if="isLoggedIn" class="account-menu-wrap">
          <button class="account-button" aria-label="打开账号菜单" :aria-expanded="accountMenuOpen" aria-controls="account-navigation" @click="accountMenuOpen = !accountMenuOpen; notificationPanelOpen = false; mobileMenuOpen = false">
            <span class="avatar">{{ currentUser.name.slice(0, 1) }}</span><b>{{ currentUser.name }}</b><AppIcon name="chevron" />
          </button>
          <nav v-if="accountMenuOpen" id="account-navigation" class="account-menu" aria-label="账号导航">
            <small>{{ currentUser.account_masked }}</small>
            <button v-if="!isAdmin" :class="{ active: tab === 'profile' }" @click="navigate('profile')"><AppIcon name="user" />账号与安全</button>
            <button v-if="!isAdmin" :class="{ active: tab === 'verification' }" @click="navigate('verification')"><AppIcon name="shield" />学生认证</button>
            <button v-if="isAdmin" @click="navigate('admin')"><AppIcon name="shield" />管理工作台</button>
            <button class="danger" @click="logout"><AppIcon name="logout" />退出登录</button>
          </nav>
        </div>
        <button v-else class="outline-btn" @click="beginLogin">登录 / 注册</button>
        <button v-if="!isAdmin" class="primary-btn publish-top" @click="openPublish(listingType === 'skill' ? 'skill' : 'resource')"><AppIcon name="plus" />发布互助</button>
        <button class="mobile-menu-toggle" :aria-label="mobileMenuOpen ? '关闭导航' : '打开导航'" :aria-expanded="mobileMenuOpen" aria-controls="site-navigation" @click="mobileMenuOpen = !mobileMenuOpen; accountMenuOpen = false"><AppIcon :name="mobileMenuOpen ? 'close' : 'menu'" /></button>
      </div>
    </header>

    <main id="page-content" class="workspace" tabindex="-1">
      <Transition name="page" mode="out-in">
        <ExchangeHome v-if="tab === 'home'" :is-admin="isAdmin" @browse="openMarketplace" @publish="openPublish('resource')" />
        <section v-else-if="tab === 'discover'" class="page discover-page plaza-page">
          <div class="plaza-hero" @pointermove="trackPlazaSpotlight">
            <span class="plaza-hero-mark" aria-hidden="true">换</span>
            <div class="plaza-hero-grid">
              <div class="plaza-hero-copy">
                <p class="plaza-kicker"><span class="plaza-live" aria-hidden="true"></span> HNU · CAMPUS SWAP MEET <span>2026</span></p>
                <h1 class="plaza-title"><span>{{ marketplaceTitle }}</span></h1>
                <p class="plaza-lede">{{ marketplaceDescription }}</p>
                <div class="plaza-hero-actions">
                  <button v-if="!isAdmin" class="plaza-btn plaza-btn--solid" @click="openPublish(listingType === 'skill' ? 'skill' : 'resource')"><AppIcon name="plus" />发布互助</button>
                  <button class="plaza-btn plaza-btn--ghost" @click="openMarketplace(listingType === 'skill' ? 'resource' : 'skill')">{{ listingType === 'skill' ? '看看资源' : '看看技能' }} <span aria-hidden="true">↗</span></button>
                </div>
                <dl class="plaza-stats">
                  <div><dt>当前展示</dt><dd>{{ statTotal }}</dd></div>
                  <div><dt>资源 / 技能</dt><dd>{{ statResource }}<i>/</i>{{ statSkill }}</dd></div>
                  <div><dt>平均信用</dt><dd><span v-if="statCredit > 0" class="plaza-star" aria-hidden="true">★</span>{{ statCredit > 0 ? statCredit : '—' }}</dd></div>
                </dl>
              </div>
              <div class="plaza-poster-zone" aria-hidden="true">
                <div class="plaza-hero-sun"></div>
                <div class="plaza-poster plaza-poster--back"><span>换</span><small>TRADE</small></div>
                <div class="plaza-poster plaza-poster--mid"><span>技</span><small>SKILL</small></div>
                <div class="plaza-poster plaza-poster--front"><span>物</span><small>GOODS</small><b>免费<br />互助</b></div>
                <div class="plaza-badge">
                  <svg viewBox="0 0 120 120" focusable="false">
                    <defs><path id="plaza-badge-path" d="M60,60 m-46,0 a46,46 0 1,1 92,0 a46,46 0 1,1 -92,0" /></defs>
                    <text><textPath href="#plaza-badge-path">HNU · SWAP MEET · 2026 · </textPath></text>
                  </svg>
                  <span class="plaza-badge-arrow"><AppIcon name="arrow" /></span>
                </div>
              </div>
            </div>
            <div class="plaza-marquee" aria-hidden="true">
              <div class="plaza-marquee-track">
                <div class="plaza-marquee-group">
                  <span>资源置换</span><i>✦</i><span>技能互助</span><i>✦</i><span>校内当面交易</span><i>✦</i><span>平台不托管资金</span><i>✦</i><span>让闲置重新流动</span><i>✦</i>
                </div>
                <div class="plaza-marquee-group">
                  <span>资源置换</span><i>✦</i><span>技能互助</span><i>✦</i><span>校内当面交易</span><i>✦</i><span>平台不托管资金</span><i>✦</i><span>让闲置重新流动</span><i>✦</i>
                </div>
              </div>
            </div>
          </div>

          <section class="seasonal-section" data-reveal aria-label="季节限定">
            <div class="seasonal-head">
              <div class="seasonal-title">
                <span class="seasonal-kicker">SEASONAL · CAMPUS MOMENTS</span>
                <h2>季节限定</h2>
                <p>在特定的校园时间里，找到刚好需要的那份帮助。</p>
              </div>
              <button v-if="activeSeasonTheme" class="seasonal-exit" @click="clearSeason">退出「{{ activeSeasonTheme.title }}」</button>
            </div>
            <div class="seasonal-grid">
              <button v-for="(theme, index) in seasonalThemes" :key="theme.id" class="seasonal-card" :class="['tone-' + theme.tone, { 'is-active': activeSeason === theme.id }]" @click="applySeason(theme)">
                <span class="seasonal-no" aria-hidden="true">0{{ index + 1 }}</span>
                <span class="seasonal-icon"><AppIcon :name="theme.icon" /></span>
                <b>{{ theme.title }}</b>
                <p>{{ theme.description }}</p>
                <footer><span>{{ theme.period }}</span><em>{{ seasonalCount(theme.id) }} 条示例</em></footer>
              </button>
            </div>
          </section>

          <div class="plaza-console">
            <div class="plaza-console-top">
              <nav class="plaza-tabs" aria-label="发布类型">
                <button :class="{ active: listingType === 'all' }" :aria-current="listingType === 'all' ? 'page' : undefined" @click="openMarketplace('all')">全部互助 <b v-if="demoMode">{{ catalogCounts.all }}</b></button>
                <button :class="{ active: listingType === 'resource' }" :aria-current="listingType === 'resource' ? 'page' : undefined" @click="openMarketplace('resource')">资源置换 <b v-if="demoMode">{{ catalogCounts.resource }}</b></button>
                <button :class="{ active: listingType === 'skill' }" :aria-current="listingType === 'skill' ? 'page' : undefined" @click="openMarketplace('skill')">技能互助 <b v-if="demoMode">{{ catalogCounts.skill }}</b></button>
              </nav>
              <button v-if="!isAdmin" class="plaza-publish" @click="openPublish(listingType === 'skill' ? 'skill' : 'resource')"><AppIcon name="plus" />发布一条</button>
            </div>
            <div class="plaza-search-row">
              <label class="plaza-search"><AppIcon name="search" /><input aria-label="搜索资源与技能" v-model="filters.keyword" placeholder="搜索教材、设备、辅导或技能" @keyup.enter="loadListings" /><kbd>ENTER</kbd></label>
              <label class="plaza-select"><span>分类</span><select v-model="filters.category_id" aria-label="分类" @change="loadListings"><option value="">全部分类</option><option v-for="item in categories.filter(item => listingType === 'all' || item.listing_type === 'both' || item.listing_type === listingType)" :key="item.id" :value="item.id">{{ item.name }}</option></select><AppIcon name="chevron" /></label>
              <label class="plaza-select"><span>排序</span><select v-model="sortMode" aria-label="排序方式"><option value="latest">最新发布</option><option value="credit">信用优先</option><option value="views">浏览最多</option></select><AppIcon name="chevron" /></label>
              <button class="plaza-search-btn" @click="loadListings">搜索 <span aria-hidden="true">→</span></button>
            </div>
            <div class="plaza-chips">
              <span class="plaza-chips-label">场景</span>
              <button v-for="scene in marketplaceScenePresets" :key="scene.id" class="plaza-chip" :class="{ 'is-active': sceneFilter === scene.id }" @click="applyScene(scene)">{{ scene.label }}</button>
              <button class="plaza-chip plaza-free" :class="{ 'is-active': sceneFilter === 'free' }" @click="applyScene({ id: 'free', keyword: '', category: '' })"><span aria-hidden="true">✦</span> 免费互助</button>
              <button class="plaza-more-filters" :class="{ 'is-active': advancedFiltersOpen || advancedFilterCount }" :aria-expanded="advancedFiltersOpen" aria-controls="plaza-advanced-filters" @click="advancedFiltersOpen = !advancedFiltersOpen">
                <AppIcon name="filter" /> 更多筛选 <b v-if="advancedFilterCount">{{ advancedFilterCount }}</b><AppIcon name="chevron" />
              </button>
            </div>
            <Transition name="filter-panel">
              <section v-if="advancedFiltersOpen" id="plaza-advanced-filters" class="plaza-advanced">
                <header class="plaza-advanced-head">
                  <div><b>把范围再收窄一点</b><span>价格、成色、交付方式和校区可以组合使用</span></div>
                  <button class="plaza-advanced-reset" @click="resetAdvancedFilters">重置</button>
                </header>
                <div class="plaza-advanced-grid">
                  <fieldset class="plaza-price-filter">
                    <legend>价格区间</legend>
                    <div><input v-model="filters.min_price" type="number" min="0" step="1" inputmode="numeric" aria-label="最低价格" placeholder="最低" /><span>—</span><input v-model="filters.max_price" type="number" min="0" step="1" inputmode="numeric" aria-label="最高价格" placeholder="最高" /></div>
                  </fieldset>
                  <label v-if="listingType !== 'skill'" class="plaza-advanced-field">资源成色<select v-model="filters.condition"><option value="all">不限</option><option v-for="(label, value) in CONDITION_LABELS" :key="value" :value="value">{{ label }}</option></select></label>
                  <label class="plaza-advanced-field">交付方式<select v-model="filters.service_mode"><option value="all">不限</option><option value="offline">线下</option><option value="online">线上</option><option value="both">线上 / 线下</option></select></label>
                  <label class="plaza-advanced-field">校区 / 地点<select v-model="filters.campus"><option value="all">不限</option><option value="海甸校区">海甸校区</option><option value="城西校区">城西校区</option><option value="儋州校区">儋州校区</option><option value="线上">线上</option></select></label>
                </div>
                <div class="plaza-advanced-foot">
                  <label class="plaza-story-toggle"><input v-model="filters.story_only" type="checkbox" /><span>只看有互助故事的帖子</span></label>
                  <div class="plaza-advanced-actions">
                    <button class="plaza-save-filter" @click="saveCurrentFilter">{{ savedFilter ? '更新常用条件' : '存为常用条件' }}</button>
                    <button class="plaza-apply-filter" @click="applyAdvancedFilters">应用筛选 <span aria-hidden="true">→</span></button>
                  </div>
                </div>
                <div v-if="savedFilter" class="plaza-saved-filter">
                  <span>上次保存：{{ savedFilterSummary }}</span>
                  <button @click="applySavedFilter">恢复</button>
                  <button @click="removeSavedFilter">删除</button>
                </div>
              </section>
            </Transition>
            <div v-if="advancedFilterCount" class="plaza-active-filters">
              <span>已选</span>
              <button v-for="item in activeFilterLabels" :key="item.key" @click="clearAdvancedFilter(item.key)">{{ item.label }} <i aria-hidden="true">×</i></button>
              <button class="plaza-clear-filters" @click="resetAdvancedFilters">清除全部</button>
            </div>
          </div>

          <div v-if="activeSeasonTheme" class="plaza-season-note">
            <span><AppIcon :name="activeSeasonTheme.icon" /> 正在查看「{{ activeSeasonTheme.title }}」</span>
            <b>{{ seasonalCount(activeSeasonTheme.id) }} 条示例</b>
            <button @click="clearSeason">返回全部互助</button>
          </div>
          <div v-if="demoMode" class="plaza-demo">
            <span class="plaza-demo-tag">设计示例</span>
            <p>当前内容用于预览界面，不对应真实帖子，不能收藏或发起交易。<template v-if="listingsError"> 服务暂时未连接，请重试。</template></p>
            <button v-if="listingsError" @click="loadListings">重试连接</button>
          </div>
          <div v-if="loading" class="plaza-state" role="status">正在整理广场信息...</div>
          <div v-else-if="listingsError && !demoMode" class="plaza-state is-error"><strong>广场信息加载失败</strong><button class="plaza-chip" @click="loadListings">重试</button></div>
          <div v-else class="plaza-board" :class="{ 'is-single': listingType !== 'all' }">
            <section v-if="listingType !== 'skill'" class="plaza-lane plaza-lane--resource">
              <header class="plaza-lane-head" data-reveal>
                <span class="plaza-lane-no" aria-hidden="true">01</span>
                <div class="plaza-lane-title"><h2>资源流转 <small>RESOURCE</small></h2><p>把闲置交给下一位需要的人</p></div>
                <span class="plaza-lane-count">{{ resourceListings.length.toString().padStart(2, '0') }}</span>
                <button v-if="!isAdmin" class="plaza-lane-add" aria-label="发布资源" @click="openPublish('resource')"><AppIcon name="plus" /></button>
              </header>
              <div v-if="!resourceListings.length" class="plaza-empty" data-reveal>
                <b>暂无匹配资源</b><span>教材、数码设备和生活用品会显示在这里。</span>
                <button v-if="!isAdmin" class="text-btn" @click="openPublish('resource')">发布第一条资源</button>
              </div>
              <template v-for="(item, index) in resourceListings" :key="item.id">
                <article v-if="index === 0" class="swap-card swap-card--feature" data-reveal :style="{ '--rv-delay': (index > 6 ? 6 : index) * 60 + 'ms' }">
                  <div class="swap-media">
                    <div class="swap-poster" :class="posterTone(item)" aria-hidden="true">
                      <span class="swap-poster-glyph">{{ posterGlyph(item) }}</span>
                      <span class="swap-poster-label">{{ item.category_name || typeLabel(item.type) }}</span>
                    </div>
                    <img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" @error="$event.target.remove()" />
                    <span v-if="item.demo" class="swap-flag">设计示例</span>
                    <button v-if="isLoggedIn && !isAdmin && !item.demo" class="swap-fav" :class="{ 'is-saved': favoriteIds.has(item.id) }" :aria-label="favoriteIds.has(item.id) ? '取消收藏' : '收藏'" @click="toggleFavorite(item)">{{ favoriteIds.has(item.id) ? '★' : '☆' }}</button>
                    <span class="swap-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}<small v-if="item.price">/ {{ item.price_unit }}</small></span>
                  </div>
                  <div class="swap-content">
                    <p class="swap-kicker"><span>{{ item.category_name || typeLabel(item.type) }}</span><span v-if="isFreeListing(item)" class="swap-free">免费互助</span><span v-if="hasListingStory(item)" class="swap-story-flag">有故事</span><time v-if="!item.demo">{{ listingTime(item.created_at) }}</time></p>
                    <h3>{{ item.title }}</h3>
                    <p class="swap-desc">{{ item.description }}</p>
                    <div class="swap-foot">
                      <span class="swap-owner">
                        <span class="swap-location">{{ item.location || '校内协商' }}</span>
                        <button class="owner-chip" :aria-label="`查看${item.owner_name || '发布者'}的主页`" @click.stop="openOwnerBubble(item, $event)">
                          <span class="owner-avatar">{{ ownerInitial(item) }}</span><span>{{ item.owner_name || '校园用户' }}</span><span v-if="ownerVerified(item)" class="owner-verified" aria-label="平台认证">✓</span>
                        </button>
                      </span>
                      <span class="swap-views"><AppIcon name="eye" />{{ listingViewText(item) }}</span>
                      <span class="swap-credit"><b>★</b>{{ listingCreditLabel(item) }}</span>
                      <button class="swap-open" @click="openListing(item)">查看详情 <AppIcon name="arrow" /></button>
                    </div>
                  </div>
                </article>
                <article v-else class="swap-card swap-card--row" data-reveal :style="{ '--rv-delay': (index > 6 ? 6 : index) * 60 + 'ms' }">
                  <div class="swap-thumb">
                    <div class="swap-poster" :class="posterTone(item)" aria-hidden="true">
                      <span class="swap-poster-glyph">{{ posterGlyph(item) }}</span>
                      <span class="swap-poster-label">{{ item.category_name }}</span>
                    </div>
                    <img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" @error="$event.target.remove()" />
                  </div>
                  <div class="swap-row-body">
                    <p class="swap-kicker"><span>{{ item.category_name || typeLabel(item.type) }}</span><span v-if="isFreeListing(item)" class="swap-free">免费</span><span v-if="item.demo" class="swap-free">示例</span><span v-if="hasListingStory(item)" class="swap-story-flag">故事</span><time v-if="!item.demo">{{ listingTime(item.created_at) }}</time></p>
                    <h3>{{ item.title }}</h3>
                    <p class="swap-desc">{{ item.description }}</p>
                    <div class="swap-foot">
                      <span class="swap-owner">
                        <span class="swap-location">{{ item.location || '校内协商' }}</span>
                        <button class="owner-chip" :aria-label="`查看${item.owner_name || '发布者'}的主页`" @click.stop="openOwnerBubble(item, $event)">
                          <span class="owner-avatar">{{ ownerInitial(item) }}</span><span>{{ item.owner_name || '校园用户' }}</span><span v-if="ownerVerified(item)" class="owner-verified" aria-label="平台认证">✓</span>
                        </button>
                      </span>
                      <span class="swap-views"><AppIcon name="eye" />{{ listingViewText(item) }}</span>
                      <span class="swap-credit"><b>★</b>{{ listingCreditLabel(item) }}</span>
                    </div>
                  </div>
                  <div class="swap-aside">
                    <strong class="swap-row-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}</strong>
                    <small>{{ isFreeListing(item) ? '无需付费' : '/ ' + item.price_unit }}</small>
                    <button v-if="isLoggedIn && !isAdmin && !item.demo" class="swap-fav" :class="{ 'is-saved': favoriteIds.has(item.id) }" :aria-label="favoriteIds.has(item.id) ? '取消收藏' : '收藏'" @click="toggleFavorite(item)">{{ favoriteIds.has(item.id) ? '★' : '☆' }}</button>
                    <button class="swap-open" aria-label="查看详情" @click="openListing(item)"><AppIcon name="arrow" /></button>
                  </div>
                </article>
              </template>
            </section>

            <section v-if="listingType !== 'resource'" class="plaza-lane plaza-lane--skill">
              <header class="plaza-lane-head" data-reveal>
                <span class="plaza-lane-no" aria-hidden="true">02</span>
                <div class="plaza-lane-title"><h2>技能互助 <small>SKILL</small></h2><p>把擅长的事变成一次帮助</p></div>
                <span class="plaza-lane-count">{{ skillListings.length.toString().padStart(2, '0') }}</span>
                <button v-if="!isAdmin" class="plaza-lane-add" aria-label="发布技能" @click="openPublish('skill')"><AppIcon name="plus" /></button>
              </header>
              <div v-if="!skillListings.length" class="plaza-empty" data-reveal>
                <b>暂无匹配技能</b><span>学习辅导、设计协助和技术支持会显示在这里。</span>
                <button v-if="!isAdmin" class="text-btn" @click="openPublish('skill')">发布第一条技能</button>
              </div>
              <template v-for="(item, index) in skillListings" :key="item.id">
                <article v-if="index === 0" class="swap-card swap-card--feature" data-reveal :style="{ '--rv-delay': (index > 6 ? 6 : index) * 60 + 'ms' }">
                  <div class="swap-media">
                    <div class="swap-poster" :class="posterTone(item)" aria-hidden="true">
                      <span class="swap-poster-glyph">{{ posterGlyph(item) }}</span>
                      <span class="swap-poster-label">{{ item.category_name || typeLabel(item.type) }}</span>
                    </div>
                    <img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" @error="$event.target.remove()" />
                    <span v-if="item.demo" class="swap-flag">设计示例</span>
                    <button v-if="isLoggedIn && !isAdmin && !item.demo" class="swap-fav" :class="{ 'is-saved': favoriteIds.has(item.id) }" :aria-label="favoriteIds.has(item.id) ? '取消收藏' : '收藏'" @click="toggleFavorite(item)">{{ favoriteIds.has(item.id) ? '★' : '☆' }}</button>
                    <span class="swap-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}<small v-if="item.price">/ {{ item.price_unit }}</small></span>
                  </div>
                  <div class="swap-content">
                    <p class="swap-kicker"><span>{{ item.category_name || typeLabel(item.type) }}</span><span v-if="isFreeListing(item)" class="swap-free">免费互助</span><span v-if="hasListingStory(item)" class="swap-story-flag">有故事</span><time v-if="!item.demo">{{ listingTime(item.created_at) }}</time></p>
                    <h3>{{ item.title }}</h3>
                    <p class="swap-desc">{{ item.description }}</p>
                    <div class="swap-foot">
                      <span class="swap-owner">
                        <span class="swap-location">{{ item.service_mode === 'online' ? '线上' : item.service_mode === 'both' ? '线上 / 线下' : (item.location || '校内协商') }}</span>
                        <button class="owner-chip" :aria-label="`查看${item.owner_name || '发布者'}的主页`" @click.stop="openOwnerBubble(item, $event)">
                          <span class="owner-avatar">{{ ownerInitial(item) }}</span><span>{{ item.owner_name || '校园用户' }}</span><span v-if="ownerVerified(item)" class="owner-verified" aria-label="平台认证">✓</span>
                        </button>
                      </span>
                      <span class="swap-views"><AppIcon name="eye" />{{ listingViewText(item) }}</span>
                      <span class="swap-credit"><b>★</b>{{ listingCreditLabel(item) }}</span>
                      <button class="swap-open" @click="openListing(item)">查看详情 <AppIcon name="arrow" /></button>
                    </div>
                  </div>
                </article>
                <article v-else class="swap-card swap-card--row" data-reveal :style="{ '--rv-delay': (index > 6 ? 6 : index) * 60 + 'ms' }">
                  <div class="swap-thumb">
                    <div class="swap-poster" :class="posterTone(item)" aria-hidden="true">
                      <span class="swap-poster-glyph">{{ posterGlyph(item) }}</span>
                      <span class="swap-poster-label">{{ item.category_name }}</span>
                    </div>
                    <img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" @error="$event.target.remove()" />
                  </div>
                  <div class="swap-row-body">
                    <p class="swap-kicker"><span>{{ item.category_name || typeLabel(item.type) }}</span><span v-if="isFreeListing(item)" class="swap-free">免费</span><span v-if="item.demo" class="swap-free">示例</span><span v-if="hasListingStory(item)" class="swap-story-flag">故事</span><time v-if="!item.demo">{{ listingTime(item.created_at) }}</time></p>
                    <h3>{{ item.title }}</h3>
                    <p class="swap-desc">{{ item.description }}</p>
                    <div class="swap-foot">
                      <span class="swap-owner">
                        <span class="swap-location">{{ item.service_mode === 'online' ? '线上' : item.service_mode === 'both' ? '线上 / 线下' : (item.location || '校内协商') }}</span>
                        <button class="owner-chip" :aria-label="`查看${item.owner_name || '发布者'}的主页`" @click.stop="openOwnerBubble(item, $event)">
                          <span class="owner-avatar">{{ ownerInitial(item) }}</span><span>{{ item.owner_name || '校园用户' }}</span><span v-if="ownerVerified(item)" class="owner-verified" aria-label="平台认证">✓</span>
                        </button>
                      </span>
                      <span class="swap-views"><AppIcon name="eye" />{{ listingViewText(item) }}</span>
                      <span class="swap-credit"><b>★</b>{{ listingCreditLabel(item) }}</span>
                    </div>
                  </div>
                  <div class="swap-aside">
                    <strong class="swap-row-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}</strong>
                    <small>{{ isFreeListing(item) ? '无需付费' : '/ ' + item.price_unit }}</small>
                    <button v-if="isLoggedIn && !isAdmin && !item.demo" class="swap-fav" :class="{ 'is-saved': favoriteIds.has(item.id) }" :aria-label="favoriteIds.has(item.id) ? '取消收藏' : '收藏'" @click="toggleFavorite(item)">{{ favoriteIds.has(item.id) ? '★' : '☆' }}</button>
                    <button class="swap-open" aria-label="查看详情" @click="openListing(item)"><AppIcon name="arrow" /></button>
                  </div>
                </article>
              </template>
            </section>
          </div>
        </section>


        <section v-else-if="tab === 'transactions'" class="page narrow-page">
          <header class="page-heading"><div><h1>我的交易</h1><p>协议、消息与双方完成确认集中处理。</p></div><button class="outline-btn" @click="loadTransactions">刷新</button></header>
          <div v-if="!isLoggedIn" class="state-panel"><strong>登录后查看你的交易</strong><button class="primary-btn" @click="showAuth = true">登录</button></div>
          <template v-else>
            <div class="workspace-filter">
              <div class="segmented compact-segmented"><button :class="{ selected: transactionRole === 'all' }" @click="transactionRole = 'all'">全部角色</button><button :class="{ selected: transactionRole === 'initiated' }" @click="transactionRole = 'initiated'">我发起的</button><button :class="{ selected: transactionRole === 'received' }" @click="transactionRole = 'received'">我收到的</button></div>
              <select v-model="transactionStatus" aria-label="交易状态筛选"><option value="active">进行中</option><option value="completed">已完成</option><option value="closed">已关闭</option><option value="all">全部状态</option></select>
            </div>
          </template>
          <div v-if="showDemoTransaction" class="inline-demo-note"><span class="demo-badge">通知关联示例</span><p>下面这笔交易对应通知中心的“紧急交易”：确认协议后，状态会同步变化，方便演示完整的交易确认界面。</p></div>
          <div v-if="isLoggedIn && !displayTransactions.length" class="state-panel"><strong>还没有交易记录</strong><span>从双轨广场发起一笔资源或技能交易。</span></div>
          <div v-else-if="isLoggedIn && !filteredTransactions.length" class="state-panel"><strong>没有符合当前条件的交易</strong><span>尝试切换角色或状态筛选。</span></div>
          <div v-else-if="isLoggedIn" class="transaction-list">
            <article v-for="item in filteredTransactions" :key="item.id" class="transaction-card" :class="{ 'is-demo-row': item.demo }">
              <div class="transaction-head"><div><span class="record-id">TRANSACTION / {{ item.id }} <span v-if="item.demo" class="demo-label">演示</span></span><h2>{{ item.listing_title }}</h2></div><span class="status-pill">{{ statusLabel(item.status) }}</span></div>
              <div class="agreement-row"><span>¥ {{ item.agreed_price || item.proposed_price }}</span><span>{{ item.proposed_time || '时间待协商' }}</span><span>{{ item.proposed_location || '地点待协商' }}</span></div>
              <p>{{ item.request_note }}</p>
              <p v-if="item.demo" class="transaction-counterparty">对方：{{ item.provider_name }} · 这条交易对应通知中心的“紧急交易”</p>
              <p v-if="item.demo_payment_status === 'simulated_paid'" class="demo-payment-line">课程演示付款已记录，不代表真实资金支付</p>
              <div class="transaction-actions">
                <button class="outline-btn" @click="openTransaction(item)">消息与协议</button>
                <button v-if="item.status === 'pending_provider' && item.provider_id === currentUser.id" class="ghost-btn danger" @click="transactionAction(item.id, 'reject')">拒绝</button>
                <button v-if="item.status === 'pending_provider' && item.provider_id === currentUser.id" class="primary-btn" @click="transactionAction(item.id, 'accept')">接受请求</button>
                <button v-if="item.status === 'pending_initiator' && item.initiator_id === currentUser.id" class="primary-btn" @click="item.demo ? demoTransactionAction('agree') : transactionAction(item.id, 'agree')">确认协议</button>
                <button v-if="currentUser.demo_features_enabled && item.initiator_id === currentUser.id && ['agreed','provider_confirmed','requester_confirmed'].includes(item.status) && item.demo_payment_status !== 'simulated_paid' && Number(item.agreed_price || item.proposed_price) > 0" class="outline-btn demo-action" @click="simulatePayment(item)">模拟付款</button>
                <button v-if="['agreed','in_progress','requester_confirmed'].includes(item.status) && item.provider_id === currentUser.id && !item.provider_completed_at" class="primary-btn" @click="transactionAction(item.id, 'provider-complete')">确认已交付</button>
                <button v-if="['agreed','provider_confirmed'].includes(item.status) && item.initiator_id === currentUser.id && !item.requester_completed_at" class="primary-btn" @click="item.demo ? demoTransactionAction('requester-complete') : transactionAction(item.id, 'requester-complete')">确认已收到</button>
              </div>
            </article>
          </div>
          <p class="boundary-note">线下付款由双方自行完成。平台不托管资金，也不验证微信或其他线下付款的真伪。</p>
        </section>

        <section v-else-if="tab === 'my-listings'" class="page narrow-page">
          <header class="page-heading"><div><h1>我的发布</h1><p>分别管理资源和技能，上下架不会改变已经达成的交易。</p></div><button class="primary-btn" @click="openPublish('resource')">＋ 新发布</button></header>
          <div v-if="showDemoMyListings" class="inline-demo-note"><span class="demo-badge">通知关联示例</span><p>下面这条演示发布对应通知中心的“审核动态”和“留言互动”，点开通知后可以在这里看到同一份内容。</p></div>
          <div v-if="!displayMyListings.length" class="state-panel"><strong>还没有发布内容</strong><span>从资源或技能开始发布第一条信息。</span></div>
          <div v-else class="management-list">
            <article v-for="item in displayMyListings" :key="item.id" class="management-row" :class="{ 'is-demo-row': item.demo }">
              <div class="item-media" :class="item.type"><img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" /><span v-else>{{ item.type === 'skill' ? '技能' : '资源' }}</span></div>
              <div class="admin-info"><strong>{{ item.title }}</strong><span>{{ typeLabel(item.type) }} · {{ item.category_name }} · <b :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}</b></span><small><span class="status-dot" :class="item.status">{{ item.status === 'published' ? '公开展示中' : item.status === 'offline' ? '已下架' : statusLabel(item.status) }}</span><span v-if="item.review_status === 'approved'" class="review-badge">审核通过</span><span v-if="item.demo" class="demo-label">演示</span> · <span class="view-count-inline"><AppIcon name="eye" />{{ listingViewText(item, '0 浏览') }}</span> · {{ item.location || '校内协商' }}</small></div>
              <div class="admin-actions"><button class="outline-btn" @click="openListing(item)">查看</button><button v-if="['published','offline'].includes(item.status)" class="ghost-btn" @click="changeListingStatus(item)">{{ item.status === 'published' ? '下架' : '重新上架' }}</button></div>
            </article>
          </div>
        </section>

        <section v-else-if="tab === 'favorites'" class="page narrow-page">
          <header class="page-heading"><div><h1>我的收藏</h1><p>回看感兴趣的资源和技能，不改变交易状态。</p></div><button class="outline-btn" @click="loadFavorites">刷新</button></header>
          <div v-if="!favoriteListings.length" class="state-panel"><strong>暂时没有收藏</strong><span>在详情页收藏后，会集中显示在这里。</span><button class="primary-btn" @click="navigate('discover')">去双轨广场</button></div>
          <div v-else class="management-list">
            <article v-for="item in favoriteListings" :key="item.id" class="management-row">
              <div class="item-media" :class="item.type"><img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" /><span v-else>{{ item.type === 'skill' ? '技能' : '资源' }}</span></div>
              <div class="admin-info"><strong>{{ item.title }}</strong><span>{{ typeLabel(item.type) }} · {{ item.owner_name }} · <b :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}</b></span><small><span class="credit-score"><b>★</b>{{ listingCreditLabel(item) }}</span> · {{ item.location || '校内协商' }}</small></div>
              <div class="admin-actions"><button class="outline-btn" @click="openListing(item)">查看详情 <span>↗</span></button><button class="save-detail saved" aria-label="取消收藏" @click="toggleFavorite(item)">★</button></div>
            </article>
          </div>
        </section>

        <section v-else-if="tab === 'verification'" class="page narrow-page">
          <header class="page-heading"><div><h1>学生认证</h1><p>课程演示认证和平台人工审核都会与手机号验证分开显示。</p></div><span class="status-pill">{{ verificationLabel(currentUser?.verification_status) }}</span></header>
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
          <header class="page-heading"><div><h1>管理工作台</h1><p>认证材料与举报记录仅管理员可访问。</p></div><button class="outline-btn" @click="loadAdmin">刷新</button></header>
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
          <header class="page-heading"><div><h1>账号与安全</h1><p>手机号用于登录；邮箱绑定是独立联系方式，不代表学生身份。</p></div></header>
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
          <section class="account-security-panel public-profile-settings">
            <div class="section-title"><div><h2>公开主页与隐私</h2><p>别人点开发帖人资料时，只会看到你选择公开的内容。</p></div><button class="outline-btn" @click="openSelfProfile">预览我的主页</button></div>
            <div class="privacy-grid">
              <label><input v-model="profilePrivacy.showCollege" type="checkbox" /><span>学院与年级</span></label>
              <label><input v-model="profilePrivacy.showStats" type="checkbox" /><span>信用分与总浏览量</span></label>
              <label><input v-model="profilePrivacy.showPosts" type="checkbox" /><span>发布过的帖子</span></label>
              <label><input v-model="profilePrivacy.showHonors" type="checkbox" /><span>荣誉墙</span></label>
            </div>
            <p class="privacy-note">学号、手机号、邮箱和认证材料始终不会出现在公开主页。关闭某项后，气泡和个人主页会同步隐藏。</p>
          </section>
        </section>
      </Transition>
    </main>
    <footer v-if="tab !== 'home'" class="workspace-footer"><span>海大互助 · 让资源流转，让技能相遇。</span><span>平台记录协议与双方确认，付款由双方线下完成。 <button @click="navigate('home')">返回首页</button></span></footer>

    <div v-if="notice || error" class="toast" :class="{ error }" role="status">{{ notice || error }}</div>

    <div v-if="ownerBubble" class="owner-bubble" :style="{ left: ownerBubble.left + 'px', top: ownerBubble.top + 'px' }" role="dialog" aria-label="发布者资料">
      <button class="owner-bubble-close" aria-label="关闭发布者资料" @click="closeOwnerBubble">×</button>
      <div class="owner-bubble-head">
        <span class="owner-bubble-avatar">{{ ownerBubble.profile.name.slice(0, 1) }}</span>
        <div><b>{{ ownerBubble.profile.name }}</b><small>{{ ownerBubble.profile.handle || '校园用户' }}<span v-if="ownerBubble.profile.verified" class="owner-verified">✓</span></small></div>
        <span v-if="ownerBubble.profile.isDemo" class="demo-label">演示资料</span>
      </div>
      <p v-if="ownerBubble.profile.bio" class="owner-bubble-bio">{{ ownerBubble.profile.bio }}</p>
      <div v-if="canShowProfileField(ownerBubble.profile, 'showStats')" class="owner-bubble-stats">
        <span><small>信用分</small><b>{{ ownerBubble.profile.credit ?? '—' }}</b></span>
        <span><small>全部帖子浏览</small><b>{{ profileStats(ownerBubble.profile).totalViews.toLocaleString('zh-CN') }}</b></span>
        <span><small>发布</small><b>{{ profileStats(ownerBubble.profile).posts }}</b></span>
      </div>
      <p v-else class="owner-bubble-private">对方选择不公开互助数据。</p>
      <div class="owner-bubble-meta">
        <span v-if="canShowProfileField(ownerBubble.profile, 'showCollege')">{{ ownerBubble.profile.college || '学院未公开' }}</span>
        <span>学号 / 手机号不公开</span>
      </div>
      <button class="primary-btn owner-bubble-action" @click="openOwnerProfileFromBubble">查看个人主页 <AppIcon name="arrow" /></button>
    </div>

    <div v-if="showAuth" class="modal-backdrop" @click.self="showAuth = false">
      <div class="modal auth-modal" role="dialog" aria-modal="true" aria-label="登录与注册">
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
      <div class="modal wide-modal" role="dialog" aria-modal="true" aria-label="发布互助">
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
      <div class="modal wide-modal" role="dialog" aria-modal="true" aria-label="发布详情">
        <button class="modal-close" aria-label="关闭" @click="selectedListing = null">×</button>
        <img v-if="selectedListing.image_urls?.length" class="detail-image" :src="mediaUrl(selectedListing.image_urls[0])" :alt="selectedListing.title" />
        <div class="detail-kicker"><span class="type-tag" :class="selectedListing.type">{{ typeLabel(selectedListing.type) }}</span><span v-if="selectedListing.demo" class="demo-label">设计示例</span><span v-if="isFreeListing(selectedListing)" class="free-label">免费互助</span><span v-if="!selectedListing.demo" class="detail-time">{{ listingTime(selectedListing.created_at) }} 发布</span><span class="detail-views"><AppIcon name="eye" />{{ listingViewText(selectedListing, '0 浏览') }}</span></div>
        <div class="detail-title-row"><h2>{{ selectedListing.title }}</h2><button v-if="isLoggedIn && !isAdmin && !selectedListing.demo && currentUser?.id !== selectedListing.owner_id" class="save-detail" :class="{ saved: favoriteIds.has(selectedListing.id) }" :aria-label="favoriteIds.has(selectedListing.id) ? '取消收藏' : '收藏'" @click="toggleFavorite(selectedListing)">{{ favoriteIds.has(selectedListing.id) ? '★' : '☆' }}</button></div>
        <p class="modal-description">{{ selectedListing.description }}</p>
        <button v-if="selectedOwnerProfile" class="detail-owner-chip" :aria-label="`查看${selectedOwnerProfile.name}的个人主页`" @click.stop="openOwnerBubble(selectedListing, $event)">
          <span class="detail-owner-avatar">{{ selectedOwnerProfile.name.slice(0, 1) }}</span>
          <span class="detail-owner-copy">
            <span class="detail-owner-name">{{ selectedOwnerProfile.name }}<span v-if="selectedOwnerProfile.verified" class="owner-verified">✓</span><span v-if="selectedOwnerProfile.isDemo" class="demo-label">演示主页</span></span>
            <small>{{ canShowProfileField(selectedOwnerProfile, 'showCollege') ? (selectedOwnerProfile.college || '学院未公开') : '学院未公开' }} · 学号与手机号不公开</small>
          </span>
          <span class="detail-owner-stats"><b v-if="canShowProfileField(selectedOwnerProfile, 'showStats')">★ {{ selectedOwnerProfile.credit ?? '未公开' }}</b><b v-else>数据未公开</b><small v-if="canShowProfileField(selectedOwnerProfile, 'showStats')">{{ selectedOwnerStats.totalViews.toLocaleString('zh-CN') }} 总浏览</small></span>
          <span class="detail-owner-more">查看主页 <AppIcon name="arrow" /></span>
        </button>
        <div class="detail-facts"><div><span>校区 / 地点</span><strong>{{ listingCampus(selectedListing) }}</strong></div><div><span>信用分</span><strong v-if="canShowProfileField(selectedOwnerProfile, 'showStats')" class="credit-score"><b>★</b>{{ listingCreditLabel(selectedListing) }}</strong><strong v-else>数据未公开</strong></div><div><span>价格</span><strong :class="{ free: isFreeListing(selectedListing) }">{{ listingPrice(selectedListing) }}</strong></div></div>
        <div v-if="selectedListing.demo" class="payment-note">这是设计示例，仅用于预览界面，不能收藏或发起交易。</div>
        <div v-else class="payment-note">平台不托管资金，也不验证线下微信付款。请在校内公共区域核验物品或服务。</div>
        <section v-if="selectedStory" class="detail-story">
          <div class="detail-story-head">
            <span class="story-kicker">MUTUAL STORY</span>
            <h3>{{ selectedStory.title }}</h3>
            <span class="story-meta">{{ selectedStory.meta }}</span>
          </div>
          <p>{{ selectedStory.content }}</p>
          <footer><span>—— {{ selectedStory.author }}</span><span v-if="selectedListing.demo" class="demo-label">演示故事</span></footer>
        </section>
        <section class="detail-comments">
          <div class="detail-section-head">
            <div><span class="story-kicker">THANK-YOU WALL</span><h3>留言与感谢</h3></div>
            <span class="comment-count">{{ selectedComments.length }} 条</span>
          </div>
          <p class="comments-note">完成一次互助后，双方可以在这里留下一句话。演示留言只保存在本机浏览器。</p>
          <div v-if="selectedComments.length" class="comment-list">
            <article v-for="comment in selectedComments" :key="comment.id" class="comment-card" :class="{ 'is-thanks': comment.thanks }">
              <span class="comment-avatar" aria-hidden="true">{{ (comment.author || '校园访客').slice(0, 1) }}</span>
              <div class="comment-body">
                <header><b>{{ comment.author }}</b><span>{{ comment.college }}</span><time>{{ comment.time }}</time></header>
                <p>{{ comment.content }}</p>
                <span v-if="comment.thanks" class="thanks-card">✦ 感谢卡</span>
              </div>
            </article>
          </div>
          <div v-else class="comment-empty">还没有留言，来留下第一句感谢。</div>
          <form class="comment-form" @submit.prevent="addListingComment">
            <textarea v-model="commentDraft" maxlength="180" rows="2" placeholder="写一句留言或感谢，例如：书已收到，谢谢冒雨送来。"></textarea>
            <div class="comment-form-foot">
              <button type="button" class="comment-kind" :class="{ active: commentAsThanks }" @click="commentAsThanks = !commentAsThanks">{{ commentAsThanks ? '✦ 作为感谢卡' : '普通留言' }}</button>
              <span>{{ commentDraft.length }} / 180</span>
              <button class="primary-btn" :disabled="commentDraft.trim().length < 2">留下感谢</button>
            </div>
          </form>
        </section>
        <div v-if="selectedListing.demo" class="inline-alert detail-access-note">示例内容仅供界面展示。</div>
        <div v-else-if="currentUser?.id === selectedListing.owner_id" class="inline-alert detail-access-note">这是你的发布信息，不能向自己发起交易。</div>
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

    <div v-if="selectedProfile" class="modal-backdrop" @click.self="selectedProfile = null">
      <div class="modal wide-modal public-profile-modal" role="dialog" aria-modal="true" aria-label="个人主页">
        <button class="modal-close" aria-label="关闭" @click="selectedProfile = null">×</button>
        <header class="public-profile-head">
          <span class="public-profile-avatar">{{ selectedProfile.name.slice(0, 1) }}</span>
          <div class="public-profile-title">
            <div><h2>{{ selectedProfile.name }}</h2><span v-if="selectedProfile.verified" class="owner-verified" aria-label="平台认证">✓</span><span v-if="selectedProfile.isDemo" class="demo-label">演示主页</span><span v-if="selectedProfile.isSelf" class="demo-label">我的主页</span></div>
            <p>{{ selectedProfile.handle || '校园互助用户' }}<span v-if="canShowProfileField(selectedProfile, 'showCollege') && selectedProfile.college"> · {{ selectedProfile.college }}</span><span v-if="selectedProfile.grade"> · {{ selectedProfile.grade }}</span></p>
          </div>
        </header>
        <p v-if="selectedProfile.bio" class="public-profile-bio">{{ selectedProfile.bio }}</p>
        <div class="public-profile-meta">
          <span>{{ selectedProfile.joined || '校园互助成员' }}</span>
          <span>学号、手机号与认证材料均不公开</span>
        </div>
        <div v-if="canShowProfileField(selectedProfile, 'showStats')" class="public-profile-stats">
          <div><span>信用分</span><strong>{{ selectedProfile.credit ?? '—' }}</strong></div>
          <div><span>全部帖子浏览</span><strong>{{ selectedProfileStats.totalViews.toLocaleString('zh-CN') }}</strong></div>
          <div><span>发布帖子</span><strong>{{ selectedProfileStats.posts }}</strong></div>
          <div><span>完成互助</span><strong>{{ selectedProfileStats.completed }}</strong></div>
        </div>
        <p v-else class="public-profile-private">这位同学选择不公开信用分和浏览量等互助数据，但仍可以浏览公开帖子。</p>
        <section v-if="canShowProfileField(selectedProfile, 'showHonors')" class="public-profile-section">
          <div class="public-profile-section-head"><div><span class="story-kicker">HONOR WALL</span><h3>荣誉墙</h3></div><span>{{ selectedProfile.honors?.length || 0 }} 枚</span></div>
          <div v-if="selectedProfile.honors?.length" class="honor-wall">
            <span v-for="(honor, index) in selectedProfile.honors" :key="honor" class="honor-chip" :class="'tone-' + (index % 4)">✦ {{ honor }}</span>
          </div>
          <p v-else class="profile-empty-line">还没有公开的荣誉记录。</p>
        </section>
        <section v-if="canShowProfileField(selectedProfile, 'showPosts')" class="public-profile-section">
          <div class="public-profile-section-head"><div><span class="story-kicker">LISTINGS</span><h3>发布过的帖子</h3></div><span>{{ selectedProfileListings.length }} 条公开</span></div>
          <div v-if="selectedProfileListings.length" class="profile-listing-list">
            <button v-for="item in selectedProfileListings" :key="item.id" class="profile-listing-row" @click="openListingFromProfile(item)">
              <span class="profile-listing-type" :class="item.type">{{ item.type === 'skill' ? '技' : '物' }}</span>
              <span class="profile-listing-copy"><b>{{ item.title }}</b><small>{{ typeLabel(item.type) }} · {{ item.category_name }} · {{ listingViewText(item, '新发布') }}</small></span>
              <span class="profile-listing-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}</span>
              <AppIcon name="arrow" />
            </button>
          </div>
          <p v-else class="profile-empty-line">还没有公开的帖子。</p>
        </section>
        <div class="public-profile-foot">
          <p>{{ selectedProfile.isSelf ? '这些展示范围可以在“账号与安全”中随时调整。' : '主页由发帖人选择公开范围，平台只展示与交易判断有关的信息。' }}</p>
          <button v-if="selectedProfile.isSelf" class="outline-btn" @click="selectedProfile = null; selectedListing = null; navigate('profile')">调整公开范围</button>
        </div>
      </div>
    </div>

    <div v-if="selectedNotification" class="modal-backdrop" @click.self="selectedNotification = null">
      <div class="modal notification-detail-modal" role="dialog" aria-modal="true" aria-label="通知详情">
        <button class="modal-close" aria-label="关闭" @click="selectedNotification = null">×</button>
        <div class="notification-detail-head">
          <span class="notification-icon" :class="'is-' + selectedNotification.type"><AppIcon :name="selectedNotification.icon" /></span>
          <div><span class="notification-type">{{ selectedNotification.typeLabel }}</span><h2>{{ selectedNotification.title }}</h2></div>
          <em v-if="selectedNotification.urgent" class="notification-urgent">紧急</em>
        </div>
        <p class="notification-detail-content">{{ selectedNotification.content }}</p>
        <div class="notification-detail-meta"><time>{{ selectedNotification.time }}</time><span>内置演示通知 · 不会发送短信</span></div>
        <div class="notification-detail-actions">
          <button class="outline-btn" @click="selectedNotification = null">稍后再看</button>
          <button class="primary-btn" @click="confirmNotification">{{ selectedNotification.action?.label || '我知道了' }}</button>
        </div>
      </div>
    </div>

    <div v-if="selectedTransaction" class="modal-backdrop" @click.self="selectedTransaction = null">
      <div class="modal wide-modal transaction-modal" role="dialog" aria-modal="true" aria-label="交易消息与协议">
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
