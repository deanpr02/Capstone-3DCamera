import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/socket.io': {
        target: 'https://192.168.0.151:8181',
        changeOrigin: true,
        secure: false,
        ws: true, // Enable WebSocket support
      },
    },
  },
})
