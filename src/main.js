import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/app.css'
import { adoptTokenFromHash, loadUser } from './api'
import { startCollection } from './lib/collection'
import { startPageTracking } from './lib/pageTracking'

adoptTokenFromHash() // returning from Google / Facebook sign-in
loadUser()
startCollection() // saved photos: browser until sign-in, then the account

const app = createApp(App)
app.use(router)
startPageTracking(router) // behaviour-events: page views (time, scroll) and CTA clicks, consent-aware
app.mount('#app')
