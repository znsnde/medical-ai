import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    // 大文件上传超时设置
    proxy: {
      // 匹配所有以 /api 开头的请求
      '/api': {
        target: 'http://127.0.0.1:8000', // 后端服务地址
        changeOrigin: true, // 开启跨域模拟
        timeout: 120000, // 上传+AI解析最长等2分钟
      },
      // 诊断报告PDF/参考影像等静态文件（report_api 返回相对 /static/... 路径）
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})