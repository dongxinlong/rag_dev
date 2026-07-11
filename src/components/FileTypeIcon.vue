<template>
  <svg v-if="svgContent" :width="size" :height="size" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="4" y="2" width="32" height="40" rx="4" :fill="bgColor" />
    <rect x="4" y="2" width="32" height="40" rx="4" stroke="oklch(0 0 0 / 0.08)" stroke-width="0.5" />
    <!-- 折角 -->
    <path :d="`M28 2v10h10`" :fill="darkColor" opacity="0.15" />
    <path :d="`M28 2l10 10h-10z`" :fill="darkColor" opacity="0.1" />
    <!-- 内容区 -->
    <rect x="8" :y="contentY" :width="contentW" height="2" rx="1" :fill="darkColor" opacity="0.3" />
    <rect x="8" :y="contentY + 6" :width="contentW2" height="2" rx="1" :fill="darkColor" opacity="0.2" />
    <rect x="8" :y="contentY + 12" :width="contentW3" height="2" rx="1" :fill="darkColor" opacity="0.15" />
    <!-- 扩展名标签 -->
    <rect :x="labelX" y="32" :width="labelW" height="10" rx="2" :fill="labelColor" />
    <text :x="labelX + labelW / 2" y="40" text-anchor="middle" fill="white" font-size="7" font-weight="600" font-family="Arial, sans-serif">
      {{ ext.toUpperCase() }}
    </text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  ext: string
  size?: number
}>(), {
  size: 48,
})

const extColors: Record<string, { bg: string; dark: string; label: string }> = {
  pdf:  { bg: '#FDE8E8', dark: '#C0392B', label: '#E74C3C' },
  doc:  { bg: '#D6EAF8', dark: '#2471A3', label: '#2B7CEA' },
  docx: { bg: '#D6EAF8', dark: '#2471A3', label: '#2B7CEA' },
  xls:  { bg: '#D5F5E3', dark: '#1E8449', label: '#27AE60' },
  xlsx: { bg: '#D5F5E3', dark: '#1E8449', label: '#27AE60' },
  csv:  { bg: '#D5F5E3', dark: '#1E8449', label: '#27AE60' },
  ppt:  { bg: '#FDEBD0', dark: '#B9770E', label: '#E67E22' },
  pptx: { bg: '#FDEBD0', dark: '#B9770E', label: '#E67E22' },
  txt:  { bg: '#F2F3F4', dark: '#7F8C8D', label: '#95A5A6' },
  md:   { bg: '#E8E8E8', dark: '#2C3E50', label: '#34495E' },
  png:  { bg: '#F4ECF7', dark: '#7D3C98', label: '#9B59B6' },
  jpg:  { bg: '#F4ECF7', dark: '#7D3C98', label: '#9B59B6' },
  jpeg: { bg: '#F4ECF7', dark: '#7D3C98', label: '#9B59B6' },
  gif:  { bg: '#F4ECF7', dark: '#7D3C98', label: '#9B59B6' },
  svg:  { bg: '#FDEBD0', dark: '#B9770E', label: '#E67E22' },
  mp4:  { bg: '#FDE8E8', dark: '#C0392B', label: '#E74C3C' },
  mp3:  { bg: '#E8F8F5', dark: '#148F77', label: '#1ABC9C' },
  zip:  { bg: '#FEF5E7', dark: '#B7950B', label: '#F39C12' },
  rar:  { bg: '#FEF5E7', dark: '#B7950B', label: '#F39C12' },
}

const defaultColors = { bg: '#F2F3F4', dark: '#7F8C8D', label: '#95A5A6' }

const colors = computed(() => extColors[props.ext] || defaultColors)
const bgColor = computed(() => colors.value.bg)
const darkColor = computed(() => colors.value.dark)
const labelColor = computed(() => colors.value.label)
const svgContent = computed(() => true)

const contentY = computed(() => 14)
const contentW = computed(() => 20)
const contentW2 = computed(() => 16)
const contentW3 = computed(() => 12)

const labelW = computed(() => {
  const len = props.ext.length
  return Math.max(22, len * 8 + 6)
})
const labelX = computed(() => (36 - labelW.value) / 2 + 4)
</script>
