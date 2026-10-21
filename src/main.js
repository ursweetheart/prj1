import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/app.css'
import { adoptTokenFromHash, loadUser } from './api'

adoptTokenFromHash() // returning from Google / Facebook sign-in
loadUser()

const app = createApp(App)
app.use(router)
app.mount('#app')
