<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiJson } from '$lib/api';
	import { auth } from '$lib/stores/auth';

	let { children } = $props();
	let ready = $state(false);

	onMount(async () => {
		const publicPaths = ['/login', '/register'];
		if (publicPaths.includes(page.url.pathname) || page.url.pathname.startsWith('/login') || page.url.pathname.startsWith('/register')) {
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
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if ready}
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
