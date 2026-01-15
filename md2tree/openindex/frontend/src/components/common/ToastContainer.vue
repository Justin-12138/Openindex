<script setup lang="ts">
import { useUIStore } from '@/stores'

const uiStore = useUIStore()

function getIcon(type: string) {
  switch (type) {
    case 'success': return '✓'
    case 'error': return '✕'
    case 'warning': return '⚠'
    case 'loading': return '◌'
    default: return 'ℹ'
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in uiStore.toasts"
          :key="toast.id"
          class="toast"
          :class="`toast-${toast.type}`"
        >
          <span class="toast-icon" :class="{ spinning: toast.type === 'loading' }">
            {{ getIcon(toast.type) }}
          </span>
          <span class="toast-message">{{ toast.message }}</span>
          <button 
            v-if="toast.type !== 'loading'"
            class="toast-close" 
            @click="uiStore.removeToast(toast.id)"
          >
            ×
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style lang="scss" scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 500;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--bg-elevated);
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
  min-width: 240px;
  max-width: 400px;
  
  &.toast-success {
    border-left: 3px solid var(--success);
    .toast-icon { color: var(--success); }
  }
  
  &.toast-error {
    border-left: 3px solid var(--error);
    .toast-icon { color: var(--error); }
  }
  
  &.toast-warning {
    border-left: 3px solid var(--warning);
    .toast-icon { color: var(--warning); }
  }
  
  &.toast-info {
    border-left: 3px solid var(--info);
    .toast-icon { color: var(--info); }
  }
  
  &.toast-loading {
    border-left: 3px solid var(--primary);
    .toast-icon { color: var(--primary); }
  }
}

.toast-icon {
  font-size: 16px;
  font-weight: bold;
  
  &.spinning {
    animation: spin 1s linear infinite;
  }
}

.toast-message {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
}

.toast-close {
  color: var(--text-muted);
  font-size: 18px;
  line-height: 1;
  transition: color 0.15s;
  
  &:hover {
    color: var(--text-primary);
  }
}

// 动画
.toast-enter-active {
  animation: slideIn 0.25s ease;
}

.toast-leave-active {
  animation: slideOut 0.2s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideOut {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
