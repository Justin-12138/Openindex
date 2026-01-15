<script setup lang="ts">
defineProps<{
  size?: 'sm' | 'md' | 'lg'
  text?: string
}>()
</script>

<template>
  <div class="loading-spinner" :class="`size-${size || 'md'}`">
    <div class="spinner"></div>
    <span v-if="text" class="loading-text">{{ text }}</span>
  </div>
</template>

<style lang="scss" scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px;
}

.spinner {
  border-radius: 50%;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary);
  animation: spin 0.8s linear infinite;
}

.size-sm .spinner {
  width: 16px;
  height: 16px;
}

.size-md .spinner {
  width: 24px;
  height: 24px;
}

.size-lg .spinner {
  width: 36px;
  height: 36px;
  border-width: 3px;
}

.loading-text {
  font-size: 13px;
  color: var(--text-secondary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
