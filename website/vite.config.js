import { defineConfig } from 'vite'

export default defineConfig({
  root: '.',
  base: '/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      input: { main: './index.html' }
    },
    chunkSizeWarningLimit: 800
  },
  server: {
    port: 8080,
    host: true
  }
})
