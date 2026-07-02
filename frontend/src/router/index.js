import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/user'
  },
  {
    path: '/user',
    name: 'UserLogin',
    component: () => import('../views/UserLogin.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/user/:user_id',
    name: 'UserChat',
    component: () => import('../views/UserChat.vue'),
    meta: { requiresAuth: true, userType: 'user' }
  },
  {
    path: '/admin',
    name: 'AdminLogin',
    component: () => import('../views/AdminLogin.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/admin/dashboard',
    name: 'AdminDashboard',
    component: () => import('../views/AdminDashboard.vue'),
    meta: { requiresAuth: true, userType: 'admin' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token')
  const adminToken = localStorage.getItem('admin_token')
  const requiresAuth = to.meta.requiresAuth
  const userType = to.meta.userType

  if (requiresAuth) {
    if (userType === 'admin') {
      if (!adminToken) {
        next('/admin')
      } else {
        next()
      }
    } else if (userType === 'user') {
      if (!token) {
        next('/user')
      } else {
        next()
      }
    }
  } else {
    // If already logged in, redirect to appropriate dashboard
    if (to.path === '/user' && token) {
      const userId = localStorage.getItem('user_id')
      next(userId ? `/user/${userId}` : '/user')
    } else if (to.path === '/admin' && adminToken) {
      next('/admin/dashboard')
    } else {
      next()
    }
  }
})

export default router
