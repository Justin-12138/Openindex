/// <reference types="vite/client" />

// 扩展模块声明以支持 ?url 后缀导入
declare module '*?url' {
  const src: string
  export default src
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}
