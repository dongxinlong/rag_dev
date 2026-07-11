/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API 基础路径 */
  readonly VITE_API_BASE_URL: string
  /** 后端代理地址（仅开发环境） */
  readonly VITE_API_TARGET: string
  /** 文件上传并发数 */
  readonly VITE_UPLOAD_CONCURRENCY: string
  /** 每次请求间隔（ms），控制速率 */
  readonly VITE_UPLOAD_INTERVAL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
