<script lang="ts">
    import { onMount } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { cart, cartTotal } from "$lib/stores/cart";
    import { apiJson } from "$lib/api";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import * as Tabs from "$lib/components/ui/tabs";
    import * as Sheet from "$lib/components/ui/sheet";
    import { Separator } from "$lib/components/ui/separator";
    import {
        ShoppingBasket, ShoppingCart, Trash2,
        Loader2, Scale, LayoutGrid, Package,
        ReceiptText, Users, LogOut
    } from "lucide-svelte";
    import { goto } from "$app/navigation";

    // --- State ---
    let products = $state<any[]>([]);
    let activeCategory = $state("all");
    let selectedProduct = $state<any>(null);
    let weightInput = $state("");
    let loadingProducts = $state(true);
    let checkoutLoading = $state(false);
    let error = $state("");
    let successMessage = $state("");
    let cartOpen = $state(false); // for mobile sheet

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

    // --- Load products ---
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
        // Retail/fixed-price: auto-add 1 unit directly to cart
        cart.addItem(product, 1);
        successMessage = `${product.name} added to cart`;
        setTimeout(() => successMessage = "", 2000);
    } else {
        // Per-kg: show weight input panel
        selectedProduct = product;
        weightInput = "";
    }
    }

    function addToCart() {
        if (!selectedProduct) return;
        const qty = parseFloat(weightInput);
        if (!qty || qty <= 0) return;

        cart.addItem(selectedProduct, qty);
        selectedProduct = null;
        weightInput = "";
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
            successMessage = `Invoice #${invoice.invoice_number} created — ₱${invoice.total_amount.toFixed(2)}`;
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
</script>

<div class="flex flex-col h-screen bg-muted/30">

    <!-- Header -->
    <header class="bg-background border-b px-4 py-3 flex items-center justify-between shrink-0">
        <div class="flex items-center gap-2">
            <ShoppingBasket class="size-5 text-primary" />
            <span class="font-semibold text-sm">{user?.business_name ?? "UpScale POS"}</span>
        </div>
        <div class="flex items-center gap-1">
            <Button variant="ghost" size="icon" aria-label="Inventory" onclick={() => goto("/inventory")}>
                <Package class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" aria-label="Invoices" onclick={() => goto("/invoices")}>
                <ReceiptText class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" aria-label="Suppliers" onclick={() => goto("/suppliers")}>
                <Users class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" aria-label="Log out" onclick={logout}>
                <LogOut class="size-4" />
            </Button>
        </div>
    </header>

    <!-- Alerts -->
    {#if error}
        <div class="bg-destructive/10 text-destructive text-sm px-4 py-2 text-center" role="alert">
            {error}
        </div>
    {/if}
    {#if successMessage}
        <div class="bg-green-500/10 text-green-700 text-sm px-4 py-2 text-center" role="status">
            {successMessage}
        </div>
    {/if}

    <!-- Main layout -->
    <div class="flex flex-1 overflow-hidden">

        <!-- LEFT: Product Grid -->
        <div class="flex flex-col flex-1 overflow-hidden">

            <!-- Category tabs -->
            <div class="bg-background border-b px-4 pt-3">
                <Tabs.Root bind:value={activeCategory}>
                    <Tabs.List class="gap-1">
                        {#each categories() as cat}
                            <Tabs.Trigger value={cat} class="capitalize text-xs">
                                {categoryLabels[cat] ?? cat}
                            </Tabs.Trigger>
                        {/each}
                    </Tabs.List>
                </Tabs.Root>
            </div>

            <!-- Products -->
            <div class="flex-1 overflow-y-auto p-4">
                {#if loadingProducts}
                    <div class="flex items-center justify-center h-40">
                        <Loader2 class="size-6 animate-spin text-muted-foreground" />
                    </div>
                {:else if filteredProducts.length === 0}
                    <div class="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                        <LayoutGrid class="size-8" />
                        <p class="text-sm">No products found</p>
                        <Button variant="outline" size="sm" onclick={() => goto("/inventory")}>
                            Add products
                        </Button>
                    </div>
                {:else}
                    <ul class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3"
                        aria-label="Product grid">
                        {#each filteredProducts as product (product.id)}
                        <li>
                            <button
                                aria-label="{product.name}, ₱{product.price} per {product.unit}"
                                onclick={() => selectProduct(product)}
                                class="bg-background rounded-xl border-2 p-3 text-left transition-all
                                    hover:border-primary hover:shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                                    {selectedProduct?.id === product.id ? 'border-primary bg-primary/5' : 'border-border'}
                                    {product.stock_quantity <= product.low_stock_threshold && product.low_stock_threshold > 0
                                        ? 'opacity-75' : ''}"
                            >
                                <div class="text-2xl mb-2">
                                    {product.category === 'beef' ? '🥩' :
                                     product.category === 'pork' ? '🥓' :
                                     product.category === 'chicken' ? '🍗' : '📦'}
                                </div>
                                <p class="font-medium text-xs leading-tight line-clamp-2">{product.name}</p>
                                {#if product.cut_type}
                                    <p class="text-muted-foreground text-xs">{product.cut_type}</p>
                                {/if}
                                <p class="text-primary font-semibold text-sm mt-1">
                                    ₱{Number(product.price).toFixed(2)}
                                    <span class="text-muted-foreground font-normal text-xs">/{product.unit}</span>
                                </p>
                                {#if product.stock_quantity <= product.low_stock_threshold && product.low_stock_threshold > 0}
                                    <Badge variant="destructive" class="text-xs mt-1">Low stock</Badge>
                                {/if}
                            </button>
                        </li>
                        {/each}
                    </ul>
                {/if}
            </div>

            <!-- Weight / Quantity input (shows when product selected) -->
            {#if selectedProduct}
                <div class="bg-background border-t p-4 space-y-3" aria-live="polite">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="font-medium text-sm">{selectedProduct.name}</p>
                            <p class="text-muted-foreground text-xs">₱{selectedProduct.price}/{selectedProduct.unit}</p>
                        </div>
                        <Button variant="ghost" size="icon" aria-label="Deselect product"
                            onclick={() => { selectedProduct = null; weightInput = ""; }}>
                            <Trash2 class="size-4" />
                        </Button>
                    </div>

                    <div class="flex items-center gap-2">
                        <Scale class="size-4 text-muted-foreground shrink-0" />
                        <input
                            type="number"
                            min="0"
                            step={selectedProduct.pricing_type === "per_kg" ? "0.001" : "1"}
                            placeholder={selectedProduct.pricing_type === "per_kg" ? "Weight in kg" : "Quantity"}
                            bind:value={weightInput}
                            aria-label={selectedProduct.pricing_type === "per_kg" ? "Weight in kilograms" : "Quantity"}
                            class="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                        <span class="text-sm text-muted-foreground shrink-0">
                            = ₱{weightInput ? (selectedProduct.price * parseFloat(weightInput || "0")).toFixed(2) : "0.00"}
                        </span>
                    </div>

                    <Button class="w-full" onclick={addToCart}
                        disabled={!weightInput || parseFloat(weightInput) <= 0}>
                        Add to Cart
                    </Button>
                </div>
            {/if}
        </div>

        <!-- RIGHT: Cart (desktop) -->
        <div class="hidden lg:flex flex-col w-80 bg-background border-l">
            <div class="p-4 border-b flex items-center justify-between">
                <h2 class="font-semibold text-sm flex items-center gap-2">
                    <ShoppingCart class="size-4" />
                    Cart
                </h2>
                {#if cartItems.length > 0}
                    <Button variant="ghost" size="sm" class="text-xs text-muted-foreground h-auto py-1"
                        onclick={() => cart.clear()}>
                        Clear
                    </Button>
                {/if}
            </div>

            <div class="flex-1 overflow-y-auto p-4 space-y-2">
                {#if cartItems.length === 0}
                    <div class="flex flex-col items-center justify-center h-32 text-muted-foreground gap-2">
                        <ShoppingCart class="size-6" />
                        <p class="text-xs">Cart is empty</p>
                    </div>
                {:else}
                    {#each cartItems as item (item.product_id)}
                        <div class="flex items-start justify-between gap-2 text-sm">
                            <div class="flex-1 min-w-0">
                                <p class="font-medium text-xs leading-tight truncate">{item.name}</p>
                                <p class="text-muted-foreground text-xs">
                                    {item.quantity}{item.unit} × ₱{item.unit_cost.toFixed(2)}
                                </p>
                            </div>
                            <div class="flex items-center gap-1 shrink-0">
                                <span class="font-medium text-xs">₱{item.line_total.toFixed(2)}</span>
                                <button aria-label="Remove {item.name} from cart"
                                    onclick={() => cart.removeItem(item.product_id)}
                                    class="text-muted-foreground hover:text-destructive transition-colors p-0.5">
                                    <Trash2 class="size-3" />
                                </button>
                            </div>
                        </div>
                        <Separator />
                    {/each}
                {/if}
            </div>

            <!-- Total + Checkout -->
            <div class="p-4 border-t space-y-3">
                <div class="flex justify-between text-sm font-semibold">
                    <span>Total</span>
                    <span>₱{total.toFixed(2)}</span>
                </div>
                <Button class="w-full" size="lg"
                    onclick={checkout}
                    disabled={cartItems.length === 0 || checkoutLoading}
                    aria-busy={checkoutLoading}>
                    {#if checkoutLoading}
                        <Loader2 class="size-4 animate-spin mr-2" />
                        Processing...
                    {:else}
                        Charge ₱{total.toFixed(2)}
                    {/if}
                </Button>
            </div>
        </div>
    </div>

    <!-- Mobile: floating cart button + sheet -->
    <div class="lg:hidden fixed bottom-4 right-4 z-50">
        <Sheet.Root bind:open={cartOpen}>
            <Sheet.Trigger>
                <Button size="lg" class="rounded-full shadow-lg relative" aria-label="Open cart">
                    <ShoppingCart class="size-5" />
                    {#if cartItems.length > 0}
                        <span class="absolute -top-1 -right-1 bg-destructive text-destructive-foreground
                            rounded-full size-5 text-xs flex items-center justify-center font-bold">
                            {cartItems.length}
                        </span>
                    {/if}
                </Button>
            </Sheet.Trigger>
            <Sheet.Content side="bottom" class="h-[70vh] rounded-t-xl">
                <Sheet.Header>
                    <Sheet.Title class="flex items-center gap-2">
                        <ShoppingCart class="size-4" />
                        Cart
                        {#if cartItems.length > 0}
                            <Button variant="ghost" size="sm"
                                class="text-xs text-muted-foreground h-auto py-1 ml-auto"
                                onclick={() => cart.clear()}>
                                Clear
                            </Button>
                        {/if}
                    </Sheet.Title>
                </Sheet.Header>

                <div class="flex-1 overflow-y-auto py-4 space-y-2">
                    {#if cartItems.length === 0}
                        <div class="flex flex-col items-center justify-center h-24 text-muted-foreground gap-2">
                            <ShoppingCart class="size-6" />
                            <p class="text-xs">Cart is empty</p>
                        </div>
                    {:else}
                        {#each cartItems as item (item.product_id)}
                            <div class="flex items-start justify-between gap-2 text-sm">
                                <div class="flex-1 min-w-0">
                                    <p class="font-medium text-xs leading-tight truncate">{item.name}</p>
                                    <p class="text-muted-foreground text-xs">
                                        {item.quantity}{item.unit} × ₱{item.unit_cost.toFixed(2)}
                                    </p>
                                </div>
                                <div class="flex items-center gap-1 shrink-0">
                                    <span class="font-medium text-xs">₱{item.line_total.toFixed(2)}</span>
                                    <button aria-label="Remove {item.name} from cart"
                                        onclick={() => cart.removeItem(item.product_id)}
                                        class="text-muted-foreground hover:text-destructive transition-colors p-0.5">
                                        <Trash2 class="size-3" />
                                    </button>
                                </div>
                            </div>
                            <Separator />
                        {/each}
                    {/if}
                </div>

                <div class="pt-4 border-t space-y-3">
                    <div class="flex justify-between font-semibold">
                        <span>Total</span>
                        <span>₱{total.toFixed(2)}</span>
                    </div>
                    <Button class="w-full" size="lg"
                        onclick={checkout}
                        disabled={cartItems.length === 0 || checkoutLoading}
                        aria-busy={checkoutLoading}>
                        {#if checkoutLoading}
                            <Loader2 class="size-4 animate-spin mr-2" />
                            Processing...
                        {:else}
                            Charge ₱{total.toFixed(2)}
                        {/if}
                    </Button>
                </div>
            </Sheet.Content>
        </Sheet.Root>
    </div>

</div>