<template>
  <el-dialog
    v-model="visible"
    :title="fileName"
    width="80%"
    top="5vh"
    destroy-on-close
    @close="handleClose"
  >
    <!-- Word 预览（mammoth 本地解析） -->
    <div v-if="isWord" class="preview-container">
      <div v-if="loading" class="preview-loading">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p>正在解析文档...</p>
      </div>
      <div v-else class="word-preview" v-html="wordHtml" />
    </div>

    <!-- PDF 预览（浏览器原生） -->
    <div v-else-if="isPdf" class="preview-container">
      <iframe :src="previewUrl" frameborder="0" class="preview-iframe" />
    </div>

    <!-- 图片预览 -->
    <div v-else-if="isImage" class="preview-container">
      <img :src="previewUrl" :alt="fileName" class="preview-image" />
    </div>

    <!-- Markdown 预览 -->
    <div v-else-if="isMarkdown" class="preview-container markdown-preview" v-html="renderedMd" />

    <!-- TXT 预览 -->
    <div v-else-if="isTxt" class="preview-container txt-preview">
      <pre>{{ txtContent }}</pre>
    </div>

    <!-- CSV 预览 -->
    <div v-else-if="isCsv" class="preview-container">
      <el-table :data="csvData" stripe border max-height="500" style="width: 100%">
        <el-table-column
          v-for="(col, idx) in csvColumns"
          :key="idx"
          :prop="col"
          :label="col"
          min-width="120"
        />
      </el-table>
    </div>

    <!-- 不支持 -->
    <div v-else class="preview-container">
      <div class="preview-tip">
        <el-icon :size="48" color="var(--color-text-placeholder)"><Warning /></el-icon>
        <p>不支持预览此文件格式</p>
        <p class="tip-sub">{{ ext?.toUpperCase() || '未知' }}</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" @click="handleDownload">
        <el-icon><Download /></el-icon>
        下载
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import mammoth from 'mammoth'
import { marked } from 'marked'

const props = defineProps<{
  modelValue: boolean
  fileName: string
  fileUrl: string
  fileSize?: number
  ext?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const loading = ref(false)

// 格式判断
const isWord = computed(() => ['doc', 'docx'].includes(props.ext || ''))
const isPdf = computed(() => props.ext === 'pdf')
const isImage = computed(() => ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(props.ext || ''))
const isMarkdown = computed(() => props.ext === 'md')
const isTxt = computed(() => props.ext === 'txt')
const isCsv = computed(() => props.ext === 'csv')

const previewUrl = computed(() => props.fileUrl || '')

// ═══ Word 解析 ═══
const wordHtml = ref('')

async function loadWordPreview() {
  if (!props.fileUrl) return
  loading.value = true
  try {
    const response = await fetch(props.fileUrl)
    const arrayBuffer = await response.arrayBuffer()
    const result = await mammoth.convertToHtml({ arrayBuffer })
    wordHtml.value = result.value || '<p style="color:#999">文档内容为空</p>'
  } catch {
    wordHtml.value = '<p style="color:#E74C3C">文档解析失败，请下载后查看</p>'
  } finally {
    loading.value = false
  }
}

// ═══ 文本解析 ═══
const csvColumns = ref<string[]>([])
const csvData = ref<Record<string, string>[]>([])
const renderedMd = ref('')
const txtContent = ref('')

async function loadTextContent() {
  if (!props.fileUrl) return
  try {
    const res = await fetch(props.fileUrl)
    const text = await res.text()
    if (isCsv.value) {
      parseCsv(text)
    } else if (isTxt.value) {
      txtContent.value = text
    } else if (isMarkdown.value) {
      renderedMd.value = renderMarkdown(text)
    }
  } catch {
    // 预览失败
  }
}

// ═══ 打开弹窗时加载 ═══
watch(() => props.modelValue, async (val) => {
  if (!val) return
  if (isWord.value) {
    await loadWordPreview()
  } else if (isMarkdown.value || isTxt.value || isCsv.value) {
    await loadTextContent()
  }
})

function parseCsv(text: string) {
  const lines = text.split('\n').filter(l => l.trim())
  if (lines.length === 0) return
  csvColumns.value = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  csvData.value = lines.slice(1).map(line => {
    const values = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))
    const row: Record<string, string> = {}
    csvColumns.value.forEach((col, idx) => { row[col] = values[idx] || '' })
    return row
  })
}

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

async function handleDownload() {
  if (!props.fileUrl) return
  try {
    // fetch 文件并创建 blob，强制用原始文件名
    const response = await fetch(props.fileUrl)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = props.fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    // fallback: 直接打开
    window.open(props.fileUrl, '_blank')
  }
}

function handleClose() {
  wordHtml.value = ''
  csvColumns.value = []
  csvData.value = []
  renderedMd.value = ''
  txtContent.value = ''
}
</script>

<style lang="scss" scoped>
.preview-container {
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  gap: 12px;
  color: var(--color-text-secondary);
}

.preview-iframe {
  width: 100%;
  height: 65vh;
  border: none;
  border-radius: var(--radius-md);
}

.preview-image {
  max-width: 100%;
  max-height: 65vh;
  object-fit: contain;
  border-radius: var(--radius-md);
}

.preview-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  text-align: center;

  p { font-size: var(--text-md); font-weight: 500; color: var(--color-text-primary); }
  .tip-sub { font-size: var(--text-sm); font-weight: 400; color: var(--color-text-secondary); }
}

// Word 预览样式
.word-preview {
  width: 100%;
  max-height: 65vh;
  overflow-y: auto;
  padding: 24px;
  background: white;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  line-height: 1.8;

  :deep(h1), :deep(h2), :deep(h3) { margin: 16px 0 8px; }
  :deep(table) { border-collapse: collapse; width: 100%; margin: 12px 0; }
  :deep(td), :deep(th) { border: 1px solid #ddd; padding: 8px; text-align: left; }
  :deep(th) { background: oklch(0.96 0.003 260); font-weight: 600; }
  :deep(img) { max-width: 100%; }
  :deep(pre) { background: oklch(0.97 0.002 260); padding: 12px; border-radius: var(--radius-md); overflow-x: auto; }
}

.txt-preview {
  text-align: left;
  width: 100%;

  pre {
    background: oklch(0.97 0.002 260);
    padding: 20px;
    border-radius: var(--radius-md);
    max-height: 65vh;
    overflow: auto;
    font-family: var(--font-family-mono);
    font-size: var(--text-sm);
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-all;
    width: 100%;
  }
}

.markdown-preview {
  padding: 24px;
  max-height: 65vh;
  overflow-y: auto;
  text-align: left;
  line-height: 1.8;
  width: 100%;

  :deep(h1), :deep(h2), :deep(h3), :deep(h4) {
    margin: 20px 0 12px;
    color: var(--color-text-primary);
    font-weight: 600;
  }
  :deep(h1) { font-size: 1.5em; border-bottom: 1px solid var(--color-border-light); padding-bottom: 8px; }
  :deep(h2) { font-size: 1.3em; border-bottom: 1px solid var(--color-border-light); padding-bottom: 6px; }
  :deep(h3) { font-size: 1.1em; }

  :deep(p) { margin: 8px 0; }

  :deep(ul), :deep(ol) {
    padding-left: 24px;
    margin: 8px 0;
  }

  :deep(li) { margin: 4px 0; }

  :deep(pre) {
    background: oklch(0.13 0.020 260);
    color: oklch(0.90 0.010 260);
    padding: 16px;
    border-radius: var(--radius-md);
    overflow-x: auto;
    font-family: var(--font-family-mono);
    font-size: var(--text-sm);
    margin: 12px 0;
  }

  :deep(code) {
    background: oklch(0.95 0.003 260);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-family: var(--font-family-mono);
    font-size: 0.9em;
  }

  :deep(pre code) {
    background: none;
    padding: 0;
  }

  :deep(blockquote) {
    border-left: 4px solid var(--color-primary);
    padding: 8px 16px;
    margin: 12px 0;
    background: var(--color-bg-page);
    color: var(--color-text-secondary);
  }

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
  }

  :deep(td), :deep(th) {
    border: 1px solid var(--color-border);
    padding: 8px 12px;
    text-align: left;
  }

  :deep(th) {
    background: var(--color-bg-page);
    font-weight: 600;
  }

  :deep(img) {
    max-width: 100%;
    border-radius: var(--radius-md);
  }

  :deep(a) {
    color: var(--color-primary);
    text-decoration: none;

    &:hover { text-decoration: underline; }
  }

  :deep(hr) {
    border: none;
    border-top: 1px solid var(--color-border-light);
    margin: 20px 0;
  }
}
</style>
