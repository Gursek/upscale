<script lang="ts">
    import { onMount } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import {
        ArrowLeft, Settings, Loader2, Beef, ShoppingBag, Check
    } from "lucide-svelte";

    let loading = $state(true);
    let saving = $state(false);
    let error = $state("");
    let successMessage = $state("");

    let email = $state("");
    let businessName = $state("");
    let businessAddress = $state("");
    let tin = $state("");
    let vatStatus = $state("non_vat");
    let sellsMeat = $state(false);
    let sellsRetail = $state(false);

    onMount(async () => {
        const token = localStorage.getItem("access_token");
        if (!token) { goto("/login"); return; }

        try {
            const user = await apiJson<any>("/auth/me");
            email = user.email;
            businessName = user.business_name ?? "";
            businessAddress = user.business_address ?? "";
            tin = user.tin ?? "";
            vatStatus = user.vat_status ?? "non_vat";
            sellsMeat = user.sells_meat ?? false;
            sellsRetail = user.sells_retail ?? false;
        } catch {
            error = "Failed to load settings";
        } finally {
            loading = false;
        }
    });

    function flash(msg: string, isError = false) {
        if (isError) { error = msg; setTimeout(() => error = "", 4000); }
        else { successMessage = msg; setTimeout(() => successMessage = "", 3000); }
    }

    async function saveSettings() {
        if (!businessName.trim()) {
            flash("Business name is required", true);
            return;
        }
        if (!sellsMeat && !sellsRetail) {
            flash("Please select at least one product type", true);
            return;
        }

        saving = true;
        error = "";
        try {
            const user = await apiJson<any>("/auth/me", {
                method: "PUT",
                body: JSON.stringify({
                    business_name: businessName.trim(),
                    business_address: businessAddress.trim() || null,
                    tin: tin.trim() || null,
                    vat_status: vatStatus,
                    sells_meat: sellsMeat,
                    sells_retail: sellsRetail,
                }),
            });
            auth.update((u) => u ? { ...u, ...user } : u);
            flash("Settings saved");
        } catch (e: any) {
            flash(e.message, true);
        } finally {
            saving = false;
        }
    }
</script>

<div class="min-h-screen bg-muted/30">

    <header class="bg-background border-b px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <Button variant="ghost" size="icon" aria-label="Back to POS" onclick={() => goto("/pos")}>
            <ArrowLeft class="size-4" />
        </Button>
        <Settings class="size-5 text-primary" />
        <h1 class="font-semibold text-sm flex-1">Settings</h1>
    </header>

    {#if error}
        <div class="bg-destructive/10 text-destructive text-sm px-4 py-2 text-center" role="alert">{error}</div>
    {/if}
    {#if successMessage}
        <div class="bg-green-500/10 text-green-700 text-sm px-4 py-2 text-center" role="status">{successMessage}</div>
    {/if}

    <div class="max-w-md mx-auto p-4">
        {#if loading}
            <div class="flex items-center justify-center h-40">
                <Loader2 class="size-6 animate-spin text-muted-foreground" />
            </div>
        {:else}
            <form class="space-y-6" onsubmit={(e) => { e.preventDefault(); saveSettings(); }}>

                <section class="bg-background rounded-xl border p-4 space-y-4">
                    <h2 class="font-medium text-sm">Business Information</h2>

                    <div class="space-y-2">
                        <Label for="business-name">Business Name</Label>
                        <Input id="business-name" placeholder="VDA Meat Shop" bind:value={businessName} />
                    </div>

                    <div class="space-y-2">
                        <Label for="business-address">Business Address</Label>
                        <textarea
                            id="business-address"
                            placeholder="Bagac, Bataan, Philippines"
                            bind:value={businessAddress}
                            rows="2"
                            class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                            aria-label="Business address"
                        ></textarea>
                    </div>

                    <div class="space-y-2">
                        <Label for="tin">TIN</Label>
                        <Input id="tin" placeholder="000-000-000-000" bind:value={tin} />
                    </div>

                    <div class="space-y-2">
                        <Label for="vat-status">VAT Status</Label>
                        <select
                            id="vat-status"
                            bind:value={vatStatus}
                            class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            aria-label="VAT status"
                        >
                            <option value="non_vat">Non-VAT (under ₱3M/year)</option>
                            <option value="vat">VAT Registered (12%)</option>
                        </select>
                        <p class="text-xs text-muted-foreground">
                            Affects tax classification on retail products. Meat products are always VAT-exempt.
                        </p>
                    </div>
                </section>

                <section class="bg-background rounded-xl border p-4 space-y-4">
                    <h2 class="font-medium text-sm">Product Types</h2>
                    <p class="text-xs text-muted-foreground -mt-2">
                        Controls which categories appear on the POS screen.
                    </p>

                    <div class="grid grid-cols-2 gap-3">
                        <button
                            type="button"
                            onclick={() => sellsMeat = !sellsMeat}
                            aria-pressed={sellsMeat}
                            aria-label="Toggle meat products"
                            class="relative rounded-xl border-2 p-4 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                                {sellsMeat
                                    ? 'border-primary bg-primary/5'
                                    : 'border-border bg-background hover:border-primary/40'}"
                        >
                            {#if sellsMeat}
                                <div class="absolute top-2 right-2 bg-primary text-primary-foreground rounded-full p-0.5">
                                    <Check class="size-3" />
                                </div>
                            {/if}
                            <Beef class="size-6 mb-2 {sellsMeat ? 'text-primary' : 'text-muted-foreground'}" />
                            <p class="font-medium text-xs">Meat Products</p>
                        </button>

                        <button
                            type="button"
                            onclick={() => sellsRetail = !sellsRetail}
                            aria-pressed={sellsRetail}
                            aria-label="Toggle retail products"
                            class="relative rounded-xl border-2 p-4 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                                {sellsRetail
                                    ? 'border-primary bg-primary/5'
                                    : 'border-border bg-background hover:border-primary/40'}"
                        >
                            {#if sellsRetail}
                                <div class="absolute top-2 right-2 bg-primary text-primary-foreground rounded-full p-0.5">
                                    <Check class="size-3" />
                                </div>
                            {/if}
                            <ShoppingBag class="size-6 mb-2 {sellsRetail ? 'text-primary' : 'text-muted-foreground'}" />
                            <p class="font-medium text-xs">Retail Products</p>
                        </button>
                    </div>
                </section>

                <section class="bg-background rounded-xl border p-4 space-y-2">
                    <h2 class="font-medium text-sm">Account</h2>
                    <div class="space-y-2">
                        <Label for="email">Email</Label>
                        <Input id="email" type="email" value={email} disabled aria-label="Email address" />
                        <p class="text-xs text-muted-foreground">Email cannot be changed.</p>
                    </div>
                </section>

                <Button
                    type="submit"
                    class="w-full"
                    disabled={saving || !businessName.trim() || (!sellsMeat && !sellsRetail)}
                    aria-busy={saving}
                >
                    {#if saving}
                        <Loader2 class="size-4 animate-spin mr-2" />
                        Saving...
                    {:else}
                        Save Settings
                    {/if}
                </Button>
            </form>
        {/if}
    </div>
</div>
