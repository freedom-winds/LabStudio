import { createRouter, createWebHashHistory } from 'vue-router'
import { isAuthed } from '../stores/auth'

const Portal = () => import('../views/Portal.vue')
const HonorWall = () => import('../views/HonorWall.vue')
const Login = () => import('../views/Login.vue')
const FirstPassword = () => import('../views/FirstPassword.vue')
const ChangePassword = () => import('../views/ChangePassword.vue')
const Dashboard = () => import('../views/Dashboard.vue')
const Years = () => import('../views/Years.vue')
const YearDetail = () => import('../views/YearDetail.vue')
const Teams = () => import('../views/Teams.vue')
const TeamDetail = () => import('../views/TeamDetail.vue')
const Experiments = () => import('../views/Experiments.vue')
const ExperimentDetail = () => import('../views/ExperimentDetail.vue')
const Reservations = () => import('../views/Reservations.vue')
const ChatCenter = () => import('../views/ChatCenter.vue')
const Announcements = () => import('../views/Announcements.vue')
const Toolbox = () => import('../views/Toolbox.vue')
const HonorAdmin = () => import('../views/HonorAdmin.vue')
const Admin = () => import('../views/Admin.vue')

const routes = [
  { path: '/', component: Portal },
  { path: '/honors', component: HonorWall },
  { path: '/login', component: Login },
  { path: '/first-password', component: FirstPassword, meta: { requiresAuth: true } },
  { path: '/app/password', component: ChangePassword, meta: { requiresAuth: true } },
  { path: '/app', component: Dashboard, meta: { requiresAuth: true } },
  { path: '/app/years', component: Years, meta: { requiresAuth: true } },
  { path: '/app/years/:id', component: YearDetail, meta: { requiresAuth: true } },
  { path: '/app/teams', component: Teams, meta: { requiresAuth: true } },
  { path: '/app/teams/:id', component: TeamDetail, meta: { requiresAuth: true } },
  { path: '/app/experiments', component: Experiments, meta: { requiresAuth: true } },
  { path: '/app/experiments/:id', component: ExperimentDetail, meta: { requiresAuth: true } },
  { path: '/app/reservations', component: Reservations, meta: { requiresAuth: true } },
  { path: '/app/chats', component: ChatCenter, meta: { requiresAuth: true } },
  { path: '/app/announcements', component: Announcements, meta: { requiresAuth: true } },
  { path: '/app/toolbox', component: Toolbox, meta: { requiresAuth: true } },
  { path: '/app/honors', component: HonorAdmin, meta: { requiresAuth: true } },
  { path: '/app/admin', component: Admin, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthed()) return '/login'
  if (to.path === '/login' && isAuthed()) return '/app'
  return true
})

export default router
