import path from 'node:path'
import process from 'node:process'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const rootDir = path.resolve(process.cwd(), '..')
  const env = {
    ...loadEnv(mode, rootDir, ''),
    ...process.env,
  }

  return {
    envDir: '..',
    plugins: [react()],
    server: {
      host: env.FRONTEND_HOST,
      port: Number(env.FRONTEND_CONTAINER_PORT),
    },
    preview: {
      host: env.FRONTEND_HOST,
      port: Number(env.FRONTEND_CONTAINER_PORT),
    },
    test: {
      environment: 'jsdom',
      globals: false,
      setupFiles: './src/test/setup.js',
      css: true,
    },
  }
})
