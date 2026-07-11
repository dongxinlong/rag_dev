import { defineConfig, loadEnv } from 'vite'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver, NaiveUiResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())

  return {
    plugins: [
      vue(),
      // 自动导入 Vue/VueRouter/Pinia API
      AutoImport({
        imports: [
          'vue',
          'vue-router',
          'pinia',
          {
            'naive-ui': [
              'useDialog',
              'useMessage',
              'useNotification',
              'useLoadingBar',
            ],
          },
        ],
        resolvers: [ElementPlusResolver()],
        dts: 'src/auto-imports.d.ts',
      }),
      // 组件按需导入
      Components({
        resolvers: [ElementPlusResolver(), NaiveUiResolver()],
        dts: 'src/components.d.ts',
      }),
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 3000,
      host: true,
      // 开发环境代理
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/uploads': {
          target: env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: '',
        },
      },
    },
  }
})
