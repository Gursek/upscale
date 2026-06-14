<script lang="ts">
    import { onMount } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { cart, cartTotal } from "$lib/stores/cart";
    import { apiJson, apiFetch, API_BASE } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Separator } from "$lib/components/ui/separator";
    import * as Sheet from "$lib/components/ui/sheet";
    import {
        ShoppingBasket, ShoppingCart, Trash2, Loader2,
        Scale, LayoutGrid, Package, ReceiptText,
        Users, LogOut, Settings, Plus, Minus,
        ScanLine, X
    } from "lucide-svelte";

    // --- State ---
    let products = $state<any[]>([]);
    let activeCategory = $state("all");
    let selectedProduct = $state<any>(null);
    let weightInput = $state("");
    let loadingProducts = $state(true);
    let checkoutLoading = $state(false);
    let scaleLoading = $state(false);
    let error = $state("");
    let successMessage = $state("");
    let cartOpen = $state(false);

    // --- Derived ---
    let user = $derived($auth);

    let categories = $derived(() => {
        const cats: string[] = ["all"];
        if (user?.sells_meat) cats.push("beef", "pork", "chicken");
        if (user?.sells_retail) cats.push("retail");
        return cats;
    });

    let filteredProducts = $derived(
        activeCategory === "all"
            ? products
            : products.filter((p) => p.category === activeCategory)
    );

    let cartItems = $derived($cart);
    let total = $derived($cartTotal);

    let computedPrice = $derived(() => {
        if (!selectedProduct || !weightInput) return 0;
        const w = parseFloat(weightInput);
        if (isNaN(w) || w <= 0) return 0;
        return Number((selectedProduct.price * w).toFixed(2));
    });

    // --- Load ---
    onMount(async () => {
        const token = localStorage.getItem("access_token");
        if (!token) { goto("/login"); return; }
        try {
            products = await apiJson<any[]>("/products/");
        } catch {
            error = "Failed to load products";
        } finally {
            loadingProducts = false;
        }
    });

    // --- Actions ---
    function selectProduct(product: any) {
        if (product.pricing_type === "fixed") {
            cart.addItem(product, 1);
            successMessage = `${product.name} added`;
            setTimeout(() => successMessage = "", 2000);
        } else {
            selectedProduct = product;
            weightInput = "";
        }
    }

    function clearSelected() {
        selectedProduct = null;
        weightInput = "";
    }

    async function readScale() {
        scaleLoading = true;
        try {
            const res = await apiFetch("/scale/read");
            const data = await res.json();
            if (data.weight_kg !== undefined) {
                weightInput = data.weight_kg.toFixed(3);
            } else {
                error = "Could not read scale";
                setTimeout(() => error = "", 3000);
            }
        } catch {
            error = "Scale not connected";
            setTimeout(() => error = "", 3000);
        } finally {
            scaleLoading = false;
        }
    }

    function addToCart() {
        if (!selectedProduct) return;
        const qty = parseFloat(weightInput);
        if (!qty || qty <= 0) return;
        cart.addItem(selectedProduct, qty);
        clearSelected();
        successMessage = "Added to cart";
        setTimeout(() => successMessage = "", 2000);
    }

    async function checkout() {
        if (cartItems.length === 0) return;
        checkoutLoading = true;
        error = "";
        try {
            const invoice = await apiJson<any>("/invoices/", {
                method: "POST",
                body: JSON.stringify({
                    items: cartItems.map((i) => ({
                        product_id: i.product_id,
                        quantity: i.quantity,
                    })),
                    invoice_type: "cash",
                }),
            });
            cart.clear();
            cartOpen = false;
            successMessage = `Invoice #${invoice.invoice_number} — ₱${Number(invoice.total_amount).toFixed(2)}`;
            setTimeout(() => successMessage = "", 5000);
        } catch (e: any) {
            error = e.message;
        } finally {
            checkoutLoading = false;
        }
    }

    function logout() {
        auth.logout();
        goto("/login");
    }

    const categoryLabels: Record<string, string> = {
        all: "All", beef: "Beef", pork: "Pork",
        chicken: "Chicken", retail: "Retail"
    };

    const categoryEmoji: Record<string, string> = {
        beef: "🥩", pork: "🥓", chicken: "🍗", retail: "📦"
    };

    function getProductImage(product: any): string | null {
        if (!product.image_url) return null;
        if (product.image_url.startsWith("http")) return product.image_url;
        return `${API_BASE.replace("/api", "")}${product.image_url}`;
    }
</script>

<div class="flex flex-col h-screen bg-[hsl(var(--background))]">

    <!-- Header -->
    <header class="bg-card border-b border-border px-4 h-12 flex items-center justify-between shrink-0 shadow-sm">
        <div class="flex items-center gap-2">
            <ShoppingBasket class="size-4 text-primary" />
            <span class="font-semibold text-sm tracking-tight">{user?.business_name ?? "UpScale POS"}</span>
        </div>
        <nav class="flex items-center" aria-label="Main navigation">
            <Button variant="ghost" size="icon" class="size-8" aria-label="Inventory" onclick={() => goto("/inventory")}>
                <Package class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-8" aria-label="Sales history" onclick={() => goto("/invoices")}>
                <ReceiptText class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-8" aria-label="Suppliers" onclick={() => goto("/suppliers")}>
                <Users class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-8" aria-label="Settings" onclick={() => goto("/settings")}>
                <Settings class="size-4" />
            </Button>
            <div class="w-px h-4 bg-border mx-1"></div>
            <Button variant="ghost" size="icon" class="size-8" aria-label="Log out" onclick={logout}>
                <LogOut class="size-4" />
            </Button>
        </nav>
    </header>

    <!-- Alerts -->
    {#if error}
        <div class="bg-destructive/10 text-destructive text-xs px-4 py-1.5 text-center shrink-0" role="alert">
            {error}
        </div>
    {/if}
    {#if successMessage}
        <div class="bg-green-600/10 text-green-700 text-xs px-4 py-1.5 text-center shrink-0" role="status">
            {successMessage}
        </div>
    {/if}

    <!-- Main -->
    <div class="flex flex-1 overflow-hidden">

        <!-- LEFT: Product area -->
        <div class="flex flex-col flex-1 overflow-hidden">

            <!-- Category tabs -->
            <div class="bg-card border-b border-border px-3 shrink-0">
                <div class="flex gap-0.5 overflow-x-auto py-2 scrollbar-none" role="tablist" aria-label="Product categories">
                    {#each categories() as cat}
                        <button
                            role="tab"
                            aria-selected={activeCategory === cat}
                            onclick={() => activeCategory = cat}
                            class="px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors
                                focus:outline-none focus-visible:ring-2 focus-visible:ring-ring shrink-0
                                {activeCategory === cat
                                    ? 'bg-primary text-primary-foreground'
                                    : 'text-muted-foreground hover:text-foreground hover:bg-accent'}"
                        >
                            {categoryLabels[cat] ?? cat}
                        </button>
                    {/each}
                </div>
            </div>

            <!-- Product grid -->
            <div class="flex-1 overflow-y-auto p-3">
                {#if loadingProducts}
                    <div class="flex items-center justify-center h-full">
                        <Loader2 class="size-5 animate-spin text-muted-foreground" />
                    </div>
                {:else if filteredProducts.length === 0}
                    <div class="flex flex-col items-center justify-center h-full gap-2 text-muted-foreground">
                        <LayoutGrid class="size-7" />
                        <p class="text-sm">No products</p>
                        <Button variant="outline" size="sm" onclick={() => goto("/inventory")}>
                            Add products
                        </Button>
                    </div>
                {:else}
                    <ul class="grid gap-2"
                        style="grid-template-columns: repeat(auto-fill, minmax(130px, 1fr))"
                        aria-label="Products">
                        {#each filteredProducts as product (product.id)}
                            <li>
                                <button
                                    onclick={() => selectProduct(product)}
                                    aria-label="{product.name}, ₱{product.price} per {product.unit}"
                                    aria-pressed={selectedProduct?.id === product.id}
                                    class="w-full h-32.5 rounded-xl border-2 overflow-hidden text-left transition-all
                                        focus:outline-none focus-visible:ring-2 focus-visible:ring-ring relative
                                        {selectedProduct?.id === product.id
                                            ? 'border-primary shadow-md'
                                            : 'border-border bg-card hover:border-primary/50 hover:shadow-sm'}"
                                >
                                    <!-- Image or emoji background -->
                                    {#if getProductImage(product)}
                                        <img
                                            src={getProductImage(product)}
                                            alt={product.name}
                                            class="absolute inset-0 w-full h-full object-cover opacity-20"
                                        />
                                    {/if}

                                    <div class="relative flex flex-col h-full p-2.5 justify-between">
                                        <div class="text-2xl leading-none">
                                            {product.image_url && !product.image_url.startsWith("/") && !product.image_url.startsWith("http")
                                                ? product.image_url
                                                : categoryEmoji[product.category] ?? "📦"}
                                        </div>

                                        <div>
                                            <p class="font-semibold text-xs leading-tight line-clamp-2">
                                                {product.name}
                                            </p>
                                            {#if product.cut_type}
                                                <p class="text-muted-foreground text-[10px] leading-tight">{product.cut_type}</p>
                                            {/if}
                                            <p class="text-primary font-bold text-sm mt-0.5">
                                                ₱{Number(product.price).toFixed(2)}
                                                <span class="text-muted-foreground font-normal text-[10px]">/{product.unit}</span>
                                            </p>
                                        </div>

                                        {#if product.stock_quantity <= product.low_stock_threshold && product.low_stock_threshold > 0}
                                            <div class="absolute top-1.5 right-1.5">
                                                <span class="bg-destructive text-destructive-foreground text-[9px] font-bold px-1 py-0.5 rounded">
                                                    LOW
                                                </span>
                                            </div>
                                        {/if}
                                    </div>
                                </button>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>

            <!-- Weight input panel (shows when per-kg product selected) -->
            {#if selectedProduct}
                <div class="bg-card border-t border-border p-3 shrink-0 shadow-[0_-2px_8px_rgba(0,0,0,0.06)]"
                    aria-live="polite">
                    <div class="flex items-center gap-3 max-w-2xl mx-auto">

                        <!-- Product info -->
                        <div class="min-w-0 shrink-0">
                            <p class="font-semibold text-sm leading-tight truncate max-w-35">
                                {selectedProduct.name}
                            </p>
                            <p class="text-muted-foreground text-xs">₱{selectedProduct.price}/kg</p>
                        </div>

                        <!-- Weight input -->
                        <div class="flex-1 flex items-center gap-2">
                            <div class="relative flex-1">
                                <input
                                    type="number"
                                    min="0"
                                    step="0.001"
                                    placeholder="0.000 kg"
                                    bind:value={weightInput}
                                    aria-label="Weight in kilograms"
                                    class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm
                                        font-mono focus:outline-none focus:ring-2 focus:ring-ring pr-16"
                                />
                                <span class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">
                                    kg
                                </span>
                            </div>

                            <!-- Read scale button -->
                            <Button
                                variant="outline"
                                size="sm"
                                onclick={readScale}
                                disabled={scaleLoading}
                                aria-label="Read weight from scale"
                                class="shrink-0 gap-1.5"
                            >
                                {#if scaleLoading}
                                    <Loader2 class="size-3.5 animate-spin" />
                                {:else}
                                    <ScanLine class="size-3.5" />
                                {/if}
                                Read Scale
                            </Button>
                        </div>

                        <!-- Price preview -->
                        <div class="text-right shrink-0 min-w-20">
                            <p class="text-xs text-muted-foreground">Total</p>
                            <p class="font-bold text-primary text-base">
                                ₱{computedPrice().toFixed(2)}
                            </p>
                        </div>

                        <!-- Add to cart -->
                        <Button
                            onclick={addToCart}
                            disabled={!weightInput || parseFloat(weightInput) <= 0}
                            class="shrink-0"
                            aria-label="Add {selectedProduct.name} to cart"
                        >
                            <Plus class="size-4 mr-1" />
                            Add
                        </Button>

                        <!-- Dismiss -->
                        <button
                            onclick={clearSelected}
                            aria-label="Cancel selection"
                            class="text-muted-foreground hover:text-foreground transition-colors p-1
                                focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
                        >
                            <X class="size-4" />
                        </button>
                    </div>
                </div>
            {/if}
        </div>

        <!-- RIGHT: Cart (desktop) -->
        <aside class="hidden lg:flex flex-col w-72 bg-card border-l border-border" aria-label="Shopping cart">
            <div class="px-4 py-3 border-b border-border flex items-center justify-between">
                <h2 class="font-semibold text-sm flex items-center gap-1.5">
                    <ShoppingCart class="size-4" />
                    Cart
                    {#if cartItems.length > 0}
                        <span class="bg-primary text-primary-foreground text-[10px] font-bold
                            rounded-full size-4 flex items-center justify-center">
                            {cartItems.length}
                        </span>
                    {/if}
                </h2>
                {#if cartItems.length > 0}
                    <button
                        onclick={() => cart.clear()}
                        aria-label="Clear cart"
                        class="text-xs text-muted-foreground hover:text-destructive transition-colors
                            focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded px-1">
                        Clear
                    </button>
                {/if}
            </div>

            <!-- Cart items -->
            <div class="flex-1 overflow-y-auto">
                {#if cartItems.length === 0}
                    <div class="flex flex-col items-center justify-center h-full gap-2 text-muted-foreground py-8">
                        <ShoppingCart class="size-8 opacity-30" />
                        <p class="text-xs">Cart is empty</p>
                    </div>
                {:else}
                    <ul class="divide-y divide-border" aria-label="Cart items">
                        {#each cartItems as item (item.product_id)}
                            <li class="px-4 py-3 flex items-start gap-3">
                                <div class="text-base shrink-0">
                                    {categoryEmoji[item.category] ?? "📦"}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <p class="font-medium text-xs leading-tight truncate">{item.name}</p>
                                    <p class="text-muted-foreground text-[11px] mt-0.5">
                                        {item.quantity}{item.unit} × ₱{item.unit_cost.toFixed(2)}
                                    </p>
                                </div>
                                <div class="flex items-center gap-1.5 shrink-0">
                                    <span class="font-semibold text-xs text-primary">
                                        ₱{item.line_total.toFixed(2)}
                                    </span>
                                    <button
                                        onclick={() => cart.removeItem(item.product_id)}
                                        aria-label="Remove {item.name} from cart"
                                        class="text-muted-foreground hover:text-destructive transition-colors
                                            focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded p-0.5">
                                        <X class="size-3" />
                                    </button>
                                </div>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>

            <!-- Total + Checkout -->
            <div class="p-4 border-t border-border space-y-3">
                <div class="flex justify-between items-center">
                    <span class="text-sm text-muted-foreground">Subtotal</span>
                    <span class="font-bold text-lg text-primary">₱{total.toFixed(2)}</span>
                </div>
                <Button
                    class="w-full h-11 text-sm font-semibold"
                    onclick={checkout}
                    disabled={cartItems.length === 0 || checkoutLoading}
                    aria-busy={checkoutLoading}
                >
                    {#if checkoutLoading}
                        <Loader2 class="size-4 animate-spin mr-2" />
                        Processing...
                    {:else}
                        Charge ₱{total.toFixed(2)}
                    {/if}
                </Button>
            </div>
        </aside>
    </div>

    <!-- Mobile: floating cart button -->
    <div class="lg:hidden fixed bottom-4 right-4 z-50">
        <Sheet.Root bind:open={cartOpen}>
            <Sheet.Trigger>
                <Button
                    size="lg"
                    class="rounded-full shadow-lg h-14 w-14 relative"
                    aria-label="Open cart, {cartItems.length} items">
                    <ShoppingCart class="size-5" />
                    {#if cartItems.length > 0}
                        <span class="absolute -top-1 -right-1 bg-destructive text-destructive-foreground
                            rounded-full size-5 text-[10px] flex items-center justify-center font-bold">
                            {cartItems.length}
                        </span>
                    {/if}
                </Button>
            </Sheet.Trigger>
            <Sheet.Content side="bottom" class="h-[75vh] rounded-t-2xl">
                <Sheet.Header>
                    <Sheet.Title class="flex items-center gap-2 text-sm">
                        <ShoppingCart class="size-4" />
                        Cart ({cartItems.length})
                        {#if cartItems.length > 0}
                            <button onclick={() => cart.clear()}
                                class="ml-auto text-xs text-muted-foreground hover:text-destructive">
                                Clear
                            </button>
                        {/if}
                    </Sheet.Title>
                </Sheet.Header>
                <div class="flex-1 overflow-y-auto py-3">
                    {#if cartItems.length === 0}
                        <div class="flex flex-col items-center justify-center h-32 gap-2 text-muted-foreground">
                            <ShoppingCart class="size-6 opacity-30" />
                            <p class="text-xs">Cart is empty</p>
                        </div>
                    {:else}
                        <ul class="divide-y divide-border">
                            {#each cartItems as item (item.product_id)}
                                <li class="py-3 flex items-start gap-3">
                                    <div class="flex-1 min-w-0">
                                        <p class="font-medium text-sm">{item.name}</p>
                                        <p class="text-muted-foreground text-xs mt-0.5">
                                            {item.quantity}{item.unit} × ₱{item.unit_cost.toFixed(2)}
                                        </p>
                                    </div>
                                    <div class="flex items-center gap-2 shrink-0">
                                        <span class="font-semibold text-sm text-primary">
                                            ₱{item.line_total.toFixed(2)}
                                        </span>
                                        <button onclick={() => cart.removeItem(item.product_id)}
                                            aria-label="Remove {item.name}">
                                            <X class="size-4 text-muted-foreground hover:text-destructive" />
                                        </button>
                                    </div>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
                <div class="pt-3 border-t space-y-3">
                    <div class="flex justify-between font-bold">
                        <span>Total</span>
                        <span class="text-primary">₱{total.toFixed(2)}</span>
                    </div>
                    <Button class="w-full h-11" onclick={checkout}
                        disabled={cartItems.length === 0 || checkoutLoading}>
                        {#if checkoutLoading}
                            <Loader2 class="size-4 animate-spin mr-2" />
                        {/if}
                        Charge ₱{total.toFixed(2)}
                    </Button>
                </div>
            </Sheet.Content>
        </Sheet.Root>
    </div>
</div>