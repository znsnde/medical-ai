// 认证工具 — token 和用户信息的 localStorage 存取

const TOKEN_KEY = 'medical_token'
const USER_KEY = 'medical_user'

export const getToken = () => localStorage.getItem(TOKEN_KEY)

export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)

export const removeToken = () => localStorage.removeItem(TOKEN_KEY)

export const getUser = () => {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || '{}')
  } catch {
    return {}
  }
}

export const setUser = (user) => localStorage.setItem(USER_KEY, JSON.stringify(user))

export const removeUser = () => localStorage.removeItem(USER_KEY)

// 是否已登录
export const isLoggedIn = () => !!getToken()

// 退出登录（清除所有认证信息）
export const logout = () => {
  removeToken()
  removeUser()
}

// 保存登录信息
export const saveLoginInfo = (token, user) => {
  setToken(token)
  setUser(user)
}
