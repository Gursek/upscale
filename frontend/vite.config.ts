import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({
				pages: 'build',
				assets: 'build',
				fallback: 'index.html',
				precompress: false
			})
		}),
		VitePWA({
			registerType: 'autoUpdate',
			manifest: false,
			includeAssets: ['manifest.webmanifest', 'pwa-192.png', 'pwa-512.png'],
			workbox: {
				navigateFallback: '/index.html',
				globPatterns: ['**/*.{html,js,css,woff,woff2,ttf,otf,png,svg}'],
				runtimeCaching: [
					{
						urlPattern: ({ url, request }) =>
							request.method === 'GET' &&
							url.pathname.replace(/\/$/, '').endsWith('/api/products'),
						handler: 'NetworkFirst',
						options: {
							cacheName: 'upscale-products',
							networkTimeoutSeconds: 5,
							expiration: {
								maxEntries: 20,
								maxAgeSeconds: 60 * 60 * 24
							},
							cacheableResponse: {
								statuses: [0, 200]
							}
						}
					},
					{
						urlPattern: ({ url, request }) =>
							request.method === 'GET' &&
							url.pathname.replace(/\/$/, '').endsWith('/api/auth/me'),
						handler: 'NetworkFirst',
						options: {
							cacheName: 'upscale-auth-me',
							networkTimeoutSeconds: 5,
							expiration: {
								maxEntries: 5,
								maxAgeSeconds: 60 * 30
							},
							cacheableResponse: {
								statuses: [0, 200]
							}
						}
					}
				]
			}
		})
	]
});
