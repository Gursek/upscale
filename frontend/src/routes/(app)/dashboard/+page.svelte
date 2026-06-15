<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { Button } from "$lib/components/ui/button";
    import * as Dialog from "$lib/components/ui/dialog";
    import {
        AlertTriangle, Beef, Carrot, Check, CloudOff, FileBarChart, Fish, LayoutDashboard,
        Loader2, LogOut, Package, PhilippinePeso, ReceiptText, RefreshCw, Settings, ShoppingBag,
        ShoppingCart, Truck, Wifi
    } from "lucide-svelte";

    let loading = $state(true);
    let chartLoading = $state(false);
    let error = $state("");
    let dashboard = $state<any>(null);
    let onboardingOpen = $state(false);
    let onboardingLoading = $state(false);
    let sellsMeat = $state(false);
    let sellsFish = $state(false);
    let sellsRetail = $state(false);
    let sellsVeggies = $state(false);
    let online = $state(true);
    let chartRange = $state<"hours" | "days" | "months">("days");
    let user = $derived($auth);
    let maxDailySales = $derived(
        Math.max(1, ...(dashboard?.sales_series ?? []).map((point: any) => point.total))
    );

    onMount(() => {
        online = navigator.onLine;
        const setOnline = () => online = true;
        const setOffline = () => online = false;
        window.addEventListener("online", setOnline);
        window.addEventListener("offline", setOffline);
        loadDashboard();
        return () => {
            window.removeEventListener("online", setOnline);
            window.removeEventListener("offline", setOffline);
        };
    });

    async function loadDashboard() {
        const token = localStorage.getItem("access_token");
        if (!token) {
            goto("/login");
            return;
        }
        loading = true;
        try {
            const currentUser = await apiJson<any>("/auth/me");
            auth.login(currentUser, token);
            sellsMeat = currentUser.sells_meat ?? false;
            sellsFish = currentUser.sells_fish ?? false;
            sellsRetail = currentUser.sells_retail ?? false;
            sellsVeggies = currentUser.sells_veggies ?? false;
            onboardingOpen = !currentUser.onboarding_completed;
            dashboard = await apiJson<any>(`/dashboard/?range=${chartRange}`);
        } catch (e: any) {
            error = e.message || "Failed to load dashboard";
        } finally {
            loading = false;
        }
    }

    async function changeChartRange(range: typeof chartRange) {
        if (range === chartRange || chartLoading) return;
        chartRange = range;
        chartLoading = true;
        try {
            const result = await apiJson<any>(`/dashboard/?range=${chartRange}`);
            if (dashboard) {
                dashboard = {
                    ...dashboard,
                    sales_range: result.sales_range,
                    sales_series: result.sales_series,
                };
            }
        } catch (e: any) {
            error = e.message || "Failed to load sales history";
        } finally {
            chartLoading = false;
        }
    }

    async function completeOnboarding() {
        if (!sellsMeat && !sellsFish && !sellsRetail && !sellsVeggies) {
            error = "Select at least one product type";
            return;
        }
        onboardingLoading = true;
        try {
            await apiJson("/auth/onboarding", {
                method: "POST",
                body: JSON.stringify({
                    sells_meat: sellsMeat,
                    sells_fish: sellsFish,
                    sells_retail: sellsRetail,
                    sells_veggies: sellsVeggies,
                }),
            });
            auth.update((current) => current ? {
                ...current,
                sells_meat: sellsMeat,
                sells_fish: sellsFish,
                sells_retail: sellsRetail,
                sells_veggies: sellsVeggies,
                onboarding_completed: true,
            } : current);
            onboardingOpen = false;
        } catch (e: any) {
            error = e.message;
        } finally {
            onboardingLoading = false;
        }
    }

    function logout() {
        auth.logout();
        goto("/login");
    }

    function formatCurrency(value: number) {
        return new Intl.NumberFormat("en-PH", {
            style: "currency",
            currency: "PHP",
        }).format(value);
    }
</script>

<div class="min-h-screen bg-muted/30">
    <header class="bg-background border-b px-4 py-3 sticky top-0 z-10">
        <div class="max-w-6xl mx-auto flex items-center gap-3">
            <LayoutDashboard class="size-5 text-primary" />
            <div class="flex-1">
                <h1 class="font-semibold text-sm">{user?.business_name ?? "UpScale POS"}</h1>
                <p class="text-xs text-muted-foreground">Business dashboard</p>
            </div>
            <div class="flex items-center gap-1 text-xs {online ? 'text-green-700' : 'text-destructive'}" role="status">
                {#if online}<Wifi class="size-3.5" /> Online{:else}<CloudOff class="size-3.5" /> Offline{/if}
            </div>
            <Button variant="ghost" size="icon" class="hover:!bg-primary hover:!text-primary-foreground" aria-label="Refresh dashboard" onclick={loadDashboard}>
                <RefreshCw class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="hover:!bg-primary hover:!text-primary-foreground" aria-label="Settings" onclick={() => goto("/settings")}>
                <Settings class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="hover:!bg-primary hover:!text-primary-foreground" aria-label="Log out" onclick={logout}>
                <LogOut class="size-4" />
            </Button>
        </div>
    </header>

    {#if error}
        <div class="bg-destructive/10 text-destructive text-sm px-4 py-2 text-center" role="alert">{error}</div>
    {/if}

    <main class="max-w-6xl mx-auto p-4 space-y-5">
        {#if loading}
            <div class="h-64 flex items-center justify-center">
                <Loader2 class="size-6 animate-spin text-muted-foreground" />
            </div>
        {:else if dashboard}
            <section class="grid grid-cols-2 lg:grid-cols-4 gap-3" aria-label="Today's summary">
                <div class="bg-background rounded-xl border p-4">
                    <PhilippinePeso class="size-5 text-primary mb-3" />
                    <p class="text-xs text-muted-foreground">Today's sales</p>
                    <p class="text-xl font-semibold mt-1">{formatCurrency(dashboard.today_sales)}</p>
                </div>
                <div class="bg-background rounded-xl border p-4">
                    <ReceiptText class="size-5 text-primary mb-3" />
                    <p class="text-xs text-muted-foreground">Transactions</p>
                    <p class="text-xl font-semibold mt-1">{dashboard.transaction_count}</p>
                </div>
                <div class="bg-background rounded-xl border p-4">
                    <AlertTriangle class="size-5 text-amber-600 mb-3" />
                    <p class="text-xs text-muted-foreground">Low stock alerts</p>
                    <p class="text-xl font-semibold mt-1">{dashboard.low_stock_count}</p>
                </div>
                <div class="bg-background rounded-xl border p-4">
                    <CloudOff class="size-5 text-primary mb-3" />
                    <p class="text-xs text-muted-foreground">Unsynced invoices</p>
                    <p class="text-xl font-semibold mt-1">{dashboard.pending_sync_count}</p>
                </div>
            </section>

            <nav class="grid grid-cols-2 md:grid-cols-5 gap-3" aria-label="Quick access">
                <Button variant="outline" class="h-16 gap-2 hover:!bg-primary hover:!text-primary-foreground active:translate-y-0" onclick={() => goto("/pos")}><ShoppingCart class="size-5" /> Open POS</Button>
                <Button variant="outline" class="h-16 gap-2 hover:!bg-primary hover:!text-primary-foreground active:translate-y-0" onclick={() => goto("/inventory")}><Package class="size-5" /> Inventory</Button>
                <Button variant="outline" class="h-16 gap-2 hover:!bg-primary hover:!text-primary-foreground active:translate-y-0" onclick={() => goto("/invoices")}><ReceiptText class="size-5" /> Invoices</Button>
                <Button variant="outline" class="h-16 gap-2 hover:!bg-primary hover:!text-primary-foreground active:translate-y-0" onclick={() => goto("/suppliers")}><Truck class="size-5" /> Suppliers</Button>
                <Button variant="outline" class="h-16 gap-2 hover:!bg-primary hover:!text-primary-foreground active:translate-y-0" onclick={() => goto("/reports")}><FileBarChart class="size-5" /> Reports</Button>
            </nav>

            <div class="grid lg:grid-cols-2 gap-4">
                <section class="bg-background rounded-xl border p-4">
                    <div class="flex items-center justify-between gap-2 mb-4">
                        <h2 class="font-semibold text-sm">Sales history</h2>
                        <div class="flex gap-1">
                            <Button variant={chartRange === "hours" ? "default" : "outline"} size="sm" onclick={() => changeChartRange("hours")}>Hours</Button>
                            <Button variant={chartRange === "days" ? "default" : "outline"} size="sm" onclick={() => changeChartRange("days")}>Days</Button>
                            <Button variant={chartRange === "months" ? "default" : "outline"} size="sm" onclick={() => changeChartRange("months")}>Months</Button>
                        </div>
                    </div>
                    <div class="h-44 relative" aria-label="Daily sales chart" aria-busy={chartLoading}>
                        {#if chartLoading}
                            <div class="absolute inset-0 flex items-center justify-center bg-background/70 z-10 rounded-lg">
                                <Loader2 class="size-5 animate-spin text-primary" />
                            </div>
                        {/if}
                        <div class="h-full flex items-end gap-2 transition-opacity {chartLoading ? 'opacity-40' : 'opacity-100'}">
                            {#each dashboard.sales_series as point}
                                <div class="flex-1 h-full flex flex-col justify-end items-center gap-1">
                                    <span class="text-[10px] text-muted-foreground">{formatCurrency(point.total)}</span>
                                    <div
                                        class="w-full bg-primary rounded-t-lg min-h-1"
                                        style="height: {Math.max(3, (point.total / maxDailySales) * 85)}%"
                                        title="{point.label}: {formatCurrency(point.total)}"
                                    ></div>
                                    <span class="text-[10px] text-muted-foreground text-center">{point.label}</span>
                                </div>
                            {/each}
                        </div>
                    </div>
                </section>

                <section class="bg-background rounded-xl border p-4">
                    <div class="flex items-center justify-between mb-3">
                        <h2 class="font-semibold text-sm">Low stock</h2>
                        <Button variant="ghost" size="sm" onclick={() => goto("/inventory")}>View inventory</Button>
                    </div>
                    {#if dashboard.low_stock_products.length === 0}
                        <p class="text-sm text-muted-foreground py-8 text-center">No low stock products.</p>
                    {:else}
                        <ul class="divide-y">
                            {#each dashboard.low_stock_products as product}
                                <li class="py-2 flex justify-between gap-3 text-sm">
                                    <span class="font-medium">{product.name}</span>
                                    <span class="text-destructive">{product.stock_quantity} {product.unit} left</span>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </section>
            </div>

            <section class="bg-background rounded-xl border p-4">
                <div class="flex items-center justify-between mb-3">
                    <h2 class="font-semibold text-sm">Recent transactions</h2>
                    <Button variant="ghost" size="sm" onclick={() => goto("/invoices")}>View all</Button>
                </div>
                {#if dashboard.recent_transactions.length === 0}
                    <p class="text-sm text-muted-foreground py-8 text-center">No transactions yet.</p>
                {:else}
                    <ul class="divide-y">
                        {#each dashboard.recent_transactions as transaction}
                            <li class="py-3 flex items-center gap-3">
                                <ReceiptText class="size-4 text-muted-foreground" />
                                <div class="flex-1">
                                    <p class="font-mono text-sm">#{transaction.invoice_number}</p>
                                    <p class="text-xs text-muted-foreground">{new Date(transaction.date_time).toLocaleString("en-PH", { timeZone: "Asia/Manila" })}</p>
                                </div>
                                <span class="text-xs capitalize {transaction.status === 'voided' ? 'text-destructive' : 'text-green-700'}">{transaction.status}</span>
                                <span class="font-semibold text-sm">{formatCurrency(transaction.total_amount)}</span>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </section>
        {/if}
    </main>
</div>

<Dialog.Root bind:open={onboardingOpen} onOpenChange={(open) => onboardingOpen = user?.onboarding_completed ? open : true}>
    <Dialog.Content class="max-w-md" showCloseButton={false} onEscapeKeydown={(event) => event.preventDefault()}>
        <Dialog.Header>
            <Dialog.Title>Welcome to UpScale POS</Dialog.Title>
            <Dialog.Description>Tell us what you sell so the POS can show the right product categories.</Dialog.Description>
        </Dialog.Header>
        <div class="grid grid-cols-2 gap-3">
            <button
                onclick={() => sellsMeat = !sellsMeat}
                aria-pressed={sellsMeat}
                class="relative rounded-xl border-2 p-5 text-left {sellsMeat ? 'border-primary bg-primary/5' : 'border-border'}"
            >
                {#if sellsMeat}<Check class="absolute top-2 right-2 size-4 text-primary" />{/if}
                <Beef class="size-7 mb-2" />
                <span class="font-medium text-sm">Meat Products</span>
                <span class="block text-xs text-muted-foreground mt-1">Cuts priced per kilogram</span>
            </button>
            <button
                onclick={() => sellsFish = !sellsFish}
                aria-pressed={sellsFish}
                class="relative rounded-xl border-2 p-5 text-left {sellsFish ? 'border-primary bg-primary/5' : 'border-border'}"
            >
                {#if sellsFish}<Check class="absolute top-2 right-2 size-4 text-primary" />{/if}
                <Fish class="size-7 mb-2" />
                <span class="font-medium text-sm">Fish</span>
                <span class="block text-xs text-muted-foreground mt-1">Fresh fish priced by weight</span>
            </button>
            <button
                onclick={() => sellsRetail = !sellsRetail}
                aria-pressed={sellsRetail}
                class="relative rounded-xl border-2 p-5 text-left {sellsRetail ? 'border-primary bg-primary/5' : 'border-border'}"
            >
                {#if sellsRetail}<Check class="absolute top-2 right-2 size-4 text-primary" />{/if}
                <ShoppingBag class="size-7 mb-2" />
                <span class="font-medium text-sm">Retail Products</span>
                <span class="block text-xs text-muted-foreground mt-1">Fixed-price packaged goods</span>
            </button>
            <button
                onclick={() => sellsVeggies = !sellsVeggies}
                aria-pressed={sellsVeggies}
                class="relative rounded-xl border-2 p-5 text-left {sellsVeggies ? 'border-primary bg-primary/5' : 'border-border'}"
            >
                {#if sellsVeggies}<Check class="absolute top-2 right-2 size-4 text-primary" />{/if}
                <Carrot class="size-7 mb-2" />
                <span class="font-medium text-sm">Veggies</span>
                <span class="block text-xs text-muted-foreground mt-1">Produce priced by weight or piece</span>
            </button>
        </div>
        <Dialog.Footer>
            <Button class="w-full" onclick={completeOnboarding} disabled={onboardingLoading || (!sellsMeat && !sellsFish && !sellsRetail && !sellsVeggies)} aria-busy={onboardingLoading}>
                {#if onboardingLoading}<Loader2 class="size-4 animate-spin mr-2" />{/if}
                Continue to dashboard
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
