import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')

setTimeout(() => {
  const loader = document.getElementById('app-loading')
  if (loader) loader.classList.add('loaded')
}, 100)
