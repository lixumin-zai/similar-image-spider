import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/search-similar': 'http://localhost:8000',
            '/search-similar-base64': 'http://localhost:8000',
            '/download-images': 'http://localhost:8000',
            '/health': 'http://localhost:8000',
        }
    }
})
