import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Library, Document } from '@/types'
import { api } from '@/composables/useApi'

export const useLibraryStore = defineStore('library', () => {
  // 状态
  const libraries = ref<Library[]>([])
  const documents = ref<Document[]>([])
  const expandedLibraries = ref<Set<string>>(new Set(['uncategorized']))
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const uncategorizedDocs = computed(() =>
    documents.value.filter(d => !d.library_id)
  )

  const getLibraryDocs = (libraryId: string) =>
    documents.value.filter(d => d.library_id === libraryId)

  const totalDocuments = computed(() => documents.value.length)

  // 方法
  async function loadLibraries() {
    try {
      loading.value = true
      libraries.value = await api.libraries.list()
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function loadDocuments() {
    try {
      loading.value = true
      documents.value = await api.documents.list()
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function loadAll() {
    await Promise.all([loadLibraries(), loadDocuments()])
  }

  async function createLibrary(name: string, icon = '📁') {
    const lib = await api.libraries.create({ name, icon })
    libraries.value.push(lib)
    expandedLibraries.value.add(lib.id)
    return lib
  }

  async function updateLibrary(id: string, data: Partial<Library>) {
    const lib = await api.libraries.update(id, data)
    const idx = libraries.value.findIndex(l => l.id === id)
    if (idx !== -1) {
      libraries.value[idx] = lib
    }
    return lib
  }

  async function deleteLibrary(id: string) {
    await api.libraries.delete(id)
    libraries.value = libraries.value.filter(l => l.id !== id)
    expandedLibraries.value.delete(id)
    // 文档会自动移至未分类
    documents.value.forEach(d => {
      if (d.library_id === id) {
        d.library_id = null
      }
    })
  }

  async function uploadDocument(file: File) {
    const result = await api.documents.upload(file)
    await loadDocuments()
    return result
  }

  async function deleteDocument(id: string) {
    await api.documents.delete(id)
    documents.value = documents.value.filter(d => d.id !== id)
  }

  async function moveDocument(docId: string, libraryId: string | null) {
    await api.documents.move(docId, libraryId)
    const doc = documents.value.find(d => d.id === docId)
    if (doc) {
      doc.library_id = libraryId
    }
  }

  function toggleLibrary(id: string) {
    if (expandedLibraries.value.has(id)) {
      expandedLibraries.value.delete(id)
    } else {
      expandedLibraries.value.add(id)
    }
  }

  function isExpanded(id: string) {
    return expandedLibraries.value.has(id)
  }

  return {
    // 状态
    libraries,
    documents,
    expandedLibraries,
    loading,
    error,
    // 计算属性
    uncategorizedDocs,
    getLibraryDocs,
    totalDocuments,
    // 方法
    loadLibraries,
    loadDocuments,
    loadAll,
    createLibrary,
    updateLibrary,
    deleteLibrary,
    uploadDocument,
    deleteDocument,
    moveDocument,
    toggleLibrary,
    isExpanded
  }
})
