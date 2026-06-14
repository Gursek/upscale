<script lang="ts">
    import { goto } from "$app/navigation";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { Button } from "$lib/components/ui/button";
    import { Beef, ShoppingBag, Check, Loader2 } from "lucide-svelte";

    let sellsMeat = $state(false);
    let sellsRetail = $state(false);
    let loading = $state(false);
    let error = $state("");

    async function handleComplete() {
        if (!sellsMeat && !sellsRetail) {
            error = "Please select at least one product type";
            return;
        }
        error = "";
        loading = true;
        try {
            await apiJson("/auth/onboarding", {
                method: "POST",
                body: JSON.stringify({
                    sells_meat: sellsMeat,
                    sells_retail: sellsRetail,
                }),
            });
            auth.update((u) => u ? {
                ...u,
                sells_meat: sellsMeat,
                sells_retail: sellsRetail,
                onboarding_completed: true,
            } : u);
            goto("/pos");
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    }
</script>

<div class="min-h-screen flex items-center justify-center bg-muted/40 p-4">
    <div class="w-full max-w-md space-y-6">

        <!-- Header -->
        <div class="text-center space-y-2">
            <h1 class="text-2xl font-semibold tracking-tight">Welcome to UpScale POS</h1>
            <p class="text-muted-foreground text-sm">
                Tell us what you sell so we can tailor your experience.
            </p>
        </div>

        {#if error}
            <div class="bg-destructive/10 text-destructive text-sm rounded-md px-3 py-2 text-center">
                {error}
            </div>
        {/if}

        <!-- Selection cards -->
        <div class="grid grid-cols-2 gap-4">

            <!-- Meat Products -->
            <button
                onclick={() => sellsMeat = !sellsMeat}
                aria-pressed={sellsMeat}
                aria-label="Toggle meat products"
                class="relative rounded-xl border-2 p-6 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                    {sellsMeat
                        ? 'border-primary bg-primary/5'
                        : 'border-border bg-background hover:border-primary/40'}"
            >
                {#if sellsMeat}
                    <div class="absolute top-3 right-3 bg-primary text-primary-foreground rounded-full p-0.5">
                        <Check class="size-3" />
                    </div>
                {/if}
                <Beef class="size-8 mb-3 {sellsMeat ? 'text-primary' : 'text-muted-foreground'}" />
                <p class="font-medium text-sm">Meat Products</p>
                <p class="text-muted-foreground text-xs mt-1">
                    Beef, pork, chicken cuts — priced per kg
                </p>
            </button>

            <!-- Retail Products -->
            <button
                onclick={() => sellsRetail = !sellsRetail}
                aria-pressed={sellsRetail}
                aria-label="Toggle retail products"
                class="relative rounded-xl border-2 p-6 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                    {sellsRetail
                        ? 'border-primary bg-primary/5'
                        : 'border-border bg-background hover:border-primary/40'}"
            >
                {#if sellsRetail}
                    <div class="absolute top-3 right-3 bg-primary text-primary-foreground rounded-full p-0.5">
                        <Check class="size-3" />
                    </div>
                {/if}
                <ShoppingBag class="size-8 mb-3 {sellsRetail ? 'text-primary' : 'text-muted-foreground'}" />
                <p class="font-medium text-sm">Retail Products</p>
                <p class="text-muted-foreground text-xs mt-1">
                    Packaged goods — fixed price per piece
                </p>
            </button>

        </div>

        <Button
            class="w-full"
            onclick={handleComplete}
            disabled={loading || (!sellsMeat && !sellsRetail)}
            aria-busy={loading}
        >
            {#if loading}
                <Loader2 class="size-4 animate-spin mr-2" />
                Setting up...
            {:else}
                Continue to POS
            {/if}
        </Button>

        <p class="text-center text-xs text-muted-foreground">
            You can change these preferences later in Settings.
        </p>

    </div>
</div>