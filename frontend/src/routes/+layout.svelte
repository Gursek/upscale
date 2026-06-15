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
		if (publicPaths.includes(page.url.pathname)) {
			ready = true;
			return;
		}

		const token = localStorage.getItem('access_token');
		if (!token) {
			await goto('/login', { replaceState: true });
			return;
		}

		try {
			const user = await apiJson<any>('/auth/me');
			auth.login(user, token);
			ready = true;
		} catch {
			auth.logout();
			await goto('/login', { replaceState: true });
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if ready}
	{@render children()}
{/if}
