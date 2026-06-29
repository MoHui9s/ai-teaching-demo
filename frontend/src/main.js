import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.css'

// Create Vue app
const app = createApp(App)

// Add Pinia for state management (optional, using composables instead)
// app.use(createPinia())

// Mount app
app.mount('#app')

// Hide loading screen
setTimeout(() => {
  const loader = document.getElementById('app-loading')
  if (loader) loader.classList.add('loaded')
}, 100)
