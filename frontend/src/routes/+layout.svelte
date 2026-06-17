<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { API_BASE, apiJson, revokeCurrentSession } from '$lib/api';
	import { drainOfflineQueue, subscribeQueueCount } from '$lib/offline-queue';
	import { auth } from '$lib/stores/auth';

	let { children } = $props();
	let ready = $state(false);
	let online = $state(true);
	let queuedCount = $state(0);
	const IDLE_TIMEOUT_MS = 8 * 60 * 60 * 1000;

	onMount(() => {
		let idleTimer: ReturnType<typeof setTimeout>;

		async function logoutAndRedirect() {
			await revokeCurrentSession();
			auth.logout();
			await goto('/login', { replaceState: true });
		}

		function resetIdleTimer() {
			clearTimeout(idleTimer);
			if (localStorage.getItem('access_token')) {
				idleTimer = setTimeout(() => {
					void logoutAndRedirect();
				}, IDLE_TIMEOUT_MS);
			}
		}

		online = navigator.onLine;
		const unsubscribeQueue = subscribeQueueCount((count) => {
			queuedCount = count;
		});
		const updateOnline = () => {
			online = navigator.onLine;
			if (online) {
				void drainOfflineQueue(API_BASE, localStorage.getItem('access_token'));
			}
		};
		window.addEventListener('online', updateOnline);
		window.addEventListener('offline', updateOnline);
		window.addEventListener('mousemove', resetIdleTimer);
		window.addEventListener('keydown', resetIdleTimer);
		window.addEventListener('touchstart', resetIdleTimer);

		async function checkSession() {
			const publicPaths = ['/login', '/register', '/offline'];
			if (
				publicPaths.includes(page.url.pathname) ||
				page.url.pathname.startsWith('/login') ||
				page.url.pathname.startsWith('/register')
			) {
				ready = true;
				return;
			}

			const token = localStorage.getItem('access_token');
			if (!token) {
				await goto('/login', { replaceState: true });
				ready = true;
				return;
			}

			try {
				const user = await apiJson<any>('/auth/me');
				auth.login(user, token);
				ready = true;
			} catch {
				auth.logout();
				await goto('/login', { replaceState: true });
				ready = true;
			}
		}

		void checkSession();
		resetIdleTimer();

		return () => {
			clearTimeout(idleTimer);
			unsubscribeQueue();
			window.removeEventListener('online', updateOnline);
			window.removeEventListener('offline', updateOnline);
			window.removeEventListener('mousemove', resetIdleTimer);
			window.removeEventListener('keydown', resetIdleTimer);
			window.removeEventListener('touchstart', resetIdleTimer);
		};
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<link rel="manifest" href="/manifest.webmanifest" />
	<meta name="theme-color" content="#8B2635" />
</svelte:head>

{#if ready}
	<div
		class="fixed bottom-3 right-3 z-80 flex items-center gap-2 rounded-full border bg-background/95 px-3 py-1.5 text-xs shadow-sm backdrop-blur"
		role="status"
		aria-live="polite"
	>
		<span
			class="size-2 rounded-full {online ? 'bg-green-600' : queuedCount > 0 ? 'bg-amber-500' : 'bg-destructive'}"
			aria-hidden="true"
		></span>
		<span>
			{#if online}
				Online{#if queuedCount > 0} · syncing {queuedCount}{/if}
			{:else if queuedCount > 0}
				Offline · {queuedCount} queued
			{:else}
				Offline
			{/if}
		</span>
	</div>
	{@render children()}
{:else}
	<div class="min-h-screen bg-muted/30 flex items-center justify-center px-4">
		<div class="rounded-2xl border bg-background p-6 text-center shadow-sm">
			<div class="mx-auto mb-3 size-8 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
			<p class="text-sm font-medium">Loading UpScale POS</p>
			<p class="mt-1 text-xs text-muted-foreground">Checking your secure session...</p>
		</div>
	</div>
{/if}
