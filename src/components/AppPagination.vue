<template>
  <div class="pagination-wrap" v-if="total > 0">
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[15, 30, 50, 100]"
      :background="true"
      :page-sizes-label="pageSizesLabel"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="handleChange"
      @size-change="handleChange"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  total: number
  page?: number
  size?: number
}>(), {
  page: 1,
  size: 30,
})

const emit = defineEmits<{
  (e: 'update:page', val: number): void
  (e: 'update:size', val: number): void
  (e: 'change'): void
}>()

const currentPage = computed({
  get: () => props.page,
  set: (val) => emit('update:page', val),
})

const pageSize = computed({
  get: () => props.size,
  set: (val) => emit('update:size', val),
})

const pageSizesLabel = '条/页'

function handleChange() {
  emit('change')
}
</script>

<style lang="scss" scoped>
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 20px 0 0;

  :deep(.el-pagination) {
    --el-pagination-font-size: 13px;

    // 中文化
    .el-pagination__total {
      font-size: 13px;
      color: var(--color-text-secondary);
    }

    .el-pagination__jump {
      font-size: 13px;
      color: var(--color-text-secondary);
    }
  }
}
</style>
