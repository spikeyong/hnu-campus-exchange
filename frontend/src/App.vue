<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import ExchangeHome from './components/ExchangeHome.vue'
import AdminWorkspace from './components/AdminWorkspace.vue'
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
const PROFILE_PREFS_KEY = 'campus_profile_prefs_v1'
const PERSONALIZATION_KEY = 'campus_personalization_v1'
const SCHEDULE_KEY = 'campus_schedule_v1'
const DEMO_FAVORITES_KEY = 'campus_demo_favorites_v1'
const SCENES = [
  { id: 'pavilion', name: '湖心亭远眺', note: '东坡湖 · 六角亭', url: '/exchange/scenes/scene-pavilion.jpg', thumb: '/exchange/scenes/thumbs/scene-pavilion.jpg' },
  { id: 'courtyard', name: '白楼树影', note: '教学楼 · 午后', url: '/exchange/scenes/scene-courtyard.jpg', thumb: '/exchange/scenes/thumbs/scene-courtyard.jpg' },
  { id: 'clocktower', name: '钟楼棕榈', note: '校门 · 钟楼', url: '/exchange/scenes/scene-clocktower.jpg', thumb: '/exchange/scenes/thumbs/scene-clocktower.jpg' },
  { id: 'lawn', name: '草坪钟楼', note: '中央草坪 · 砖径', url: '/exchange/scenes/scene-lawn.jpg', thumb: '/exchange/scenes/thumbs/scene-lawn.jpg' },
  { id: 'blossom', name: '花树钟楼', note: '凤凰花 · 钟楼', url: '/exchange/scenes/scene-blossom.jpg', thumb: '/exchange/scenes/thumbs/scene-blossom.jpg' },
  { id: 'lake', name: '湖畔倒影', note: '东坡湖 · 倒影', url: '/exchange/scenes/scene-lake.jpg', thumb: '/exchange/scenes/thumbs/scene-lake.jpg' },
]
const PAGE_SCENE = {
  discover: 'pavilion',
  transactions: 'lake',
  schedule: 'clocktower',
  'my-listings': 'pavilion',
  favorites: 'lawn',
  verification: 'clocktower',
  me: 'blossom',
  settings: 'courtyard',
  profile: 'lake',
  admin: 'lawn',
}
const PAGE_BACKGROUNDS = Object.fromEntries(
  Object.entries(PAGE_SCENE).map(([key, id]) => [key, (SCENES.find((scene) => scene.id === id) || SCENES[0]).url]),
)
const PALETTE_OPTIONS = [
  { id: 'default', name: '水彩海风', note: '湖绿与珊瑚色', colors: ['#8cc9e8', '#3f7f8a', '#e88b70'] },
  { id: 'lagoon', name: '潮汐蓝', note: '清透湖蓝', colors: ['#8cc4d8', '#3f8f9e', '#cf8268'] },
  { id: 'sunset', name: '落日橘', note: '砖红与暖沙', colors: ['#f0c9a0', '#b06a45', '#d9764f'] },
  { id: 'forest', name: '苔原绿', note: '叶绿与米白', colors: ['#b9d3ae', '#4f7a55', '#b9784f'] },
  { id: 'lavender', name: '暮色紫', note: '暮紫与灰蓝', colors: ['#c3b6e0', '#7364a4', '#c07f8f'] },
]
const HONOR_META = {
  '平台认证': { icon: 'shield', note: '学生身份已通过平台人工审核，不是学校官方背书。' },
  '信用之星': { icon: 'spark', note: '信用分在 105 以上，来自按时完成与双方好评。' },
  '完成互助': { icon: 'exchange', note: '至少有一笔交易走完双方确认，形成真实履约记录。' },
  '活跃发布': { icon: 'box', note: '发布了三条以上资源或技能，愿意先把手里的东西交出去。' },
  '初来乍到': { icon: 'user', note: '刚刚加入互助广场，完成一次互助后会解锁更多勋章。' },
}

function defaultProfilePrivacy() {
  return { showCollege: true, showStats: true, showPosts: true, showHonors: true }
}

function defaultPersonalization() {
  return {
    palette: 'default',
    backgroundMode: 'page',
    fixedBackground: '',
    customBackgrounds: [],
    customBackgroundId: '',
    backgroundBlur: 2,
    backgroundDim: 38,
  }
}

function loadStoredJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function saveStoredJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch {
    // Storage can be unavailable (private mode) or full (local background images).
    return false
  }
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
        { key: 'me', label: '个人中心', type: 'all' },
        { key: 'settings', label: '个人设置', type: 'all' },
        { key: 'my-listings', label: '我的发布', type: 'all' },
        { key: 'favorites', label: '我的收藏', type: 'all' },
        { key: 'transactions', label: '我的交易', type: 'all' },
        { key: 'schedule', label: '我的日程', type: 'all' },
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
const storedSchedule = loadStoredJson(SCHEDULE_KEY, {})
const scheduleStore = ref(storedSchedule && typeof storedSchedule === 'object' && !Array.isArray(storedSchedule) ? storedSchedule : {})
const storedDemoFavorites = loadStoredJson(DEMO_FAVORITES_KEY, {})
const demoFavoritesStore = ref(storedDemoFavorites && typeof storedDemoFavorites === 'object' && !Array.isArray(storedDemoFavorites) ? storedDemoFavorites : {})
const showScheduleForm = ref(false)
const showConflictDialog = ref(false)
const showReportDialog = ref(false)
const reportTarget = ref(null)
const pendingSchedule = ref(null)
const scheduleConflicts = ref([])
const clockTick = ref(Date.now())
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
const storedProfilePrefs = loadStoredJson(PROFILE_PREFS_KEY, {})
const profilePrefsStore = ref(storedProfilePrefs && typeof storedProfilePrefs === 'object' && !Array.isArray(storedProfilePrefs) ? storedProfilePrefs : {})
const storedPersonalization = loadStoredJson(PERSONALIZATION_KEY, {})
const personalizationStore = ref(storedPersonalization && typeof storedPersonalization === 'object' && !Array.isArray(storedPersonalization) ? storedPersonalization : {})
const profileBio = ref('')
const profilePrivacy = ref(defaultProfilePrivacy())
const personalization = ref(defaultPersonalization())
const backgroundInput = ref(null)
const backgroundDragging = ref(false)
const customBackgroundWarning = ref(false)
const profileIntroDirty = ref(false)
const demoMyListingStatus = ref('published')
// Notification bookkeeping must exist before the immediate user watcher runs.
let notificationPrimedUser = null
const announcedNotificationIds = new Set()
watch(currentUser, (user) => {
  demoTransaction.initiator_id = user?.id ?? null
    demoTransaction.initiator_name = user?.name || '我'
  if (!user || user.role === 'admin') {
    notificationPanelOpen.value = false
    selectedNotification.value = null
    selectedProfile.value = null
    ownerBubble.value = null
    showScheduleForm.value = false
    showConflictDialog.value = false
    showReportDialog.value = false
    reportTarget.value = null
  }
  loadProfilePrefs(user)
  loadPersonalization(user)
  notificationPrimedUser = null
  announcedNotificationIds.clear()
}, { immediate: true })
watch(profilePrivacy, () => saveProfilePrefs(), { deep: true })
// Local backgrounds can be a few hundred KB of base64, so debounce the write.
let personalizationSaveTimer = 0
watch(personalization, () => {
  window.clearTimeout(personalizationSaveTimer)
  personalizationSaveTimer = window.setTimeout(() => savePersonalization(), 320)
}, { deep: true })
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
let scheduleTicker = null
let notificationTicker = null
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
const scheduleForm = reactive({ transaction_id: '', title: '', counterpart: '', date: '', start_time: '15:00', end_time: '16:00', location: '', note: '' })
const reviewForm = reactive({ rating: 5, content: '' })
const reportForm = reactive({ reason: '', description: '' })
const verificationForm = reactive({ student_no: '', college: '', grade: '' })
const emailForm = reactive({ email: '', code: '' })
const isFreeListing = (item) => Number(item?.price || 0) === 0
const listingCredit = (item) => item?.owner_credit_score == null ? '信用未公开' : `信用 ${item.owner_credit_score}`
const listingCreditLabel = (item) => {
  const profile = profileForListing(item)
  if (profile && !canShowProfileField(profile, 'showStats')) return '数据未公开'
  return listingCredit(item)
}
const listingPrice = (item) => isFreeListing(item) ? '免费' : `¥${item.price}`
const listingPlace = (item) => item?.type === 'skill'
  ? (item.service_mode === 'online' ? '线上' : item.service_mode === 'both' ? '线上 / 线下' : (item.location || '校内协商'))
  : (item?.location || '校内协商')
const listingTime = (value) => value ? new Date(value).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) : '刚刚'
const listingStatusLabel = (status) => ({ published: '公开', offline: '已下架', reserved: '交易中', completed: '已完成', deleted: '已删除' }[status] || status)
const isFeatured = (item) => Boolean(item?.featured || item?.is_featured)
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
const selectedStory = computed(() => selectedListing.value ? demoStories[selectedListing.value.id] || null : null)
const selectedOwnerProfile = computed(() => selectedListing.value ? profileForListing(selectedListing.value) : null)
const selectedOwnerStats = computed(() => profileStats(selectedOwnerProfile.value))
const selectedComments = computed(() => {
  const listingId = selectedListing.value?.id
  if (!listingId) return []
  return [...(demoComments[listingId] || []), ...(localComments.value[listingId] || [])]
})
const demoListings = [
  { id: 'demo-book', demo: true, type: 'resource', category_name: '教材与学习资料', title: '英文诗集《Milk and Honey》', description: '书页完整，有少量阅读标记，可在紫荆操场附近自取。', price: 28, price_unit: '元', location: '海甸校区 · 图书馆北门', campus_area: '海甸校区', condition_level: '九成新', service_mode: 'offline', view_count: 1286, featured: true, owner_id: 'demo-user-lin', owner_name: '林小满', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 104, image_urls: ['https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-headphones', demo: true, type: 'resource', category_name: '数码设备', title: '头戴式降噪耳机', description: '功能正常，耳罩已更换，附收纳袋，支持当面试听。', price: 96, price_unit: '元', location: '海甸校区 · 二食堂门口', campus_area: '海甸校区', condition_level: '八成新', service_mode: 'offline', view_count: 864, owner_id: 'demo-user-zhou', owner_name: '周予安', owner_college: '信息科学技术学院', owner_verified: true, owner_credit_score: 112, image_urls: ['https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-bicycle', demo: true, type: 'resource', category_name: '生活用品', title: '通勤自行车，可试骑', description: '刹车和车灯正常，毕业离校转让，仅限校内当面交易。', price: 180, price_unit: '元', location: '海甸校区 · 东坡湖旁', campus_area: '海甸校区', condition_level: '有使用痕迹', service_mode: 'offline', view_count: 512, owner_id: 'demo-user-xu', owner_name: '许知行', owner_college: '国际商学院', owner_verified: true, owner_credit_score: 101, image_urls: ['https://images.unsplash.com/photo-1529422643029-d4585747aaf2?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-python', demo: true, type: 'skill', category_name: '技能辅导', title: 'Python 作业思路梳理', description: '讲解基础语法和调试思路，不代写作业，可线上或图书馆。', price: 25, price_unit: '小时', location: '海甸校区 · 图书馆', campus_area: '海甸校区', service_mode: 'both', available_time: '工作日晚 7 点后、周末下午', view_count: 733, featured: true, owner_id: 'demo-user-zhou', owner_name: '周予安', owner_college: '信息科学技术学院', owner_verified: true, owner_credit_score: 112, image_urls: ['https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-english', demo: true, type: 'skill', category_name: '技能辅导', title: '英语口语搭子 · 四六级', description: '每周两次情景对话，互相纠音，首次可免费体验 30 分钟。', price: 0, price_unit: '元', location: '海甸校区 · 社科楼', campus_area: '海甸校区', service_mode: 'offline', available_time: '周末下午', view_count: 958, owner_id: 'demo-user-lin', owner_name: '林小满', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 104, image_urls: ['https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-photo', demo: true, type: 'skill', category_name: '设计与媒体', title: '社团活动摄影协助', description: '可拍活动纪实与合照，交付基础调色照片，时间需提前约定。', price: 80, price_unit: '场', location: '城西校区 · 教学楼大厅', campus_area: '城西校区', service_mode: 'offline', available_time: '周末', view_count: 421, owner_id: 'demo-user-chen', owner_name: '陈一禾', owner_college: '国际商学院', owner_verified: true, owner_credit_score: null, image_urls: ['https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-finals-notes', demo: true, type: 'resource', category_name: '教材与学习资料', title: '宏观经济学复习笔记（含题型整理）', description: '期末周整理的重点框架和计算题题型，附一份空白自测卷，图书馆自取。', price: 15, price_unit: '份', location: '海甸校区 · 图书馆二楼', campus_area: '海甸校区', condition_level: '全新', service_mode: 'offline', view_count: 642, owner_id: 'demo-user-lin', owner_name: '林小满', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 104, image_urls: ['https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=900&q=80'] },
  { id: 'demo-freshman-guide', demo: true, type: 'skill', category_name: '技能辅导', title: '新生校园半日向导', description: '带新生认教学楼、食堂、快递点和校医院，可顺路帮忙搬一次行李。', price: 0, price_unit: '元', location: '海甸校区 · 校门口', campus_area: '海甸校区', service_mode: 'offline', available_time: '开学季周末', view_count: 388, owner_id: 'demo-user-xu', owner_name: '许知行', owner_college: '国际商学院', owner_verified: true, owner_credit_score: 101, image_urls: [] },
  { id: 'demo-graduation-box', demo: true, type: 'resource', category_name: '生活用品', title: '毕业季清仓：台灯和收纳盒', description: '台灯亮度正常，收纳盒有轻微使用痕迹，毕业前在宿舍楼下自取。', price: 30, price_unit: '套', location: '海甸校区 · 紫荆公寓', campus_area: '海甸校区', condition_level: '有使用痕迹', service_mode: 'offline', view_count: 276, owner_id: 'demo-user-lin', owner_name: '林小满', owner_college: '人文传播学院', owner_verified: true, owner_credit_score: 104, image_urls: ['https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=80'] },
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
      ? `楼${filters.min_price} 鈥?楼${filters.max_price}`
      : filters.min_price !== ''
        ? `鈮?楼${filters.min_price}`
        : `鈮?楼${filters.max_price}`
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
    if (value.keyword) bits.push(`「${value.keyword}」`)
    if (value.min_price !== '' && value.min_price != null) bits.push(`最低 ¥${value.min_price}`)
    if (value.max_price !== '' && value.max_price != null) bits.push(`最高 ¥${value.max_price}`)
  if (value.condition && value.condition !== 'all') bits.push(CONDITION_LABELS[value.condition] || value.condition)
  if (value.service_mode && value.service_mode !== 'all') bits.push(SERVICE_MODE_LABELS[value.service_mode] || value.service_mode)
  if (value.campus && value.campus !== 'all') bits.push(CAMPUS_LABELS[value.campus] || value.campus)
    if (value.story_only) bits.push('有互助故事')
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
const demoFavoriteIds = computed(() => new Set(currentUser.value ? (demoFavoritesStore.value[currentUser.value.id] || []) : []))
const displayFavoriteListings = computed(() => [
  ...favoriteListings.value,
  ...demoListings.filter((item) => demoFavoriteIds.value.has(item.id)),
])
const scheduleEntries = computed(() => {
  const items = currentUser.value ? (scheduleStore.value[currentUser.value.id] || []) : []
  return Array.isArray(items) ? [...items].sort((a, b) => `${a.date} ${a.start_time}`.localeCompare(`${b.date} ${b.start_time}`)) : []
})
const scheduleConflictGroups = computed(() => findScheduleConflictGroups(scheduleEntries.value))
const scheduleNotifications = computed(() => {
  clockTick.value
  return buildScheduleNotifications(scheduleEntries.value, scheduleConflictGroups.value)
})

// Real events for the bell: derive one notification per transaction that needs
// the signed-in user's attention. Read state is stored with the other notices.
function formatNotificationTime(value) {
  if (!value) return ''
  // The API returns naive UTC timestamps; treat them as UTC before comparing.
  const raw = value instanceof Date ? value.toISOString() : String(value)
  const normalized = /[zZ]$|[+-]\d{2}:\d{2}$/.test(raw) ? raw : `${raw.replace(' ', 'T')}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return ''
  const diff = Date.now() - date.getTime()
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))} 分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))} 小时前`
  if (diff < 7 * 24 * 60 * 60 * 1000) return `${Math.floor(diff / (24 * 60 * 60 * 1000))} 天前`
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`
}

function transactionNotification(item) {
  const me = currentUser.value?.id
  if (!me || item.demo) return null
  const isProvider = item.provider_id === me
  const isInitiator = item.initiator_id === me
  if (!isProvider && !isInitiator) return null

  const who = isProvider ? (item.initiator_name || '对方') : (item.provider_name || '对方')
  const listing = item.listing_title || '校园互助'
  const amount = Number(item.agreed_price ?? item.proposed_price ?? 0)
  const money = amount > 0 ? `¥${amount}` : '免费互助'
  const place = `${item.proposed_time || '时间待协商'} · ${item.proposed_location || '地点待协商'}`
  const eventTime = (...values) => values.find(Boolean) || item.created_at

  const base = {
    type: 'transaction',
    icon: 'exchange',
    demo: false,
    group: 'real',
    action: { tab: 'transactions', label: '去处理交易', transactionId: item.id },
  }

  switch (item.status) {
    case 'pending_provider':
      if (!isProvider) return null
      return {
        ...base,
        id: `tx-${item.id}-request`,
        typeLabel: '交易请求',
        icon: 'bell',
        urgent: true,
        time: formatNotificationTime(item.created_at),
        title: '收到一条新的交易请求',
        summary: `${who} 想和你交换《${listing}》`,
        content: `${who} 想以 ${money} 交换《${listing}》，约定 ${place}。请求说明：${item.request_note || '未填写'}。请到“我的交易”接受或拒绝；24 小时内未处理会一直保留在这里。`,
        action: { ...base.action, label: '去处理请求' },
      }
    case 'pending_initiator':
      if (!isInitiator) return null
      return {
        ...base,
        id: `tx-${item.id}-accepted`,
        typeLabel: '协议待确认',
        icon: 'clock',
        urgent: true,
        time: formatNotificationTime(eventTime(item.provider_agreed_at)),
        title: '对方接受了你的交易请求',
        summary: `《${listing}》等待你确认协议`,
        content: `${who} 接受了你在《${listing}》下发出的请求，金额 ${money}，约定 ${place}。双方确认协议后交易才会进入交付阶段。`,
        action: { ...base.action, label: '去确认协议' },
      }
    case 'agreed':
      return {
        ...base,
        id: `tx-${item.id}-agreed`,
        typeLabel: '协议达成',
        icon: 'exchange',
        urgent: false,
        time: formatNotificationTime(eventTime(item.initiator_agreed_at, item.provider_agreed_at)),
        title: '交易协议已达成',
        summary: `《${listing}》已进入交付阶段`,
        content: `《${listing}》的协议已由双方确认，金额 ${money}，约定 ${place}。交付完成后请在“我的交易”里确认。`,
        action: { ...base.action, label: '查看这笔交易' },
      }
    case 'provider_confirmed':
      if (!isInitiator) return null
      return {
        ...base,
        id: `tx-${item.id}-delivered`,
        typeLabel: '待确认收货',
        icon: 'box',
        urgent: true,
        time: formatNotificationTime(item.provider_completed_at),
        title: '对方已确认交付',
        summary: `《${listing}》等待你确认收货`,
        content: `${who} 已确认交付《${listing}》。核对物品或服务后，请在“我的交易”中确认收货，双方都确认后交易才会完成。`,
        action: { ...base.action, label: '去确认收货' },
      }
    case 'requester_confirmed':
      if (!isProvider) return null
      return {
        ...base,
        id: `tx-${item.id}-received`,
        typeLabel: '待确认交付',
        icon: 'box',
        urgent: true,
        time: formatNotificationTime(item.requester_completed_at),
        title: '对方已确认收货',
        summary: `《${listing}》等待你确认交付`,
        content: `${who} 已确认收到《${listing}》。请确认你已完成交付，双方都确认后交易才会完成。`,
        action: { ...base.action, label: '去确认交付' },
      }
    case 'completed':
      return {
        ...base,
        id: `tx-${item.id}-completed`,
        typeLabel: '交易完成',
        icon: 'shield',
        urgent: false,
        time: formatNotificationTime(eventTime(item.requester_completed_at, item.provider_completed_at)),
        title: '一笔交易已完成',
        summary: `《${listing}》双方已确认完成`,
        content: `《${listing}》已完成双方确认，金额 ${money}。可以回到交易详情给对方留下评价或感谢卡。`,
        action: { ...base.action, label: '查看交易' },
      }
    case 'cancelled':
      return {
        ...base,
        id: `tx-${item.id}-cancelled`,
        typeLabel: '交易取消',
        icon: 'close',
        urgent: false,
        time: formatNotificationTime(item.created_at),
        title: '一笔交易已取消',
        summary: `《${listing}》的交易已取消`,
        content: `《${listing}》的交易已取消。如果是对方取消，可以在交易详情里查看取消原因；需要时也可以重新在广场里发起请求。`,
        action: { ...base.action, label: '查看交易' },
      }
    case 'rejected':
      if (!isInitiator) return null
      return {
        ...base,
        id: `tx-${item.id}-rejected`,
        typeLabel: '请求被拒绝',
        icon: 'close',
        urgent: false,
        time: formatNotificationTime(item.created_at),
        title: '交易请求未被接受',
        summary: `《${listing}》的请求被拒绝`,
        content: `${who} 拒绝了你在《${listing}》下发出的交易请求。可以回到广场看看其他帖子，或换一个交付时间再沟通。`,
        action: { tab: 'discover', type: 'all', label: '回广场看看' },
      }
    default:
      return null
  }
}

const transactionNotifications = computed(() => {
  if (!isLoggedIn.value || isAdmin.value) return []
  return transactions.value.map(transactionNotification).filter(Boolean)
})
const realNotifications = computed(() => [
  ...transactionNotifications.value,
  ...scheduleNotifications.value.map((item) => ({ ...item, group: 'real' })),
])
const realUnreadCount = computed(() => realNotifications.value.filter((item) => !readNotificationSet.value.has(item.id)).length)
const allNotifications = computed(() => [...realNotifications.value, ...demoNotifications.map((item) => ({ ...item, group: 'demo' }))])
const unreadNotifications = computed(() => allNotifications.value.filter((item) => !readNotificationSet.value.has(item.id)))
const unreadNotificationCount = computed(() => unreadNotifications.value.length)
const hasUrgentNotification = computed(() => unreadNotifications.value.some((item) => item.urgent))
const scheduleDraftConflicts = computed(() => {
  if (!scheduleForm.date || !scheduleForm.start_time || !scheduleForm.end_time) return []
  return findConflictsForDraft(scheduleForm, scheduleEntries.value)
})
const scheduleConflictIds = computed(() => new Set(scheduleConflictGroups.value.flatMap((group) => group.entries.map((entry) => entry.id))))
const todayScheduleCount = computed(() => {
  clockTick.value
  return scheduleEntries.value.filter((entry) => entry.date === todayISO()).length
})
const upcomingScheduleCount = computed(() => {
  clockTick.value
  return scheduleEntries.value.filter((entry) => entry.date >= todayISO()).length
})
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
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join('、')
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
  if (notificationPanelOpen.value) pollNotificationQueue()
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
  markNotificationRead(item)
}

async function confirmNotification() {
  const item = selectedNotification.value
  if (!item) return
  markNotificationRead(item)
  selectedNotification.value = null
  if (item.action?.transactionId) {
    navigate('transactions')
    await nextTick()
    const target = displayTransactions.value.find((transaction) => String(transaction.id) === String(item.action.transactionId))
    if (target) {
      await openTransaction(target)
    } else {
      flash('这笔交易不在当前列表里，已为你打开“我的交易”')
    }
    return
  }
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
  readNotificationIds.value = [...new Set([...readNotificationIds.value, ...allNotifications.value.map((item) => item.id)])]
  saveStoredJson(NOTIFICATION_READ_KEY, readNotificationIds.value)
  flash('所有通知已标为已读')
}

function pad2(value) {
  return String(value).padStart(2, '0')
}

function isoDate(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

function todayISO() {
  return isoDate(new Date())
}

function addDaysISO(days) {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return isoDate(date)
}

function timeToMinutes(value) {
  const match = String(value || '').match(/^(\d{1,2}):(\d{2})$/)
  if (!match) return null
  return Number(match[1]) * 60 + Number(match[2])
}

function minutesToTime(total) {
  const normalized = ((Number(total) % 1440) + 1440) % 1440
  return `${pad2(Math.floor(normalized / 60))}:${pad2(normalized % 60)}`
}

function addMinutesToTime(value, minutes) {
  const start = timeToMinutes(value)
  if (start == null) return ''
  return minutesToTime(start + minutes)
}

function guessScheduleDate(value) {
  const text = String(value || '')
  const now = new Date()
  const explicitDate = text.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/)
  if (explicitDate) return `${explicitDate[1]}-${pad2(explicitDate[2])}-${pad2(explicitDate[3])}`
  if (text.includes('今天')) return isoDate(now)
  if (text.includes('明天')) {
    now.setDate(now.getDate() + 1)
    return isoDate(now)
  }
    const weekdayMatch = text.match(/([日一二三四五六])/)
  if (weekdayMatch) {
      const target = { 日: 0, 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6 }[weekdayMatch[1]]
    let delta = (target - now.getDay() + 7) % 7
    if (delta === 0) delta = 7
    now.setDate(now.getDate() + delta)
    return isoDate(now)
  }
  now.setDate(now.getDate() + 1)
  return isoDate(now)
}

function guessStartTime(value) {
    const match = String(value || '').match(/(\d{1,2})[:：](\d{2})/)
  if (!match) return '15:00'
  return `${pad2(match[1])}:${match[2]}`
}

function scheduleDateTime(entry) {
  if (!entry?.date || !entry?.start_time) return null
  const date = new Date(`${entry.date}T${entry.start_time}:00`)
  return Number.isNaN(date.getTime()) ? null : date
}

function scheduleDayLabel(entry) {
  const today = todayISO()
  const tomorrow = addDaysISO(1)
  if (entry.date === today) return '今天'
  if (entry.date === tomorrow) return '明天'
  const start = new Date(`${entry.date}T00:00:00`)
  const base = new Date(`${today}T00:00:00`)
  const days = Math.round((start - base) / 86400000)
  if (days > 1) return `${days} 天后`
    if (days < 0) return '已结束'
  return entry.date
}

function scheduleDayNumber(date) {
  return String(Number(String(date || '').slice(8, 10)) || '')
}

function scheduleMonth(date) {
  const month = Number(String(date || '').slice(5, 7))
  return month ? `${month} 月` : ''
}

function scheduleDateLabel(entry) {
  const date = new Date(`${entry.date}T00:00:00`)
  if (Number.isNaN(date.getTime())) return entry.date
  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric', weekday: 'short' })
}

function scheduleStatusLabel(entry) {
  if (entry.date < todayISO()) return '已结束'
  if (entry.date === todayISO()) return '今天'
  return scheduleDayLabel(entry)
}

function findConflictsForDraft(draft, entries = scheduleEntries.value) {
  const start = timeToMinutes(draft.start_time)
  const end = timeToMinutes(draft.end_time)
  if (start == null || end == null || end <= start) return []
  return entries.filter((entry) => {
    if (entry.date !== draft.date) return false
    if (draft.id && entry.id === draft.id) return false
    const otherStart = timeToMinutes(entry.start_time)
    const otherEnd = timeToMinutes(entry.end_time)
    if (otherStart == null || otherEnd == null) return false
    return start < otherEnd && end > otherStart
  })
}

function findScheduleConflictGroups(entries) {
  const groups = []
  for (let i = 0; i < entries.length; i += 1) {
    for (let j = i + 1; j < entries.length; j += 1) {
      const a = entries[i]
      const b = entries[j]
      if (a.date !== b.date) continue
      const aStart = timeToMinutes(a.start_time)
      const aEnd = timeToMinutes(a.end_time)
      const bStart = timeToMinutes(b.start_time)
      const bEnd = timeToMinutes(b.end_time)
      if (aStart == null || aEnd == null || bStart == null || bEnd == null) continue
      if (aStart < bEnd && aEnd > bStart) {
        groups.push({ key: [a.id, b.id].sort().join('-'), entries: [a, b] })
      }
    }
  }
  return groups
}

function buildScheduleNotifications(entries, conflictGroups) {
  const notifications = []
  const today = todayISO()
  const base = new Date(`${today}T00:00:00`)
  entries.forEach((entry) => {
    const start = new Date(`${entry.date}T${entry.start_time}:00`)
    if (Number.isNaN(start.getTime())) return
    if (start.getTime() < Date.now() - 3600000) return
    const days = Math.round((new Date(`${entry.date}T00:00:00`) - base) / 86400000)
    if (days > 3) return
    const when = days === 0 ? '今天' : days === 1 ? '明天' : `${days} 天后`
    notifications.push({
      id: `schedule-${entry.id}`,
      type: 'schedule',
      typeLabel: '日程提醒',
      icon: 'calendar',
        title: `日程提醒：${entry.title}`,
        summary: `${when} ${entry.start_time} · ${entry.location || '地点待定'}`,
        content: `${when} ${entry.start_time}–${entry.end_time}，${entry.location || '地点待定'}。${entry.counterpart ? `对方：${entry.counterpart}。` : ''}${entry.note ? `备注：${entry.note}` : ''}`,
      time: `${when} ${entry.start_time}`,
      urgent: days <= 1,
      action: { tab: 'schedule', label: '查看我的日程' },
    })
  })
  conflictGroups.filter((group) => group.entries.some((entry) => entry.date >= todayISO())).forEach((group) => {
    const [a, b] = group.entries
    notifications.push({
      id: `schedule-conflict-${group.key}`,
      type: 'schedule-conflict',
      typeLabel: '日程冲突',
      icon: 'clock',
      title: '日程时间冲突，请确认',
        summary: `「${a.title}」与「${b.title}」时间重叠`,
        content: `${scheduleDateLabel(a)}「${a.title}」${a.start_time}–${a.end_time} 与「${b.title}」${b.start_time}–${b.end_time} 重叠，请确认是否需要调整其中一条日程。`,
        time: '待确认',
      urgent: true,
      action: { tab: 'schedule', label: '去确认日程' },
    })
  })
  return notifications
}

function openScheduleForm(item = null) {
  const tomorrow = addDaysISO(1)
  Object.assign(scheduleForm, {
    transaction_id: '',
    title: '',
    counterpart: '',
    date: tomorrow,
    start_time: '15:00',
    end_time: '16:00',
    location: '',
    note: '',
  })
  if (item) {
    scheduleForm.transaction_id = item.id
    scheduleForm.title = item.listing_title || item.title || '互助安排'
    scheduleForm.counterpart = currentUser.value?.id === item.initiator_id
      ? (item.provider_name || '交易对方')
      : (item.initiator_name || '交易对方')
    scheduleForm.location = item.proposed_location || item.location || ''
    scheduleForm.note = item.request_note || ''
    scheduleForm.date = guessScheduleDate(item.proposed_time)
    scheduleForm.start_time = guessStartTime(item.proposed_time)
    scheduleForm.end_time = addMinutesToTime(scheduleForm.start_time, 60)
  }
  showScheduleForm.value = true
  showConflictDialog.value = false
}

function persistScheduleEntries(items) {
  if (!currentUser.value) return
  scheduleStore.value = { ...scheduleStore.value, [currentUser.value.id]: items }
  saveStoredJson(SCHEDULE_KEY, scheduleStore.value)
}

function commitSchedule(draft) {
  if (!currentUser.value) {
    showAuth.value = true
    return
  }
  const next = [...scheduleEntries.value.filter((entry) => entry.id !== draft.id), draft]
  persistScheduleEntries(next)
  showScheduleForm.value = false
  showConflictDialog.value = false
  pendingSchedule.value = null
  scheduleConflicts.value = []
  flash(draft.demo ? '示例日程已加入' : '已加入我的日程')
}

function submitScheduleForm() {
  if (!currentUser.value) {
    showAuth.value = true
    return
  }
  if (!scheduleForm.title.trim()) {
    flash('请填写日程标题', true)
    return
  }
  if (!scheduleForm.date || !scheduleForm.start_time || !scheduleForm.end_time) {
    flash('请选择日期和起止时间', true)
    return
  }
  const start = timeToMinutes(scheduleForm.start_time)
  const end = timeToMinutes(scheduleForm.end_time)
  if (start == null || end == null || end <= start) {
    flash('结束时间需要晚于开始时间', true)
    return
  }
  const draft = {
    id: `sched-${Date.now()}`,
    transaction_id: scheduleForm.transaction_id || '',
    title: scheduleForm.title.trim(),
    counterpart: scheduleForm.counterpart.trim(),
    date: scheduleForm.date,
    start_time: scheduleForm.start_time,
    end_time: scheduleForm.end_time,
    location: scheduleForm.location.trim(),
    note: scheduleForm.note.trim(),
    created_at: new Date().toISOString(),
  }
  const conflicts = findConflictsForDraft(draft, scheduleEntries.value)
  if (conflicts.length) {
    pendingSchedule.value = draft
    scheduleConflicts.value = conflicts
    showConflictDialog.value = true
    return
  }
  commitSchedule(draft)
}

function forceSchedule() {
  if (!pendingSchedule.value) return
  commitSchedule(pendingSchedule.value)
}

function closeConflictDialog() {
  showConflictDialog.value = false
  pendingSchedule.value = null
  scheduleConflicts.value = []
}

function scrollToScheduleConflict() {
  document.querySelector('.schedule-card.has-conflict')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function removeSchedule(entry) {
    if (!window.confirm(`确定移出「${entry.title}」这条日程？`)) return
  persistScheduleEntries(scheduleEntries.value.filter((item) => item.id !== entry.id))
  flash('已移出我的日程')
}

function loadDemoSchedule() {
  if (!isLoggedIn.value) {
    showAuth.value = true
    return
  }
  const demoId = `demo-schedule-${currentUser.value.id}`
  if (scheduleEntries.value.some((entry) => entry.id === demoId)) {
    flash('示例日程已经存在')
    return
  }
  persistScheduleEntries([...scheduleEntries.value, {
    id: demoId,
    transaction_id: '',
      title: '图书馆还书 + 自习',
    counterpart: '自己',
    date: addDaysISO(2),
    start_time: '15:00',
    end_time: '16:00',
      location: '海甸校区 · 图书馆北门',
      note: '这是一条用于展示提醒和冲突检测的示例日程。',
    demo: true,
    created_at: new Date().toISOString(),
  }])
  flash('示例日程已加入')
}

function openTransactionById(id) {
  const item = displayTransactions.value.find((transaction) => String(transaction.id) === String(id))
  if (!item) {
    flash('对应交易不在当前列表中', true)
    return
  }
  openTransaction(item)
}

function canScheduleTransaction(item) {
  if (!item || !currentUser.value || isAdmin.value) return false
  const participant = item.initiator_id === currentUser.value.id || item.provider_id === currentUser.value.id
  return participant && ['agreed', 'in_progress', 'provider_confirmed', 'requester_confirmed'].includes(item.status)
}

function scheduledForTransaction(id) {
  return scheduleEntries.value.find((entry) => String(entry.transaction_id) === String(id))
}

// Action buttons shown inside the transaction dialog, so a notification can be
// handled without closing the dialog and finding the row in the list.
function transactionActionsFor(item) {
  if (!item || item.demo || !currentUser.value || isAdmin.value) return []
  const me = currentUser.value.id
  const actions = []
  if (item.status === 'pending_provider' && item.provider_id === me) {
    actions.push({ key: 'reject', label: '拒绝请求', tone: 'danger' })
    actions.push({ key: 'accept', label: '接受请求', tone: 'primary' })
  }
  if (item.status === 'pending_initiator' && item.initiator_id === me) {
    actions.push({ key: 'agree', label: '确认协议', tone: 'primary' })
  }
  if (['agreed', 'in_progress', 'requester_confirmed'].includes(item.status) && item.provider_id === me && !item.provider_completed_at) {
    actions.push({ key: 'provider-complete', label: '确认已交付', tone: 'primary' })
  }
  if (['agreed', 'provider_confirmed'].includes(item.status) && item.initiator_id === me && !item.requester_completed_at) {
    actions.push({ key: 'requester-complete', label: '确认已收到', tone: 'primary' })
  }
  return actions
}

function openScheduleForTransaction(item) {
  if (scheduledForTransaction(item.id)) {
    selectedTransaction.value = null
    navigate('schedule')
    return
  }
  openScheduleForm(item)
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

function loadProfilePrefs(user) {
  const saved = user ? profilePrefsStore.value[String(user.id)] : null
  const legacy = !saved && storedProfilePrivacy && typeof storedProfilePrivacy === 'object' ? storedProfilePrivacy : null
  profilePrivacy.value = { ...defaultProfilePrivacy(), ...(saved?.privacy || legacy || {}) }
  profileBio.value = saved?.bio || ''
  profileIntroDirty.value = false
}

function saveProfilePrefs() {
  const user = currentUser.value
  if (!user) return
  profilePrefsStore.value = {
    ...profilePrefsStore.value,
    [String(user.id)]: { bio: profileBio.value, privacy: { ...profilePrivacy.value } },
  }
  saveStoredJson(PROFILE_PREFS_KEY, profilePrefsStore.value)
}

function normalizePersonalization(saved) {
  const next = { ...defaultPersonalization(), ...(saved || {}) }
  if (!Array.isArray(next.customBackgrounds)) next.customBackgrounds = []
  next.customBackgrounds = next.customBackgrounds.filter((item) => item && item.url).slice(-4)
  // Earlier builds stored a single custom background string; lift it into the picker list.
  if (saved?.customBackground && !next.customBackgrounds.length) {
    next.customBackgrounds = [{ id: 'legacy', name: '本地图片', url: saved.customBackground }]
    next.customBackgroundId = 'legacy'
    next.backgroundMode = 'custom'
  }
  if (!next.customBackgrounds.some((item) => item.id === next.customBackgroundId)) {
    next.customBackgroundId = next.customBackgrounds[0]?.id || ''
  }
  if (!['page', 'fixed', 'custom'].includes(next.backgroundMode)) next.backgroundMode = 'page'
  if (!PALETTE_OPTIONS.some((item) => item.id === next.palette)) next.palette = 'default'
  next.backgroundBlur = Math.min(24, Math.max(0, Number(next.backgroundBlur) || 0))
  next.backgroundDim = Math.min(100, Math.max(0, Number(next.backgroundDim) || 0))
  return next
}

function loadPersonalization(user) {
  const saved = user ? personalizationStore.value[String(user.id)] : null
  personalization.value = normalizePersonalization(saved)
}

function savePersonalization() {
  const user = currentUser.value
  if (!user) return
  const key = String(user.id)
  const payloadFor = (state) => ({ ...personalizationStore.value, [key]: { ...state } })
  if (saveStoredJson(PERSONALIZATION_KEY, payloadFor(personalization.value))) {
    personalizationStore.value = payloadFor(personalization.value)
    customBackgroundWarning.value = false
    return
  }
  // Local images can exceed the 5 MB storage quota: keep the theme, drop the pictures.
  const fallback = { ...personalization.value, customBackgrounds: [], customBackgroundId: '', backgroundMode: 'page' }
  if (saveStoredJson(PERSONALIZATION_KEY, payloadFor(fallback))) {
    personalizationStore.value = payloadFor(fallback)
    if (!customBackgroundWarning.value) {
      customBackgroundWarning.value = true
      flash('浏览器缓存放不下这张图，已保留配色设置；换一张小一点的图片试试', true)
    }
  }
}

const myHonors = computed(() => {
  if (!currentUser.value) return []
  const honors = []
  if (isVerified.value) honors.push('平台认证')
  if (Number(currentUser.value.credit_score) >= 105) honors.push('信用之星')
  if (transactions.value.some((item) => item.status === 'completed')) honors.push('完成互助')
  if (displayMyListings.value.length >= 3) honors.push('活跃发布')
  if (!honors.length) honors.push('初来乍到')
  return honors
})

const activeCustomBackground = computed(() => {
  const list = personalization.value.customBackgrounds || []
  return list.find((item) => item.id === personalization.value.customBackgroundId) || list[0] || null
})
const activePalette = computed(() => PALETTE_OPTIONS.find((item) => item.id === personalization.value.palette) || PALETTE_OPTIONS[0])
const activePageScene = computed(() => SCENES.find((scene) => scene.id === PAGE_SCENE[tab.value]) || SCENES[0])
const activeScene = computed(() => {
  if (personalization.value.backgroundMode === 'custom') return null
  if (personalization.value.backgroundMode === 'fixed') return SCENES.find((scene) => scene.url === personalization.value.fixedBackground) || null
  return activePageScene.value
})
const backgroundModeLabel = computed(() => ({ page: '跟随页面', fixed: '固定一张', custom: '我的图片' }[personalization.value.backgroundMode] || '跟随页面'))
const sceneDimStyle = computed(() => ({
  '--ambient-blur': `${personalization.value.backgroundBlur}px`,
  '--ambient-dim': String(personalization.value.backgroundDim),
}))
const activePageBackground = computed(() => {
  if (tab.value === 'home') return ''
  if (personalization.value.backgroundMode === 'custom') return activeCustomBackground.value?.url || ''
  if (personalization.value.backgroundMode === 'fixed' && personalization.value.fixedBackground) return personalization.value.fixedBackground
  return PAGE_BACKGROUNDS[tab.value] || PAGE_BACKGROUNDS.me
})

const myProfile = computed(() => selfProfile())
const myProfileStats = computed(() => profileStats(myProfile.value))
const myCompletedCount = computed(() => transactions.value.filter((item) => item.status === 'completed').length)

function honorMeta(name) {
  return HONOR_META[name] || { icon: 'spark', note: '' }
}

const creditGrade = computed(() => {
  const score = Number(currentUser.value?.credit_score || 0)
  if (score >= 110) return { label: '优秀', tone: 'high', percent: 100, note: '信用分在 110 以上，完成记录和双方评价都很稳定。' }
  if (score >= 100) return { label: '良好', tone: 'mid', percent: Math.min(96, Math.max(30, score - 62)), note: '信用分在 100 以上，保持按时完成和及时沟通。' }
  if (score >= 90) return { label: '正常', tone: 'low', percent: Math.max(18, score - 64), note: '还没有足够的完成记录，走完一笔互助后信用会更新。' }
  return { label: '观察中', tone: 'low', percent: Math.max(8, score - 60), note: '信用分偏低，先完成已有协议里的互助会更稳妥。' }
})

function useFixedBackground() {
  const url = activePageBackground.value || activeScene.value?.url || ''
  if (!url) return
  personalization.value = { ...personalization.value, backgroundMode: 'fixed', fixedBackground: url }
  flash('已把当前画面固定为所有页面的背景')
}

function setPalette(paletteId) {
  personalization.value = { ...personalization.value, palette: paletteId }
  flash('整体配色已更新')
}

function usePageBackground() {
  personalization.value = { ...personalization.value, backgroundMode: 'page', fixedBackground: '' }
  flash('已恢复按页面自动切换的插画背景')
}

function chooseBackground(scene) {
  personalization.value = { ...personalization.value, backgroundMode: 'fixed', fixedBackground: scene.url }
  flash(`所有页面将使用「${scene.name}」作为背景`)
}

function isSceneActive(scene) {
  return personalization.value.backgroundMode === 'fixed' && personalization.value.fixedBackground === scene.url
}

function isSceneForCurrentPage(scene) {
  return personalization.value.backgroundMode === 'page' && scene.id === PAGE_SCENE[tab.value]
}

function chooseCustomBackground(item) {
  personalization.value = { ...personalization.value, backgroundMode: 'custom', customBackgroundId: item.id }
  flash(`已使用本地图片「${item.name}」`)
}

function removeCustomBackground(item) {
  const list = personalization.value.customBackgrounds.filter((entry) => entry.id !== item.id)
  personalization.value = {
    ...personalization.value,
    customBackgrounds: list,
    customBackgroundId: list[0]?.id || '',
    backgroundMode: list.length ? personalization.value.backgroundMode : 'page',
  }
  flash('已删除这张本地背景')
}

function clearCustomBackground() {
  personalization.value = { ...personalization.value, backgroundMode: 'page', fixedBackground: '', customBackgrounds: [], customBackgroundId: '' }
  flash('已清除所有本地背景')
}

function triggerBackgroundUpload() {
  backgroundInput.value?.click()
}

function downscaleBackground(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const image = new Image()
      image.onload = () => {
        const maxSide = 1600
        const ratio = Math.min(1, maxSide / Math.max(image.width, image.height))
        const canvas = document.createElement('canvas')
        canvas.width = Math.round(image.width * ratio)
        canvas.height = Math.round(image.height * ratio)
        const context = canvas.getContext('2d')
        context.drawImage(image, 0, 0, canvas.width, canvas.height)
        try {
          resolve(canvas.toDataURL('image/jpeg', 0.78))
        } catch (err) {
          reject(err)
        }
      }
      image.onerror = () => reject(new Error('image'))
      image.src = String(reader.result)
    }
    reader.onerror = () => reject(new Error('read'))
    reader.readAsDataURL(file)
  })
}

async function addBackgroundFiles(files) {
  const picked = Array.from(files || []).filter((file) => file && String(file.type || '').startsWith('image/'))
  if (!picked.length) {
    flash('请选择 JPG、PNG 或 WebP 图片', true)
    return
  }
  const room = Math.max(0, 4 - personalization.value.customBackgrounds.length)
  if (!room) {
    flash('最多保存 4 张本地背景，先删掉一张再上传', true)
    return
  }
  const added = []
  for (const file of picked.slice(0, room)) {
    if (file.size > 12 * 1024 * 1024) {
      flash('单张图片请控制在 12MB 以内', true)
      continue
    }
    try {
      const url = await downscaleBackground(file)
      added.push({
        id: `bg-${Date.now()}-${added.length}`,
        name: String(file.name || '本地图片').replace(/\.[^.]+$/, '').slice(0, 22) || '本地图片',
        url,
      })
    } catch {
      flash('图片读取失败，请换一张试试', true)
    }
  }
  if (!added.length) return
  personalization.value = {
    ...personalization.value,
    customBackgrounds: [...personalization.value.customBackgrounds, ...added].slice(-4),
    customBackgroundId: added[0].id,
    backgroundMode: 'custom',
  }
  flash(added.length > 1 ? `已保存 ${added.length} 张本地背景` : '本地背景已保存；只保存在当前浏览器')
}

function handleBackgroundUpload(event) {
  addBackgroundFiles(event.target.files)
  event.target.value = ''
}

function handleBackgroundDrop(event) {
  backgroundDragging.value = false
  addBackgroundFiles(event.dataTransfer?.files)
}

function resetPersonalization() {
  personalization.value = defaultPersonalization()
  flash('已恢复默认配色与背景')
}

function saveProfileIntro() {
  saveProfilePrefs()
  profileIntroDirty.value = false
  flash('个人介绍已保存到本机')
}

function selfProfile() {
  if (!currentUser.value) return null
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
    bio: profileBio.value.trim() || '这是我的校园互助主页。可以在个人中心调整公开范围、介绍和展示偏好。',
    honors: myHonors.value,
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

async function loadTransactions(options = {}) {
  if (!isLoggedIn.value || isAdmin.value) return
  try {
    const previousIds = new Set(transactionNotifications.value.map((item) => item.id))
    const primed = notificationPrimedUser === currentUser.value?.id
    const { data } = await api.get('/transactions')
    transactions.value = data
    notificationPrimedUser = currentUser.value?.id ?? null
    if (primed) {
      const fresh = transactionNotifications.value.find((item) => (
        !previousIds.has(item.id)
        && !readNotificationSet.value.has(item.id)
        && !announcedNotificationIds.has(item.id)
      ))
      if (fresh) {
        announcedNotificationIds.add(fresh.id)
        flash(`新通知：${fresh.title}`)
      }
    }
  } catch (err) {
    if (!options.silent) flash(errorMessage(err, '交易记录加载失败'), true)
  }
}

// The queue has no push channel, so poll quietly while the tab is visible.
async function pollNotificationQueue() {
  if (!isLoggedIn.value || isAdmin.value) return
  if (typeof document !== 'undefined' && document.hidden) return
  await loadTransactions({ silent: true })
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
    flash(errorMessage(err, '验证码发送失败', true))
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
    flash(errorMessage(err, '操作失败，请检查输入', true))
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
  selectedListing.value = null
  selectedTransaction.value = null
  selectedNotification.value = null
  selectedProfile.value = null
  ownerBubble.value = null
  showScheduleForm.value = false
  showConflictDialog.value = false
  showReportDialog.value = false
  reportTarget.value = null
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

function isFavorited(item) {
  if (!item) return false
  return item.demo ? demoFavoriteIds.value.has(item.id) : favoriteIds.value.has(item.id)
}

async function toggleFavorite(listing) {
  if (!isLoggedIn.value) {
    showAuth.value = true
    return
  }
  if (listing.demo) {
    const userId = currentUser.value?.id
    if (!userId) return
    const current = new Set(demoFavoritesStore.value[userId] || [])
    if (current.has(listing.id)) current.delete(listing.id)
    else current.add(listing.id)
    demoFavoritesStore.value = { ...demoFavoritesStore.value, [userId]: [...current] }
    saveStoredJson(DEMO_FAVORITES_KEY, demoFavoritesStore.value)
    flash(current.has(listing.id) ? '已收藏演示帖子，可在我的收藏查看' : '已取消收藏')
    return
  }
  const wasFavorite = isFavorited(listing)
  try {
    if (wasFavorite) await api.delete('/listings/' + listing.id + '/favorite')
    else await api.post('/listings/' + listing.id + '/favorite')
    await loadFavorites()
    flash(wasFavorite ? '已取消收藏' : '已收藏，可在我的收藏查看')
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
    flash(errorMessage(err, '状态更新失败', true))
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
    flash(errorMessage(err, '消息发送失败', true))
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

function openListingReport(item) {
  if (!item) return
  if (!isLoggedIn.value) {
    pendingListing.value = item
    selectedListing.value = null
    showAuth.value = true
    return
  }
  if (isAdmin.value || currentUser.value?.id === item.owner_id) return
  reportTarget.value = item
  Object.assign(reportForm, { reason: '', description: '' })
  showReportDialog.value = true
}

function closeReportDialog() {
  showReportDialog.value = false
  reportTarget.value = null
  Object.assign(reportForm, { reason: '', description: '' })
}

function startPublishFromReport() {
  closeReportDialog()
  selectedListing.value = null
  openPublish('resource')
}

async function submitListingReport() {
  const item = reportTarget.value
  if (!item || item.demo) return
  if (reportForm.reason.trim().length < 2 || reportForm.description.trim().length < 5) {
    flash('请填写举报原因和至少 5 个字的说明', true)
    return
  }
  try {
    await api.post('/reports', {
      target_type: 'listing',
      target_id: item.id,
      reason: reportForm.reason.trim(),
      description: reportForm.description.trim(),
    })
    flash('举报已提交，管理员会核查该帖子')
    closeReportDialog()
  } catch (err) {
    flash(errorMessage(err, '举报提交失败'), true)
  }
}

async function createVerificationChallenge() {
  try {
    verificationChallenge.value = (await api.post('/auth/verification/challenge')).data
  } catch (err) {
    flash(errorMessage(err, '挑战码生成失败', true))
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
    flash(errorMessage(err, '邮箱验证码发送失败', true))
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

const availableTabs = new Set(['home', 'discover', 'me', 'settings', 'transactions', 'schedule', 'my-listings', 'favorites', 'verification', 'admin', 'profile'])

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
  if (isAdmin.value && ['me', 'settings', 'transactions', 'schedule', 'my-listings', 'favorites', 'verification', 'profile'].includes(nextTab)) nextTab = 'admin'
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
    const title = tab.value === 'discover' ? marketplaceTitle.value : ({ home: 'EXCHANGE', me: '个人中心', settings: '个人设置', transactions: '我的交易', schedule: '我的日程', 'my-listings': '我的发布', favorites: '我的收藏', verification: '学生认证', admin: '管理工作台', profile: '账号与安全' }[tab.value])
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

watch([showAuth, showPublish, selectedListing, selectedTransaction, selectedNotification, selectedProfile, showScheduleForm, showConflictDialog, showReportDialog], async (values, previous) => {
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
    if (showReportDialog.value) { closeReportDialog(); return }
    if (showConflictDialog.value) { closeConflictDialog(); return }
    if (showScheduleForm.value) { showScheduleForm.value = false; return }
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
  scheduleTicker = window.setInterval(() => { clockTick.value = Date.now() }, 60000)
  notificationTicker = window.setInterval(() => { pollNotificationQueue() }, 25000)
  window.addEventListener('focus', pollNotificationQueue)
  document.addEventListener('visibilitychange', pollNotificationQueue)
  await refreshCurrentUser()
  if (isLoggedIn.value && !isAdmin.value) {
    await Promise.all([loadTransactions(), loadMyListings(), loadFavorites()])
  }
  await Promise.all([loadCategories(), loadListings()])
  readLocation()
  document.title = `${tab.value === 'home' ? 'EXCHANGE' : document.title.split(' · ')[0]} · 海大互助`
})

onBeforeUnmount(() => {
  window.clearInterval(smsTimer)
  window.clearInterval(emailTimer)
  window.clearInterval(scheduleTicker)
  window.clearInterval(notificationTicker)
  window.clearTimeout(personalizationSaveTimer)
  window.removeEventListener('focus', pollNotificationQueue)
  document.removeEventListener('visibilitychange', pollNotificationQueue)
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
  <div class="app-shell" :class="{ 'is-home': tab === 'home', 'is-plaza': tab === 'discover', 'has-ambient': tab !== 'home' && activePageBackground }" :data-palette="personalization.palette">
    <a href="#page-content" class="skip-link" @click.prevent="skipToContent">跳到主要内容</a>
    <div v-if="tab !== 'home' && activePageBackground" class="page-ambient" :style="sceneDimStyle" aria-hidden="true">
      <div class="page-ambient-image" :style="{ backgroundImage: `url('${activePageBackground}')` }"></div>
      <div class="page-ambient-overlay"></div>
      <div class="page-ambient-grain"></div>
    </div>
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
          <button class="notification-bell" :class="{ 'has-unread': unreadNotificationCount, 'has-urgent': hasUrgentNotification }" :aria-label="unreadNotificationCount ? `通知中心 ${unreadNotificationCount} 条未读` : '通知中心'" :aria-expanded="notificationPanelOpen" aria-controls="notification-panel" @click="toggleNotifications">
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
              <span v-if="hasUrgentNotification" class="notification-summary-urgent">含待处理交易</span>
              <span v-else>{{ realNotifications.length ? '交易提醒与服务器同步' : '内含审核、交易与留言动态' }}</span>
            </div>
            <div class="notification-list">
              <template v-for="(item, index) in allNotifications" :key="item.id">
                <p v-if="index === 0 || allNotifications[index - 1].group !== item.group" class="notification-group-label">
                  {{ item.group === 'demo' ? '内置演示通知' : '交易与日程' }}
                  <span v-if="item.group !== 'demo' && realUnreadCount">{{ realUnreadCount }} 条新</span>
                  <em v-if="item.group === 'demo'">演示</em>
                </p>
                <button class="notification-item" :class="{ 'is-unread': !readNotificationSet.has(item.id), 'is-urgent': item.urgent }" @click="openNotification(item)">
                  <span class="notification-icon" :class="'is-' + item.type"><AppIcon :name="item.icon" /></span>
                  <span class="notification-copy">
                    <span class="notification-line"><b>{{ item.title }}</b><em v-if="item.urgent" class="notification-urgent">紧急</em><time>{{ item.time }}</time></span>
                    <small>{{ item.summary }}</small>
                    <span class="notification-type">{{ item.typeLabel }}</span>
                  </span>
                  <i v-if="!readNotificationSet.has(item.id)" class="notification-unread-dot" aria-label="未读"></i>
                </button>
              </template>
            </div>
            <footer class="notification-panel-foot"><AppIcon name="bell" /><span>交易提醒来自服务器（每 25 秒同步一次）；日程提醒保存在本机浏览器</span></footer>
          </section>
        </div>
        <div v-if="isLoggedIn" class="account-menu-wrap">
          <button class="account-button" aria-label="打开账号菜单" :aria-expanded="accountMenuOpen" aria-controls="account-navigation" @click="accountMenuOpen = !accountMenuOpen; notificationPanelOpen = false; mobileMenuOpen = false">
            <span class="avatar">{{ currentUser.name.slice(0, 1) }}</span><b>{{ currentUser.name }}</b><AppIcon name="chevron" />
          </button>
          <nav v-if="accountMenuOpen" id="account-navigation" class="account-menu" aria-label="账号导航">
            <small>{{ currentUser.account_masked }}</small>
            <button v-if="!isAdmin" :class="{ active: tab === 'me' }" @click="navigate('me')"><AppIcon name="user" />个人中心</button>
            <button v-if="!isAdmin" :class="{ active: tab === 'settings' }" @click="navigate('settings')"><AppIcon name="spark" />个人设置</button>
            <button v-if="!isAdmin" :class="{ active: tab === 'profile' }" @click="navigate('profile')"><AppIcon name="shield" />账号与安全</button>
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
                  <span>资源置换</span><i>✦</i><span>技能互助</span><i>✦</i><span>校内当面交易</span><i>✦</i><span>平台不托管资金</span><i>✦</i><span>让闲置重新流转</span><i>✦</i>
                </div>
                <div class="plaza-marquee-group">
                  <span>资源置换</span><i>✦</i><span>技能互助</span><i>✦</i><span>校内当面交易</span><i>✦</i><span>平台不托管资金</span><i>✦</i><span>让闲置重新流转</span><i>✦</i>
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
                <button :class="{ active: listingType === 'skill' }" :aria-current="listingType === 'skill' ? 'page' : undefined" @click="openMarketplace('skill')">技能互助<b v-if="demoMode">{{ catalogCounts.skill }}</b></button>
              </nav>
              <button v-if="!isAdmin" class="plaza-publish" @click="openPublish(listingType === 'skill' ? 'skill' : 'resource')"><AppIcon name="plus" />发布一条</button>
            </div>
            <div class="plaza-search-row">
              <label class="plaza-search"><AppIcon name="search" /><input aria-label="搜索资源与技能" v-model="filters.keyword" placeholder="搜索教材、设备、辅导或技能" @keyup.enter="loadListings" /><kbd>ENTER</kbd></label>
              <label class="plaza-select"><span>分类</span><select v-model="filters.category_id" aria-label="分类" @change="loadListings"><option value="">全部分类</option><option v-for="item in categories.filter(item => listingType === 'all' || item.listing_type === 'both' || item.listing_type === listingType)" :key="item.id" :value="item.id">{{ item.name }}</option></select><AppIcon name="chevron" /></label>
              <label class="plaza-select"><span>排序</span><select v-model="sortMode" aria-label="排序方式"><option value="latest">最新发布</option><option value="credit">信用优先</option><option value="views">浏览最多</option></select><AppIcon name="chevron" /></label>
              <button class="plaza-search-btn" @click="loadListings">搜索 <span aria-hidden="true">⌕</span></button>
            </div>
            <div class="plaza-chips">
              <span class="plaza-chips-label">场景</span>
              <button v-for="scene in marketplaceScenePresets" :key="scene.id" class="plaza-chip" :class="{ 'is-active': sceneFilter === scene.id }" @click="applyScene(scene)">{{ scene.label }}</button>
              <button class="plaza-chip plaza-free" :class="{ 'is-active': sceneFilter === 'free' }" @click="applyScene({ id: 'free', keyword: '', category: '' })"><span aria-hidden="true">可</span> 免费互助</button>
              <button class="plaza-more-filters" :class="{ 'is-active': advancedFiltersOpen || advancedFilterCount }" :aria-expanded="advancedFiltersOpen" aria-controls="plaza-advanced-filters" @click="advancedFiltersOpen = !advancedFiltersOpen">
                <AppIcon name="filter" /> 更多筛选<b v-if="advancedFilterCount">{{ advancedFilterCount }}</b><AppIcon name="chevron" />
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
                    <div><input v-model="filters.min_price" type="number" min="0" step="1" inputmode="numeric" aria-label="最低价格" placeholder="最低" /><span>–</span><input v-model="filters.max_price" type="number" min="0" step="1" inputmode="numeric" aria-label="最高价格" placeholder="最高" /></div>
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
            <span><AppIcon :name="activeSeasonTheme.icon" /> 正在查看「{{ activeSeasonTheme.title }}</span>
            <b>{{ seasonalCount(activeSeasonTheme.id) }} 条示例</b>
            <button @click="clearSeason">返回全部互助</button>
          </div>
          <div v-if="demoMode" class="plaza-demo">
            <span class="plaza-demo-tag">设计示例</span>
            <p>当前内容用于预览界面，登录后可收藏到“我的收藏”（演示收藏只保存在本机），但不能发起交易请求。</p>
            <template v-if="listingsError"> 服务暂时未连接，请重试连接</template>
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
              <div class="plaza-lane-grid">
                <article v-for="(item, index) in resourceListings" :key="item.id" class="swap-card swap-card--uniform" data-reveal :style="{ '--rv-delay': (index > 8 ? 8 : index) * 50 + 'ms' }">
                  <div class="swap-media" role="button" tabindex="0" :aria-label="`查看${item.title}详情`" @click="openListing(item)" @keydown.enter="openListing(item)" @keydown.space.prevent="openListing(item)">
                    <div class="swap-poster" :class="posterTone(item)" aria-hidden="true">
                      <span class="swap-poster-glyph">{{ posterGlyph(item) }}</span>
                      <span class="swap-poster-label">{{ item.category_name || typeLabel(item.type) }}</span>
                    </div>
                    <img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" @error="$event.target.remove()" />
                    <span v-if="isFeatured(item)" class="swap-featured-flag">精华</span>
                    <button v-if="isLoggedIn && !isAdmin" class="swap-fav" :class="{ 'is-saved': isFavorited(item) }" :aria-label="isFavorited(item) ? '取消收藏' : '收藏'" @click.stop="toggleFavorite(item)" @keydown.stop>{{ isFavorited(item) ? '★' : '☆' }}</button>
                    <span class="swap-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}<small v-if="item.price">/ {{ item.price_unit }}</small></span>
                    <span class="swap-media-hint">查看详情 <AppIcon name="arrow" /></span>
                  </div>
                  <div class="swap-content">
                    <p class="swap-kicker"><span>{{ item.category_name || typeLabel(item.type) }}</span><span v-if="isFreeListing(item)" class="swap-free">免费</span><span v-if="item.demo" class="swap-demo">示例</span><span v-if="hasListingStory(item)" class="swap-story-flag">有故事</span><time v-if="!item.demo">{{ listingTime(item.created_at) }}</time></p>
                    <h3>{{ item.title }}</h3>
                    <p class="swap-desc">{{ item.description }}</p>
                    <div class="swap-foot">
                      <span class="swap-owner">
                        <span class="swap-location">{{ listingPlace(item) }}</span>
                        <button class="owner-chip" :aria-label="`查看${item.owner_name || '发布者'}的主页`" @click.stop="openOwnerBubble(item, $event)">
                          <span class="owner-avatar">{{ ownerInitial(item) }}</span><span>{{ item.owner_name || '校园用户' }}</span><span v-if="ownerVerified(item)" class="owner-verified" aria-label="平台认证">✓</span>
                        </button>
                      </span>
                      <span class="swap-views"><AppIcon name="eye" />{{ listingViewText(item) }}</span>
                      <span class="swap-credit"><b>★</b>{{ listingCreditLabel(item) }}</span>
                    </div>
                    <button class="swap-detail-btn" @click.stop="openListing(item)">查看详情 <AppIcon name="arrow" /></button>
                  </div>
                </article>
              </div>
            </section>

            <section v-if="listingType !== 'resource'" class="plaza-lane plaza-lane--skill">
              <header class="plaza-lane-head" data-reveal>
                <span class="plaza-lane-no" aria-hidden="true">02</span>
                <div class="plaza-lane-title"><h2>技能互助<small>SKILL</small></h2><p>把擅长的事变成一次帮助</p></div>
                <span class="plaza-lane-count">{{ skillListings.length.toString().padStart(2, '0') }}</span>
                <button v-if="!isAdmin" class="plaza-lane-add" aria-label="发布技能" @click="openPublish('skill')"><AppIcon name="plus" /></button>
              </header>
              <div v-if="!skillListings.length" class="plaza-empty" data-reveal>
                <b>暂无匹配技能</b><span>学习辅导、设计协助和技术支持会显示在这里。</span>
              </div>
              <div class="plaza-lane-grid">
                <article v-for="(item, index) in skillListings" :key="item.id" class="swap-card swap-card--uniform" data-reveal :style="{ '--rv-delay': (index > 8 ? 8 : index) * 50 + 'ms' }">
                  <div class="swap-media" role="button" tabindex="0" :aria-label="`查看${item.title}详情`" @click="openListing(item)" @keydown.enter="openListing(item)" @keydown.space.prevent="openListing(item)">
                    <div class="swap-poster" :class="posterTone(item)" aria-hidden="true">
                      <span class="swap-poster-glyph">{{ posterGlyph(item) }}</span>
                      <span class="swap-poster-label">{{ item.category_name || typeLabel(item.type) }}</span>
                    </div>
                    <img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" @error="$event.target.remove()" />
                    <span v-if="isFeatured(item)" class="swap-featured-flag">精华</span>
                    <button v-if="isLoggedIn && !isAdmin" class="swap-fav" :class="{ 'is-saved': isFavorited(item) }" :aria-label="isFavorited(item) ? '取消收藏' : '收藏'" @click.stop="toggleFavorite(item)" @keydown.stop>{{ isFavorited(item) ? '★' : '☆' }}</button>
                    <span class="swap-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}<small v-if="item.price">/ {{ item.price_unit }}</small></span>
                    <span class="swap-media-hint">查看详情 <AppIcon name="arrow" /></span>
                  </div>
                  <div class="swap-content">
                    <p class="swap-kicker"><span>{{ item.category_name || typeLabel(item.type) }}</span><span v-if="isFreeListing(item)" class="swap-free">免费</span><span v-if="item.demo" class="swap-demo">示例</span><span v-if="hasListingStory(item)" class="swap-story-flag">有故事</span><time v-if="!item.demo">{{ listingTime(item.created_at) }}</time></p>
                    <h3>{{ item.title }}</h3>
                    <p class="swap-desc">{{ item.description }}</p>
                    <div class="swap-foot">
                      <span class="swap-owner">
                        <span class="swap-location">{{ listingPlace(item) }}</span>
                        <button class="owner-chip" :aria-label="`查看${item.owner_name || '发布者'}的主页`" @click.stop="openOwnerBubble(item, $event)">
                          <span class="owner-avatar">{{ ownerInitial(item) }}</span><span>{{ item.owner_name || '校园用户' }}</span><span v-if="ownerVerified(item)" class="owner-verified" aria-label="平台认证">✓</span>
                        </button>
                      </span>
                      <span class="swap-views"><AppIcon name="eye" />{{ listingViewText(item) }}</span>
                      <span class="swap-credit"><b>★</b>{{ listingCreditLabel(item) }}</span>
                    </div>
                    <button class="swap-detail-btn" @click.stop="openListing(item)">查看详情 <AppIcon name="arrow" /></button>
                  </div>
                </article>
              </div>
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
          <div v-else-if="isLoggedIn && !filteredTransactions.length" class="state-panel"><strong>没有符合当前条件的交易</strong><span>尝试切换角色或状态筛选条件</span></div>
          <div v-else-if="isLoggedIn" class="transaction-list">
            <article v-for="item in filteredTransactions" :key="item.id" class="transaction-card" :class="{ 'is-demo-row': item.demo }">
              <div class="transaction-head"><div><span class="record-id">TRANSACTION / {{ item.id }} <span v-if="item.demo" class="demo-label">演示</span></span><h2>{{ item.listing_title }}</h2></div><span class="status-pill">{{ statusLabel(item.status) }}</span></div>
              <div class="agreement-row"><span>¥ {{ item.agreed_price || item.proposed_price }}</span><span>{{ item.proposed_time || '时间待协商' }}</span><span>{{ item.proposed_location || '地点待协商' }}</span></div>
              <p>{{ item.request_note }}</p>
              <p v-if="item.demo" class="transaction-counterparty">对方：{{ item.provider_name }} · 这条交易对应通知中心的“紧急交易”。</p>
              <p v-if="item.demo_payment_status === 'simulated_paid'" class="demo-payment-line">课程演示付款已记录，不代表真实资金支付</p>
              <div class="transaction-actions">
                <button class="outline-btn" @click="openTransaction(item)">消息与协议</button>
                <button v-if="canScheduleTransaction(item)" class="outline-btn schedule-btn" @click="openScheduleForTransaction(item)">{{ scheduledForTransaction(item.id) ? '已加入日程' : '加入我的日程' }}</button>
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

        <section v-else-if="tab === 'schedule'" class="page narrow-page schedule-page">
          <header class="page-heading"><div><h1>我的日程</h1><p>把已经确认的互助安排放进日程；临近日期会在通知铃铛提醒，时间重叠会先请你确认协议。</p></div><button class="primary-btn" @click="openScheduleForm()">先新增日程</button></header>
          <div v-if="!isLoggedIn" class="state-panel"><strong>登录后使用我的日程</strong><span>日程与提醒只对当前账号展示。</span><button class="primary-btn" @click="showAuth = true">登录 / 注册</button></div>
          <template v-else>
            <div v-if="scheduleConflictGroups.length" class="schedule-conflict-banner">
              <AppIcon name="clock" />
              <div><b>检测到 {{ scheduleConflictGroups.length }} 组日程时间冲突</b><span>请确认是否调整其中一条，避免同一时间安排两件事</span></div>
              <button @click="scrollToScheduleConflict">查看冲突</button>
            </div>
            <div class="schedule-summary">
              <div><span>待进行</span><b>{{ upcomingScheduleCount }}</b><small>条日程</small></div>
              <div><span>今天</span><b>{{ todayScheduleCount }}</b><small>条安排</small></div>
              <div><span>冲突</span><b>{{ scheduleConflictGroups.length }}</b><small>组时间重叠</small></div>
              <div><span>提醒</span><b>3</b><small>天内进入铃铛</small></div>
            </div>
            <div class="schedule-layout">
              <div class="schedule-main">
                <div v-if="!scheduleEntries.length" class="state-panel schedule-empty">
                  <strong>还没有日程</strong>
                  <span>先在“我的交易”确认协议，再把约定时间加入日程；也可以先新增一条手动日程。</span>
                  <div class="schedule-empty-actions">
                    <button class="primary-btn" @click="navigate('transactions')">去我的交易</button>
                    <button class="outline-btn" @click="loadDemoSchedule">载入一条示例日程</button>
                  </div>
                </div>
                <div v-else class="schedule-list">
                  <article v-for="entry in scheduleEntries" :key="entry.id" class="schedule-card" :class="{ 'has-conflict': scheduleConflictIds.has(entry.id), 'is-past': entry.date < todayISO() }">
                    <div class="schedule-date"><b>{{ scheduleDayNumber(entry.date) }}</b><span>{{ scheduleMonth(entry.date) }}</span></div>
                    <div class="schedule-body">
                      <div class="schedule-card-head">
                        <span class="schedule-time">{{ entry.start_time }}–{{ entry.end_time }}</span>
                        <span class="schedule-status" :class="{ today: entry.date === todayISO(), past: entry.date < todayISO() }">{{ scheduleStatusLabel(entry) }}</span>
                        <span v-if="scheduleConflictIds.has(entry.id)" class="conflict-chip">时间冲突</span>
                        <span v-if="entry.demo" class="demo-label">示例</span>
                      </div>
                      <h2>{{ entry.title }}</h2>
                      <p class="schedule-meta"><AppIcon name="pin" />{{ entry.location || '地点待定' }}<span v-if="entry.counterpart"> · {{ entry.counterpart }}</span></p>
                      <p v-if="entry.note" class="schedule-note">{{ entry.note }}</p>
                      <div class="schedule-actions">
                        <button v-if="entry.transaction_id" class="outline-btn" @click="openTransactionById(entry.transaction_id)">查看交易</button>
                        <button class="ghost-btn danger" @click="removeSchedule(entry)">移出日程</button>
                      </div>
                    </div>
                  </article>
                </div>
              </div>
              <aside class="schedule-map">
                <div class="schedule-map-head"><span class="seasonal-kicker">CAMPUS MAP · HAIDIAN</span><h2>校园地图</h2><p>面交优先选图书馆、食堂、教学楼大厅等公共区域。</p></div>
                <a class="schedule-map-image" href="/exchange/campus-map.jpg" target="_blank" rel="noopener">
                  <img src="/exchange/campus-map.jpg" alt="海南大学海甸校区手绘校园地图" loading="lazy" />
                </a>
                <div class="schedule-map-spots"><span>图书馆北门</span><span>二食堂门口</span><span>东坡湖旁</span></div>
                <a class="schedule-map-link" href="/exchange/campus-map.jpg" target="_blank" rel="noopener">查看完整地图 <AppIcon name="arrow" /></a>
              </aside>
            </div>
            <p class="schedule-local-note">日程和提醒保存在本机浏览器，用于课程演示；后续可接真实日程表与提醒服务。</p>
          </template>
        </section>

        <section v-else-if="tab === 'my-listings'" class="page narrow-page">
          <header class="page-heading"><div><h1>我的发布</h1><p>分别管理资源和技能，上下架不会改变已经达成的交易。</p></div><button class="primary-btn" @click="openPublish('resource')">最新发布</button></header>
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
          <header class="page-heading"><div><h1>我的收藏</h1><p>真实帖子收藏会同步到账号；演示帖子收藏只保存在本机浏览器</p></div><button class="outline-btn" @click="loadFavorites">刷新</button></header>
          <div v-if="!isLoggedIn" class="state-panel"><strong>登录后才能使用收藏</strong><button class="primary-btn" @click="showAuth = true">登录 / 注册</button></div>
          <template v-else>
            <div v-if="displayFavoriteListings.length" class="favorites-summary"><span>共收藏<b>{{ displayFavoriteListings.length }}</b> </span><span v-if="demoFavoriteIds.size">"{{ demoFavoriteIds.size }} 条本机演示收藏</span></div>
            <div v-if="!displayFavoriteListings.length" class="state-panel"><strong>暂时没有收藏</strong><span>登录后在广场卡片或详情页点星标，收藏会集中显示在这里。</span><button class="primary-btn" @click="navigate('discover')">去双轨广场</button></div>
            <div v-else class="management-list">
              <article v-for="item in displayFavoriteListings" :key="item.id" class="management-row" :class="{ 'is-demo-row': item.demo }">
                <div class="item-media" :class="item.type"><img loading="lazy" decoding="async" v-if="item.image_urls?.length" :src="mediaUrl(item.image_urls[0])" :alt="item.title" /><span v-else>{{ item.type === 'skill' ? '技能' : '资源' }}</span></div>
                <div class="admin-info"><strong>{{ item.title }}</strong><span>{{ typeLabel(item.type) }} · {{ item.owner_name }} · <b :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}</b><span v-if="item.demo" class="demo-label">演示收藏</span></span><small><span class="credit-score"><b>★</b>{{ listingCreditLabel(item) }}</span> · {{ item.location || '校内协商' }}</small></div>
                <div class="admin-actions"><button class="outline-btn" @click="openListing(item)">查看详情 <AppIcon name="arrow" /></button><button class="save-detail saved" aria-label="取消收藏" @click="toggleFavorite(item)">★</button></div>
              </article>
            </div>
          </template>
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
                <div class="verification-step complete"><span>01</span><div><b>手机号已验证</b><p>{{ currentUser.account_masked }} 仅证明该号码由你控制，不是学生身份证明</p></div></div>
                <div class="verification-step" :class="{ complete: isVerified, active: !isVerified }"><span>02</span><div><b>提交学生材料</b><p>学生证或海大 e 卡信息需与一次性挑战码出现在同一画面。</p></div></div>
                <div class="verification-step" :class="{ complete: isVerified }"><span>03</span><div><b>管理员人工审核</b><p>通过后显示“平台人工认证”，不代表学校官方背书。</p></div></div>
              </aside>
              <section class="verification-panel">
                <div v-if="isVerified" class="verification-result success"><b>{{ currentUser.verification_method === 'demo' ? '课程演示认证已通过' : '学生身份已通过平台人工认证' }}</b><p>{{ currentUser.verification_method === 'demo' ? '该状态仅用于展示课程项目完整流程，不是官方学生身份证明' : '现在可以发布资源或技能，并发起交易请求' }}</p></div>
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

        <AdminWorkspace v-else-if="tab === 'admin'" @toast="flash" />

        <section v-else-if="tab === 'me' && isLoggedIn" class="page narrow-page me-page">
          <header class="page-heading me-heading">
            <div><p class="me-eyebrow">PERSONAL CENTER</p><h1>个人中心</h1><p>公开主页、勋章、信誉和介绍集中在这里；配色与背景在个人设置里调整。</p></div>
            <div class="me-heading-actions">
              <button class="outline-btn" @click="openSelfProfile">预览公开主页</button>
              <button class="primary-btn" @click="navigate('settings')"><AppIcon name="spark" />个人设置</button>
            </div>
          </header>

          <div class="me-hero">
            <div class="me-avatar">{{ currentUser.name.slice(0, 1) }}</div>
            <div class="me-identity">
              <div class="me-name-line"><h2>{{ currentUser.name }}</h2><span v-if="isVerified" class="me-verified">✓ 已认证</span><span v-else class="demo-label">{{ verificationLabel(currentUser.verification_status) }}</span></div>
              <p class="me-handle">@me<span v-if="currentUser.college"> · {{ currentUser.college }}</span><span v-if="currentUser.grade"> · {{ currentUser.grade }}</span></p>
              <p class="me-bio">{{ profileBio.trim() || '还没有写个人介绍，可以从下方开始。' }}</p>
              <div class="me-hero-actions"><button class="outline-btn" @click="openSelfProfile">公开主页预览</button><button class="ghost-btn" @click="navigate('my-listings')">管理我的发布</button><button class="ghost-btn" @click="navigate('schedule')">我的日程</button></div>
            </div>
            <div class="me-credit"><span>信用分</span><strong>{{ currentUser.credit_score }}</strong><small>{{ creditGrade.label }} · {{ verificationLabel(currentUser.verification_status) }}</small></div>
          </div>

          <div class="me-stats">
            <div><span>发布帖子</span><strong>{{ myProfileStats.posts }}</strong></div>
            <div><span>全部浏览</span><strong>{{ myProfileStats.totalViews.toLocaleString('zh-CN') }}</strong></div>
            <div><span>完成互助</span><strong>{{ myCompletedCount }}</strong></div>
            <div><span>公开勋章</span><strong>{{ myHonors.length }}</strong></div>
          </div>

          <div class="me-layout">
            <div class="me-main">
              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">HONOR WALL</p><h2>我的勋章</h2></div><span>{{ myHonors.length }} 枚</span></div>
                <div class="honor-grid">
                  <div v-for="(honor, index) in myHonors" :key="honor" class="honor-card" :class="'tone-' + (index % 4)">
                    <span class="honor-card-icon"><AppIcon :name="honorMeta(honor).icon" /></span>
                    <div><b>{{ honor }}</b><small>{{ honorMeta(honor).note }}</small></div>
                  </div>
                </div>
                <p class="me-card-note">勋章由认证状态、信用分和互助记录自动生成；关闭“我的勋章”后，别人只能看到你的基础资料。</p>
              </section>

              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">ABOUT ME</p><h2>我的个人介绍</h2></div><span>{{ profileBio.length }} / 240</span></div>
                <textarea v-model="profileBio" class="me-intro-input" maxlength="240" rows="4" placeholder="写几句你愿意让同学了解的话，例如擅长什么、想交换什么、常出没的校区。" @input="profileIntroDirty = true"></textarea>
                <div class="me-card-foot"><span>{{ profileIntroDirty ? '有未保存的修改' : '自动保存在当前浏览器' }}</span><button class="primary-btn" @click="saveProfileIntro">保存介绍</button></div>
              </section>

              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">VISIBILITY</p><h2>我想要隐藏的信息</h2></div><span>公开主页同步生效</span></div>
                <div class="privacy-grid me-privacy-grid">
                  <label><input v-model="profilePrivacy.showCollege" type="checkbox" /><span>学院与年级</span></label>
                  <label><input v-model="profilePrivacy.showStats" type="checkbox" /><span>信用分与总浏览量</span></label>
                  <label><input v-model="profilePrivacy.showPosts" type="checkbox" /><span>发布过的帖子</span></label>
                  <label><input v-model="profilePrivacy.showHonors" type="checkbox" /><span>我的勋章</span></label>
                </div>
                <p class="me-card-note">学号、手机号、邮箱和认证材料始终不会出现在公开主页。关闭后，帖子气泡和个人主页会同步隐藏。</p>
              </section>

              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">MY LISTINGS</p><h2>我的发布</h2></div><button class="text-btn" @click="navigate('my-listings')">管理全部 <AppIcon name="arrow" /></button></div>
                <div v-if="displayMyListings.length" class="me-listing-list">
                  <button v-for="item in displayMyListings.slice(0, 4)" :key="item.id" class="profile-listing-row" @click="openListing(item)">
                    <span class="profile-listing-type" :class="item.type">{{ item.type === 'skill' ? '技' : '物' }}</span>
                    <span class="profile-listing-copy"><b>{{ item.title }}</b><small>{{ typeLabel(item.type) }} · {{ listingStatusLabel(item.status) }}</small></span>
                    <span class="profile-listing-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}</span>
                    <AppIcon name="arrow" />
                  </button>
                </div>
                <p v-else class="profile-empty-line">还没有发布内容。去广场发布第一条互助吧</p>
              </section>
            </div>

            <aside class="me-aside">
              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">MY REPUTATION</p><h2>我的信誉</h2></div><span class="credit-grade" :class="'is-' + creditGrade.tone">{{ creditGrade.label }}</span></div>
                <div class="me-reputation">
                  <div><span>信用分</span><b>{{ currentUser.credit_score }}</b></div>
                  <div><span>完成互助</span><b>{{ myCompletedCount }}</b></div>
                  <div><span>认证状态</span><b>{{ verificationLabel(currentUser.verification_status) }}</b></div>
                  <div><span>学院</span><b>{{ currentUser.college || '学院未填写' }}</b></div>
                </div>
                <div class="credit-track" :style="{ '--credit': creditGrade.percent + '%' }"><i></i></div>
                <p class="me-card-note">{{ creditGrade.note }}信用分由完成记录和平台信用事件形成，异常处理会留下管理员日志。</p>
              </section>

              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">APPEARANCE</p><h2>配色与背景</h2></div><span>{{ activePalette.name }}</span></div>
                <div class="me-theme-preview">
                  <img v-if="activePageBackground" :src="activePageBackground" alt="当前页面背景预览" loading="lazy" />
                  <span class="me-theme-swatches"><i v-for="color in activePalette.colors" :key="color" :style="{ background: color }"></i></span>
                </div>
                <p class="me-card-note">{{ activeScene ? `当前背景：${activeScene.name} · 景深 ${personalization.backgroundBlur}px` : '当前使用你自己上传的图片作为背景' }}</p>
                <button class="outline-btn wide-btn" @click="navigate('settings')">调整整体配色与背景</button>
              </section>

              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">SHORTCUTS</p><h2>快捷入口</h2></div></div>
                <div class="me-shortcuts">
                  <button @click="navigate('transactions')"><AppIcon name="exchange" /><span>我的交易</span><b>{{ displayTransactions.length }}</b></button>
                  <button @click="navigate('favorites')"><AppIcon name="heart" /><span>我的收藏</span><b>{{ displayFavoriteListings.length }}</b></button>
                  <button @click="navigate('verification')"><AppIcon name="shield" /><span>学生认证</span><b>{{ verificationLabel(currentUser.verification_status) }}</b></button>
                  <button @click="navigate('profile')"><AppIcon name="user" /><span>账号与安全</span><b>手机 / 邮箱</b></button>
                </div>
              </section>
            </aside>
          </div>
        </section>

        <section v-else-if="tab === 'settings' && isLoggedIn" class="page narrow-page settings-page">
          <header class="page-heading me-heading">
            <div><p class="me-eyebrow">PERSONAL SETTINGS</p><h1>个人设置</h1><p>整体配色、页面插画背景、景深模糊和公开范围都只保存在当前浏览器。</p></div>
            <button class="outline-btn" @click="navigate('me')">返回个人中心</button>
          </header>

          <div class="settings-layout">
            <div class="settings-main">
              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">PALETTE</p><h2>整体配色</h2></div><span>{{ activePalette.name }}</span></div>
                <div class="palette-grid">
                  <button v-for="palette in PALETTE_OPTIONS" :key="palette.id" class="palette-card" :class="{ active: personalization.palette === palette.id }" @click="setPalette(palette.id)">
                    <span class="palette-strip"><i v-for="color in palette.colors" :key="color" :style="{ background: color }"></i></span>
                    <b>{{ palette.name }}</b>
                    <small>{{ palette.note }}</small>
                    <em v-if="personalization.palette === palette.id">使用中</em>
                  </button>
                </div>
                <p class="me-card-note">配色会同时影响按钮、标签、卡片底色和背景蒙层，切换后立即生效。</p>
              </section>

              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">BACKGROUND</p><h2>页面背景</h2></div><span>{{ backgroundModeLabel }}</span></div>
                <div class="segmented settings-segmented">
                  <button :class="{ selected: personalization.backgroundMode === 'page' }" @click="usePageBackground">跟随页面</button>
                  <button :class="{ selected: personalization.backgroundMode === 'fixed' }" @click="useFixedBackground">固定一张</button>
                  <button :class="{ selected: personalization.backgroundMode === 'custom' }" :disabled="!personalization.customBackgrounds.length" @click="personalization.backgroundMode = 'custom'">我的图片</button>
                </div>

                <div class="scene-grid">
                  <button v-for="scene in SCENES" :key="scene.id" class="scene-card" :class="{ active: isSceneActive(scene), 'is-page': isSceneForCurrentPage(scene) }" @click="chooseBackground(scene)">
                    <img :src="scene.thumb" :alt="scene.name" loading="lazy" />
                    <span>{{ scene.name }}</span>
                    <small>{{ scene.note }}</small>
                  </button>
                </div>
                <p class="me-card-note">六张校园水彩插画已经做过景深处理，作为背景时不会抢走内容注意力；点任意一张可固定到所有页面。</p>

                <div
                  class="upload-zone"
                  :class="{ 'is-dragging': backgroundDragging }"
                  role="button"
                  tabindex="0"
                  @click="triggerBackgroundUpload"
                  @keydown.enter.prevent="triggerBackgroundUpload"
                  @keydown.space.prevent="triggerBackgroundUpload"
                  @dragover.prevent="backgroundDragging = true"
                  @dragleave.prevent="backgroundDragging = false"
                  @drop.prevent="handleBackgroundDrop"
                >
                  <span class="upload-zone-icon"><AppIcon name="plus" /></span>
                  <b>上传本地图片当背景</b>
                  <span>点击选择或把图片拖到这里 · JPG / PNG / WebP · 单张 12MB 以内 · 最多 4 张</span>
                  <input ref="backgroundInput" class="me-bg-file" type="file" multiple accept="image/jpeg,image/png,image/webp" @change="handleBackgroundUpload" />
                </div>

                <div v-if="personalization.customBackgrounds.length" class="my-backgrounds">
                  <article v-for="item in personalization.customBackgrounds" :key="item.id" class="my-background" :class="{ active: personalization.backgroundMode === 'custom' && personalization.customBackgroundId === item.id }">
                    <button class="my-background-pick" @click="chooseCustomBackground(item)">
                      <img :src="item.url" :alt="item.name" />
                      <span>{{ item.name }}</span>
                    </button>
                    <button class="my-background-remove" :aria-label="`删除本地背景 ${item.name}`" @click.stop="removeCustomBackground(item)">×</button>
                    <em v-if="personalization.backgroundMode === 'custom' && personalization.customBackgroundId === item.id">使用中</em>
                  </article>
                  <button class="text-btn my-background-clear" @click="clearCustomBackground">清除全部本地背景</button>
                </div>

                <div class="settings-sliders">
                  <label class="me-blur">景深模糊 <b>{{ personalization.backgroundBlur }}px</b><input v-model.number="personalization.backgroundBlur" type="range" min="0" max="16" step="1" /></label>
                  <label class="me-blur">蒙层浓度 <b>{{ personalization.backgroundDim }}%</b><input v-model.number="personalization.backgroundDim" type="range" min="10" max="100" step="2" /></label>
                </div>
                <p class="me-card-note">蒙层越浓，背景越淡，文字越清晰；插画背景默认保留了适当的模糊和留白。</p>
              </section>
            </div>

            <aside class="settings-aside">
              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">VISIBILITY</p><h2>公开范围</h2></div><span>公开主页</span></div>
                <div class="privacy-grid me-privacy-grid">
                  <label><input v-model="profilePrivacy.showCollege" type="checkbox" /><span>学院与年级</span></label>
                  <label><input v-model="profilePrivacy.showStats" type="checkbox" /><span>信用分与总浏览量</span></label>
                  <label><input v-model="profilePrivacy.showPosts" type="checkbox" /><span>发布过的帖子</span></label>
                  <label><input v-model="profilePrivacy.showHonors" type="checkbox" /><span>我的勋章</span></label>
                </div>
                <p class="me-card-note">学号、手机号、邮箱和认证材料不会出现在公开主页；关闭的内容对帖子和个人主页同时生效。</p>
                <button class="outline-btn wide-btn" @click="openSelfProfile">预览公开主页</button>
              </section>

              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">ABOUT ME</p><h2>个人介绍</h2></div><span>{{ profileBio.length }} / 240</span></div>
                <textarea v-model="profileBio" class="me-intro-input" maxlength="240" rows="5" placeholder="例如：信息学院大三，擅长 Python 和海报设计，想换一台二手显示器。" @input="profileIntroDirty = true"></textarea>
                <div class="me-card-foot"><span>{{ profileIntroDirty ? '有未保存的修改' : '已保存在本机' }}</span><button class="primary-btn" @click="saveProfileIntro">保存介绍</button></div>
              </section>

              <section class="me-card">
                <div class="me-card-head"><div><p class="me-eyebrow">LOCAL DATA</p><h2>本机偏好</h2></div></div>
                <dl class="settings-facts">
                  <div><dt>当前配色</dt><dd>{{ activePalette.name }}</dd></div>
                  <div><dt>背景来源</dt><dd>{{ backgroundModeLabel }}</dd></div>
                  <div><dt>景深模糊</dt><dd>{{ personalization.backgroundBlur }}px</dd></div>
                  <div><dt>本地图片</dt><dd>{{ personalization.customBackgrounds.length }} / 4 张</dd></div>
                </dl>
                <p v-if="customBackgroundWarning" class="inline-alert">浏览器缓存已满，本地背景未能写入；配色设置仍然保留。</p>
                <div class="me-card-foot"><span>仅保存在当前浏览器，不上传服务器</span><button class="text-btn danger" @click="resetPersonalization">恢复默认</button></div>
              </section>
            </aside>
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
            <div class="section-title"><div><h2>邮箱绑定</h2><p>用于接收平台通知和未来的账号恢复；不会被当作学生身份证明。</p></div><span class="status-pill">{{ currentUser.email_verified ? '已绑' : '未绑定' }}</span></div>
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
    <footer v-if="tab !== 'home'" class="workspace-footer"><span>海大互助 · 让资源流转，让技能相遇</span><span>平台记录协议与双方确认，付款由双方线下完成。<button @click="navigate('home')">返回首页</button></span></footer>

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

    <div v-if="showScheduleForm" class="modal-backdrop" @click.self="showScheduleForm = false">
      <div class="modal schedule-form-modal" role="dialog" aria-modal="true" aria-label="加入我的日程">
        <button class="modal-close" aria-label="关闭" @click="showScheduleForm = false">×</button>
        <h2>{{ scheduleForm.transaction_id ? '把约定时间加入日程' : '新增一条日程' }}</h2>
        <p class="modal-subtitle">日程会保存在本机浏览器；临近 3 天时进入通知铃铛，和时间重叠的日程会先提醒确认协议。</p>
        <form @submit.prevent="submitScheduleForm">
          <label>日程标题<input v-model="scheduleForm.title" required maxlength="160" placeholder="例如：Python 作业思路梳理" /></label>
          <div class="form-grid">
            <label>日期<input v-model="scheduleForm.date" type="date" required /></label>
            <label>开始时间<input v-model="scheduleForm.start_time" type="time" required /></label>
            <label>结束时间<input v-model="scheduleForm.end_time" type="time" required /></label>
            <label>地点<input v-model="scheduleForm.location" maxlength="160" placeholder="例如：图书馆北门" /></label>
          </div>
          <label>对方 / 备注<input v-model="scheduleForm.counterpart" maxlength="80" placeholder="对方昵称（可选）" /></label>
          <label>补充说明<textarea v-model="scheduleForm.note" rows="3" maxlength="300" placeholder="例如：带上笔记本，提前十分钟到"></textarea></label>
          <div v-if="scheduleDraftConflicts.length" class="schedule-inline-warning">
            <AppIcon name="clock" /><span>这个时间和「{{ scheduleDraftConflicts.map((item) => item.title).join('、') }}」重叠，提交时会再次提醒你确认。</span>
          </div>
          <div v-if="scheduleForm.transaction_id" class="schedule-source-note">来源交易：{{ scheduleForm.transaction_id }}</div>
          <button class="primary-btn wide">保存到我的日程</button>
        </form>
      </div>
    </div>

    <div v-if="showConflictDialog" class="modal-backdrop" @click.self="closeConflictDialog">
      <div class="modal conflict-modal" role="dialog" aria-modal="true" aria-label="日程时间冲突">
        <button class="modal-close" aria-label="关闭" @click="closeConflictDialog">×</button>
        <div class="conflict-modal-icon"><AppIcon name="calendar" /></div>
        <h2>这个时间和已有日程重叠</h2>
        <p class="modal-subtitle">请确认是否调整，或者仍然把两条安排都留在日程里。系统会持续在日程表和通知铃铛中标出冲突检测。</p>
        <div class="conflict-list">
          <article v-for="entry in scheduleConflicts" :key="entry.id" class="conflict-card">
            <b>{{ entry.title }}</b>
            <span>{{ entry.start_time }}–{{ entry.end_time }} · {{ entry.location || '地点待定' }}</span>
          </article>
        </div>
        <div v-if="pendingSchedule" class="conflict-pending">待加入：{{ pendingSchedule.title }} · {{ pendingSchedule.start_time }}–{{ pendingSchedule.end_time }}</div>
        <div class="conflict-actions">
          <button class="outline-btn" @click="closeConflictDialog">返回调整</button>
          <button class="primary-btn" @click="forceSchedule">仍然加入</button>
        </div>
      </div>
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
          <section class="publish-section"><div class="publish-step"><span>02</span><div><h3>价格与交易</h3><p>提前说清金额、时间和校内地点。</p></div></div><div class="form-grid">
            <label>金额<input v-model.number="publishForm.price" type="number" min="0" step="0.01" required /></label>
            <label>单位<input v-model="publishForm.price_unit" required placeholder="元 / 小时 / 次" /></label>
            <label>校内地点<input v-model="publishForm.location" placeholder="例如：海甸校区图书馆北门" /></label>
            <label v-if="publishForm.type === 'resource'">物品状态<input v-model="publishForm.condition_level" placeholder="例如：九成新，有少量划线" /></label>
            <label v-else>服务方式<select v-model="publishForm.service_mode"><option value="offline">线下</option><option value="online">线上</option><option value="both">线上 / 线下</option></select></label>
            <label v-if="publishForm.type === 'skill'" class="full">可服务时间<input v-model="publishForm.available_time" placeholder="例如：工作日 7 点后、周末下午" /></label>
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
        <div class="detail-kicker"><span class="type-tag" :class="selectedListing.type">{{ typeLabel(selectedListing.type) }}</span><span v-if="isFeatured(selectedListing)" class="detail-featured-label">推荐精华</span><span v-if="selectedListing.demo" class="demo-label">设计示例</span><span v-if="isFreeListing(selectedListing)" class="free-label">免费互助</span><span v-if="!selectedListing.demo" class="detail-time">{{ listingTime(selectedListing.created_at) }} 发布</span><span class="detail-views"><AppIcon name="eye" />{{ listingViewText(selectedListing, '0 浏览') }}</span></div>
        <div class="detail-title-row">
          <h2>{{ selectedListing.title }}</h2>
          <div class="detail-title-actions">
            <button v-if="isLoggedIn && !isAdmin && currentUser?.id !== selectedListing.owner_id" class="save-detail" :class="{ saved: isFavorited(selectedListing) }" :aria-label="isFavorited(selectedListing) ? '取消收藏' : '收藏'" @click="toggleFavorite(selectedListing)">{{ isFavorited(selectedListing) ? '★' : '☆' }}</button>
            <button v-if="!isAdmin && currentUser?.id !== selectedListing.owner_id" class="detail-report-btn" @click="openListingReport(selectedListing)"><AppIcon name="shield" />举报</button>
          </div>
        </div>
        <p class="modal-description">{{ selectedListing.description }}</p>
        <button v-if="selectedOwnerProfile" class="detail-owner-chip" :aria-label="`查看${selectedOwnerProfile.name}的个人主页`" @click.stop="openOwnerBubble(selectedListing, $event)">
          <span class="detail-owner-avatar">{{ selectedOwnerProfile.name.slice(0, 1) }}</span>
          <span class="detail-owner-copy">
            <span class="detail-owner-name">{{ selectedOwnerProfile.name }}<span v-if="selectedOwnerProfile.verified" class="owner-verified">✓</span><span v-if="selectedOwnerProfile.isDemo" class="demo-label">演示主页</span></span>
            <small>{{ canShowProfileField(selectedOwnerProfile, 'showCollege') ? (selectedOwnerProfile.college || '学院未公开') : '学院未公开' }} · 学号与手机号不公开</small>
          </span>
          <span class="detail-owner-stats"><b v-if="canShowProfileField(selectedOwnerProfile, 'showStats')">"{{ selectedOwnerProfile.credit ?? '未公开' }}</b><b v-else>数据未公开</b><small v-if="canShowProfileField(selectedOwnerProfile, 'showStats')">{{ selectedOwnerStats.totalViews.toLocaleString('zh-CN') }} 总浏览</small></span>
          <span class="detail-owner-more">查看主页 <AppIcon name="arrow" /></span>
        </button>
        <div class="detail-facts"><div><span>校区 / 地点</span><strong>{{ listingCampus(selectedListing) }}</strong></div><div><span>信用分</span><strong v-if="canShowProfileField(selectedOwnerProfile, 'showStats')" class="credit-score"><b>★</b>{{ listingCreditLabel(selectedListing) }}</strong><strong v-else>数据未公开</strong></div><div><span>价格</span><strong :class="{ free: isFreeListing(selectedListing) }">{{ listingPrice(selectedListing) }}</strong></div></div>
        <div v-if="selectedListing.demo" class="payment-note">这是设计示例，登录后可收藏到“我的收藏”（演示收藏保存在本机），不能发起交易；举报只支持真实帖子。</div>
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
              <button type="button" class="comment-kind" :class="{ active: commentAsThanks }" @click="commentAsThanks = !commentAsThanks">{{ commentAsThanks ? '不作为感谢' : '普通留言' }}</button>
              <span>{{ commentDraft.length }} / 180</span>
              <button class="primary-btn" :disabled="commentDraft.trim().length < 2">留下感谢</button>
            </div>
          </form>
        </section>
        <div v-if="selectedListing.demo" class="inline-alert detail-access-note">示例内容仅供界面展示；收藏状态保存在本机浏览器</div>
        <div v-else-if="currentUser?.id === selectedListing.owner_id" class="inline-alert detail-access-note">这是你的发布信息，不能向自己发起交易。</div>
        <div v-else-if="isAdmin" class="inline-alert detail-access-note">管理员账号只处理平台事务，不参与学生交易。</div>
        <div v-else-if="!isVerified" class="detail-access-note">
          <p>{{ isLoggedIn ? '完成学生认证后才能发起交易' : '登录并完成学生认证后可以发起交易' }}</p>
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

    <div v-if="showReportDialog" class="modal-backdrop" @click.self="closeReportDialog">
      <div class="modal report-modal" role="dialog" aria-modal="true" aria-label="举报帖子">
        <button class="modal-close" aria-label="关闭" @click="closeReportDialog">×</button>
        <span class="report-modal-icon"><AppIcon name="shield" /></span>
        <h2>举报这条帖子</h2>
        <p class="modal-subtitle">{{ reportTarget?.title }}</p>
        <template v-if="reportTarget?.demo">
          <div class="inline-alert">这是设计示例，没有对应的数据库记录，不能提交给管理员。真实帖子发布后，举报会进入管理员工作台</div>
          <div class="dialog-schedule-actions">
            <button class="ghost-btn" @click="closeReportDialog">先不举报</button>
            <button class="primary-btn" @click="startPublishFromReport">去发布真实帖子</button>
          </div>
        </template>
        <form v-else @submit.prevent="submitListingReport">
          <label>举报原因<input v-model="reportForm.reason" required minlength="2" maxlength="120" placeholder="例如：描述与实物不符" /></label>
          <label>详细说明<textarea v-model="reportForm.description" required minlength="5" maxlength="2000" rows="3" placeholder="请说明具体情况，方便管理员核查"></textarea></label>
          <p class="boundary-note">举报会进入管理员工作台；管理员可以下架帖子、禁用账号或调整信用分，处理过程会留下日志</p>
          <button class="primary-btn wide">提交给管理员</button>
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
              <span class="profile-listing-type" :class="item.type">{{ item.type === 'skill' ? '技能' : '资源' }}</span>
              <span class="profile-listing-copy"><b>{{ item.title }}</b><small>{{ typeLabel(item.type) }} · {{ item.category_name }} · {{ listingViewText(item, '新发布') }}</small></span>
              <span class="profile-listing-price" :class="{ free: isFreeListing(item) }">{{ listingPrice(item) }}</span>
              <AppIcon name="arrow" />
            </button>
          </div>
          <p v-else class="profile-empty-line">还没有公开的帖子。</p>
        </section>
        <div class="public-profile-foot">
          <p>{{ selectedProfile.isSelf ? '这些展示范围可以在“账号与安全”中随时调整' : '主页由发帖人选择公开范围，平台只展示与交易判断有关的信息' }}</p>
          <button v-if="selectedProfile.isSelf" class="outline-btn" @click="selectedProfile = null; selectedListing = null; navigate('me')">调整公开范围</button>
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
        <div v-if="transactionActionsFor(selectedTransaction).length" class="dialog-transaction-actions">
          <div><b>{{ selectedTransaction.status === 'pending_provider' ? '这条请求等待你处理' : '这笔交易等待你确认' }}</b><span>{{ selectedTransaction.status === 'pending_provider' ? '接受后对方还需确认协议，交易才会进入交付阶段。' : '双方都确认后交易才会完成，过程中可以随时在下方留言协商。' }}</span></div>
          <div class="dialog-transaction-actions-buttons">
            <button v-for="action in transactionActionsFor(selectedTransaction)" :key="action.key" :class="action.tone === 'primary' ? 'primary-btn' : 'ghost-btn danger'" @click="transactionAction(selectedTransaction.id, action.key)">{{ action.label }}</button>
          </div>
        </div>
        <div v-if="canScheduleTransaction(selectedTransaction)" class="dialog-schedule-cta">
          <div><span>下一步</span><b>把约定时间加入我的日程</b><p>临近日期会在通知铃铛提醒；如果和已有日程冲突，会先请你确认协议。</p></div>
          <button class="outline-btn" @click="openScheduleForTransaction(selectedTransaction)">{{ scheduledForTransaction(selectedTransaction.id) ? '查看我的日程' : '加入我的日程' }}</button>
        </div>
        <div class="demo-payment-box" :class="{ paid: selectedTransaction.demo_payment_status === 'simulated_paid' }">
          <div><span class="demo-badge">课程演示</span><b>{{ selectedTransaction.demo_payment_status === 'simulated_paid' ? '模拟付款已记录' : '未记录模拟付款' }}</b><p>只演示订单状态，不调用微信、支付宝或任何真实资金接口。</p></div>
          <button v-if="currentUser.demo_features_enabled && selectedTransaction.initiator_id === currentUser.id && ['agreed','provider_confirmed','requester_confirmed'].includes(selectedTransaction.status) && selectedTransaction.demo_payment_status !== 'simulated_paid' && Number(selectedTransaction.agreed_price || selectedTransaction.proposed_price) > 0" class="outline-btn demo-action" @click="simulatePayment(selectedTransaction)">模拟付款</button>
        </div>
        <section class="dialog-section">
          <div class="dialog-heading"><b>交易消息</b><span>仅交易双方可见</span></div>
          <div class="message-list"><div v-if="!messages.length" class="message-empty">还没有消息</div><div v-for="message in messages" :key="message.id" class="message" :class="{ mine: message.sender_id === currentUser.id }"><small>{{ message.sender_name }}</small><span>{{ message.content }}</span></div></div>
          <form v-if="!['completed','cancelled','rejected'].includes(selectedTransaction.status)" class="message-form" @submit.prevent="sendMessage"><input v-model="newMessage" placeholder="输入交易消息" /><button class="primary-btn">发</button></form>
        </section>
        <section v-if="selectedTransaction.status === 'completed'" class="dialog-section">
          <div class="dialog-heading"><b>交易评价</b><span>双方完成确认后开放</span></div>
          <form class="compact-form" @submit.prevent="submitReview"><label>评分<select v-model.number="reviewForm.rating"><option v-for="rating in 5" :key="rating" :value="rating">{{ rating }} </option></select></label><label>评价<textarea v-model="reviewForm.content" rows="2" maxlength="500"></textarea></label><button class="outline-btn">提交评价</button></form>
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

