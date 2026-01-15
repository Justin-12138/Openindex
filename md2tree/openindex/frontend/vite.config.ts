import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  base: './', // 使用相对路径
  optimizeDeps: {
    include: ['pdfjs-dist']
  },
  esbuild: {
    target: 'esnext'
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8090',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: '../static',
    emptyOutDir: true,
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks: {
          'pdf': ['pdfjs-dist'],
          'vendor': ['vue', 'pinia', '@vueuse/core']
        }
      }
    }
  }
})
