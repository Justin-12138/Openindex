<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  resize: [delta: number]
}>()

const isDragging = ref(false)
let startX = 0

function handleMouseDown(e: MouseEvent) {
  isDragging.value = true
  startX = e.clientX
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function handleMouseMove(e: MouseEvent) {
  if (!isDragging.value) return
  const delta = e.clientX - startX
  emit('resize', delta)
  startX = e.clientX
}

function handleMouseUp() {
  isDragging.value = false
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}
</script>

<template>
  <div 
    class="panel-resizer" 
    :class="{ dragging: isDragging }"
    @mousedown="handleMouseDown"
  >
    <div class="resizer-line" />
  </div>
</template>

<style lang="scss" scoped>
.panel-resizer {
  width: 6px;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  transition: background 0.15s ease;
  
  &:hover,
  &.dragging {
    background: rgba(59, 130, 246, 0.1);
    
    .resizer-line {
      background: var(--primary);
      opacity: 1;
    }
  }
}

.resizer-line {
  width: 2px;
  height: 40px;
  background: var(--border-color);
  border-radius: 2px;
  opacity: 0.5;
  transition: all 0.15s ease;
}
</style>
