<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import { onMount } from 'svelte';
	import { CloudOff } from 'lucide-svelte';

	let cachedProductCount = $state<number | null>(null);

	onMount(async () => {
		if (!('caches' in window)) return;
		try {
			const cache = await caches.open('upscale-products');
			const requests = await cache.keys();
			const productRequest = requests.find((request) => request.url.includes('/api/products'));
			if (!productRequest) return;

			const response = await cache.match(productRequest);
			const products = await response?.clone().json();
			cachedProductCount = Array.isArray(products) ? products.length : null;
		} catch {
			cachedProductCount = null;
		}
	});
</script>

<svelte:head>
	<title>Offline | UpScale POS</title>
</svelte:head>

<main class="min-h-screen bg-muted/30 px-4 py-8">
	<section class="mx-auto flex max-w-md flex-col items-center rounded-2xl border bg-background p-6 text-center shadow-sm">
		<div class="mb-4 rounded-full bg-amber-500/10 p-4 text-amber-700">
			<CloudOff class="size-8" />
		</div>
		<h1 class="text-xl font-semibold">You are offline.</h1>
		<p class="mt-2 text-sm text-muted-foreground">
			The POS will resume when connection is restored. Cached products and queued invoices will be used when available.
		</p>
		{#if cachedProductCount !== null}
			<p class="mt-3 rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground" role="status">
				Cached products available: {cachedProductCount}
			</p>
		{/if}
		<Button class="mt-5" onclick={() => goto('/pos')}>Return to POS</Button>
	</section>
</main>
