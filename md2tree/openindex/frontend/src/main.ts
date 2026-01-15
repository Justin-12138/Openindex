import { createApp } from 'vue'
import { pinia } from './stores'
import App from './App.vue'
import './assets/styles/global.scss'
import 'katex/dist/katex.min.css'

const app = createApp(App)
app.use(pinia)
app.mount('#app')
