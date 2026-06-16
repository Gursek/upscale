<script lang="ts">
    import { onMount } from "svelte";
    import { tick } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { cart, cartTotal } from "$lib/stores/cart";
    import { apiJson, apiFetch, API_BASE } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Separator } from "$lib/components/ui/separator";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import * as Sheet from "$lib/components/ui/sheet";
    import * as Dialog from "$lib/components/ui/dialog";
    import {
        ShoppingBasket, ShoppingCart, Trash2, Loader2, Search,
        Scale, FileBarChart, LayoutDashboard, LayoutGrid, Package, ReceiptText,
        Users, LogOut, Settings, Plus, Minus,
        ScanLine, X
    } from "lucide-svelte";

    // --- State ---
    let products = $state<any[]>([]);
    let activeCategory = $state("all");
    let searchTerm = $state("");
    let selectedProduct = $state<any>(null);
    let weightInput = $state("");
    let loadingProducts = $state(true);
    let checkoutLoading = $state(false);
    let scaleLoading = $state(false);
    let error = $state("");
    let successMessage = $state("");
    let cartOpen = $state(false);
    let checkoutDialogOpen = $state(false);
    let receiptDialogOpen = $state(false);
    let showBuyerFields = $state(false);
    let showDiscountFields = $state(false);
    let lastInvoice = $state<any>(null);
    let cashTendered = $state("");
    let buyerName = $state("");
    let buyerTin = $state("");
    let buyerAddress = $state("");
    let buyerBusinessStyle = $state("");
    let discountType = $state("");
    let discountAmount = $state("0");
    let discountBeneficiaryName = $state("");
    let discountBeneficiaryTin = $state("");
    let discountIdNo = $state("");
    let weightInputElement = $state<HTMLInputElement | null>(null);

    // --- Derived ---
    let user = $derived($auth);

    let categories = $derived(() => {
        const cats: string[] = ["all"];
        if (user?.sells_meat) cats.push("beef", "pork", "chicken");
        if (user?.sells_fish) cats.push("fish");
        if (user?.sells_retail) cats.push("retail");
        if (user?.sells_veggies) cats.push("veggies");
        return cats;
    });

    let filteredProducts = $derived.by(() => {
        const query = searchTerm.trim().toLowerCase();
        return products.filter((product) => {
            const categoryMatches = activeCategory === "all" || product.category === activeCategory;
            const searchMatches = !query ||
                product.name?.toLowerCase().includes(query) ||
                product.cut_type?.toLowerCase().includes(query) ||
                product.sku?.toLowerCase().includes(query);
            return categoryMatches && searchMatches;
        });
    });

    let cartItems = $derived($cart);
    let total = $derived($cartTotal);
    let payableTotal = $derived(Math.max(0, total - (Number(discountAmount) || 0)));
    let changeAmount = $derived(Math.max(0, (Number(cashTendered) || 0) - payableTotal));
    let quickCashAmounts = $derived.by(() => {
        const due = Math.ceil(payableTotal);
        const candidates = [due, 50, 100, 200, 500, 1000].filter((amount) => amount >= due);
        return [...new Set(candidates)].slice(0, 4);
    });

    let computedPrice = $derived(() => {
        if (!selectedProduct || !weightInput) return 0;
        const w = parseFloat(weightInput);
        if (isNaN(w) || w <= 0) return 0;
        return Number((selectedProduct.price * w).toFixed(2));
    });

    // --- Load ---
    onMount(() => {
        const token = localStorage.getItem("access_token");
        if (!token) { goto("/login"); return; }
        const refresh = () => loadProducts(false);
        window.addEventListener("focus", refresh);
        loadProducts();
        return () => window.removeEventListener("focus", refresh);
    });

    // --- Actions ---
    async function loadProducts(showLoading = true) {
        if (showLoading) loadingProducts = true;
        try {
            products = await apiJson<any[]>("/products/");
            cart.syncStock(products);
        } catch {
            error = "Failed to load products";
        } finally {
            loadingProducts = false;
        }
    }

    function cartQuantity(productId: number) {
        return cartItems.find((item) => item.product_id === productId)?.quantity ?? 0;
    }

    function availableStock(product: any) {
        return Math.max(0, Number(product.stock_quantity) - cartQuantity(product.id));
    }

    async function selectProduct(product: any) {
        if (product.pricing_type === "fixed") {
            const result = cart.addItem(product, 1);
            if (!result.added) {
                error = `Only ${result.available} ${product.unit} of ${product.name} available`;
                setTimeout(() => error = "", 3000);
                return;
            }
            successMessage = `${product.name}: ${result.quantity} in cart`;
            setTimeout(() => successMessage = "", 2000);
        } else {
            if (Number(product.stock_quantity) <= 0) {
                error = `${product.name} is out of stock`;
                return;
            }
            selectedProduct = product;
            weightInput = String(cartQuantity(product.id) || "");
            await tick();
            weightInputElement?.focus();
        }
    }

    function adjustWeight(delta: number) {
        const current = parseFloat(weightInput) || 0;
        const available = Number(selectedProduct?.stock_quantity ?? 0);
        weightInput = String(Math.min(available, Math.max(0, current + delta)));
        weightInputElement?.focus();
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
                const weight = Math.min(Number(data.weight_kg), Number(selectedProduct?.stock_quantity ?? 0));
                weightInput = weight.toFixed(3);
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
        const result = cart.addItem(selectedProduct, qty);
        if (!result.added) {
            error = `Only ${result.available} ${selectedProduct.unit} of ${selectedProduct.name} available`;
            return;
        }
        clearSelected();
        successMessage = "Added to cart";
        setTimeout(() => successMessage = "", 2000);
    }

    function beginCheckout() {
        if (cartItems.length === 0) return;
        cashTendered = payableTotal.toFixed(2);
        showBuyerFields = false;
        showDiscountFields = false;
        checkoutDialogOpen = true;
    }

    function resetOptionalCheckoutFields() {
        buyerName = "";
        buyerTin = "";
        buyerAddress = "";
        buyerBusinessStyle = "";
        discountType = "";
        discountAmount = "0";
        discountBeneficiaryName = "";
        discountBeneficiaryTin = "";
        discountIdNo = "";
        showBuyerFields = false;
        showDiscountFields = false;
    }

    async function checkout() {
        if (cartItems.length === 0) return;
        const tendered = Number(cashTendered);
        if (!Number.isFinite(tendered) || tendered < payableTotal) {
            error = "Cash received must cover the total amount due";
            return;
        }
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
                    payment_mode: "cash",
                    cash_tendered: tendered,
                    buyer_name: buyerName.trim() || null,
                    buyer_tin: buyerTin.trim() || null,
                    buyer_address: buyerAddress.trim() || null,
                    buyer_business_style: buyerBusinessStyle.trim() || null,
                    discount_type: discountType || null,
                    discount_amount: Number(discountAmount) || 0,
                    discount_beneficiary_name: discountBeneficiaryName.trim() || null,
                    discount_beneficiary_tin: discountBeneficiaryTin.trim() || null,
                    discount_id_no: discountIdNo.trim() || null,
                }),
            });
            lastInvoice = invoice;
            cart.clear();
            cartOpen = false;
            checkoutDialogOpen = false;
            receiptDialogOpen = true;
            resetOptionalCheckoutFields();
            await loadProducts(false);
            successMessage = `Invoice #${invoice.invoice_number} — ₱${Number(invoice.total_amount).toFixed(2)}`;
            setTimeout(() => successMessage = "", 5000);
        } catch (e: any) {
            error = e.message;
        } finally {
            checkoutLoading = false;
        }
    }

    async function printLastReceipt() {
        if (!lastInvoice) return;
        try {
            const response = await apiFetch(`/invoices/${lastInvoice.id}/print`);
            const html = await response.text();
            if (!response.ok) throw new Error("Could not load receipt");
            const printWindow = window.open("", "_blank", "width=420,height=720");
            if (!printWindow) throw new Error("Popup was blocked");
            printWindow.document.open();
            printWindow.document.write(html);
            printWindow.document.close();
            printWindow.focus();
        } catch (e: any) {
            error = e.message || "Could not print receipt";
        }
    }

    function nextTransaction() {
        receiptDialogOpen = false;
        lastInvoice = null;
        selectedProduct = null;
        weightInput = "";
    }

    function logout() {
        auth.logout();
        goto("/login");
    }

    const categoryLabels: Record<string, string> = {
        all: "All", beef: "Beef", pork: "Pork",
        chicken: "Chicken", fish: "Fish", retail: "Retail", veggies: "Veggies"
    };

    const categoryEmoji: Record<string, string> = {
        beef: "🥩", pork: "🥓", chicken: "🍗", fish: "🐟", retail: "📦", veggies: "🥕"
    };

    function getProductImage(product: any): string | null {
        if (!product.image_url) return null;
        if (product.image_url.startsWith("http")) return product.image_url;
        if (product.image_url.startsWith("/")) {
            return `${API_BASE.replace("/api", "")}${product.image_url}`;
        }
        return null;
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
            <Button variant="ghost" size="icon" class="size-8 hover:bg-primary! hover:text-primary-foreground!" aria-label="Dashboard" onclick={() => goto("/dashboard")}>
                <LayoutDashboard class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-8 hover:bg-primary! hover:text-primary-foreground!" aria-label="Inventory" onclick={() => goto("/inventory")}>
                <Package class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-8 hover:bg-primary! hover:text-primary-foreground!" aria-label="Sales history" onclick={() => goto("/invoices")}>
                <ReceiptText class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-8 hover:bg-primary! hover:text-primary-foreground!" aria-label="BIR reports" onclick={() => goto("/reports")}>
                <FileBarChart class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-8 hover:bg-primary! hover:text-primary-foreground!" aria-label="Suppliers" onclick={() => goto("/suppliers")}>
                <Users class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-8 hover:bg-primary! hover:text-primary-foreground!" aria-label="Settings" onclick={() => goto("/settings")}>
                <Settings class="size-4" />
            </Button>
            <div class="w-px h-4 bg-border mx-1"></div>
            <Button variant="ghost" size="icon" class="size-8 hover:bg-primary! hover:text-primary-foreground!" aria-label="Log out" onclick={logout}>
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
                            class="px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors
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

            <div class="bg-card border-b border-border px-3 py-2 shrink-0">
                <div class="relative max-w-md">
                    <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                    <Input
                        class="h-10 pl-9"
                        placeholder="Search products, cuts, or SKU"
                        bind:value={searchTerm}
                        aria-label="Search products"
                    />
                </div>
            </div>

            <!-- Product grid -->
            <div class="flex-1 overflow-y-auto p-3 pb-24 md:pb-3">
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
                    <ul class="grid gap-2 sm:gap-3"
                        style="grid-template-columns: repeat(auto-fill, minmax(150px, 1fr))"
                        aria-label="Products">
                        {#each filteredProducts as product (product.id)}
                            <li>
                                <button
                                    onclick={() => selectProduct(product)}
                                    aria-label="{product.name}, ₱{product.price} per {product.unit}"
                                    aria-pressed={selectedProduct?.id === product.id}
                                    disabled={availableStock(product) <= 0}
                                    class="w-full h-36 rounded-xl border-2 overflow-hidden text-left transition-all
                                        focus:outline-none focus-visible:ring-2 focus-visible:ring-ring relative
                                        disabled:opacity-50 disabled:cursor-not-allowed
                                        {selectedProduct?.id === product.id
                                            ? 'border-primary shadow-md'
                                            : 'border-border bg-card hover:border-primary/50 hover:shadow-sm'}"
                                >
                                    <!-- Image or emoji background -->
                                    {#if getProductImage(product)}
                                        <img
                                            src={getProductImage(product)}
                                            alt={product.name}
                                            class="absolute inset-0 w-full h-full object-cover opacity-35"
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
                                            <p class="text-muted-foreground text-[10px] mt-0.5">
                                                Available: {availableStock(product).toFixed(product.unit === "kg" ? 3 : 0)} {product.unit}
                                            </p>
                                        </div>

                                        {#if cartQuantity(product.id) > 0}
                                            <span class="absolute top-1.5 left-1.5 bg-primary text-primary-foreground text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                                                {cartQuantity(product.id)} in cart
                                            </span>
                                        {/if}
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
                                    bind:this={weightInputElement}
                                    type="number"
                                    min="0"
                                    max={selectedProduct.stock_quantity}
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

                            <Button
                                variant="outline"
                                size="icon"
                                onclick={() => adjustWeight(-1)}
                                disabled={!weightInput || parseFloat(weightInput) <= 0}
                                aria-label="Decrease quantity by one kilogram"
                            >
                                <Minus class="size-4" />
                            </Button>
                            <Button
                                variant="outline"
                                size="icon"
                                onclick={() => adjustWeight(1)}
                                disabled={(parseFloat(weightInput) || 0) >= Number(selectedProduct.stock_quantity)}
                                aria-label="Increase quantity by one kilogram"
                            >
                                <Plus class="size-4" />
                            </Button>

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
                            disabled={!weightInput || parseFloat(weightInput) <= 0 || parseFloat(weightInput) > Number(selectedProduct.stock_quantity)}
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
        <aside class="hidden md:flex flex-col w-80 bg-card border-l border-border" aria-label="Shopping cart">
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
                                    {#if item.pricing_type === "fixed"}
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            class="size-6"
                                            onclick={() => cart.setQuantity(item.product_id, item.quantity - 1)}
                                            aria-label="Decrease {item.name} quantity"
                                        ><Minus class="size-3" /></Button>
                                        <span class="w-5 text-center text-xs">{item.quantity}</span>
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            class="size-6"
                                            onclick={() => cart.setQuantity(item.product_id, item.quantity + 1)}
                                            disabled={item.quantity >= item.stock_quantity}
                                            aria-label="Increase {item.name} quantity"
                                        ><Plus class="size-3" /></Button>
                                    {/if}
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
                    onclick={beginCheckout}
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

    <!-- Mobile: bottom cart action bar -->
    <div class="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t bg-background/95 p-3 shadow-lg backdrop-blur">
        <Sheet.Root bind:open={cartOpen}>
            <div class="grid grid-cols-[auto_1fr_auto] items-center gap-2">
                <Sheet.Trigger>
                    <Button variant="outline" class="h-12 gap-2" aria-label="Open cart, {cartItems.length} items">
                        <ShoppingCart class="size-4" />
                        {cartItems.length}
                    </Button>
                </Sheet.Trigger>
                <div>
                    <p class="text-[11px] text-muted-foreground">Total</p>
                    <p class="text-lg font-bold text-primary">₱{total.toFixed(2)}</p>
                </div>
                <Button class="h-12 px-4" onclick={beginCheckout} disabled={cartItems.length === 0 || checkoutLoading}>
                    Charge
                </Button>
            </div>
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
                                        {#if item.pricing_type === "fixed"}
                                            <Button variant="outline" size="icon" class="size-7" onclick={() => cart.setQuantity(item.product_id, item.quantity - 1)} aria-label="Decrease {item.name}">
                                                <Minus class="size-3" />
                                            </Button>
                                            <span class="text-xs">{item.quantity}</span>
                                            <Button variant="outline" size="icon" class="size-7" onclick={() => cart.setQuantity(item.product_id, item.quantity + 1)} disabled={item.quantity >= item.stock_quantity} aria-label="Increase {item.name}">
                                                <Plus class="size-3" />
                                            </Button>
                                        {/if}
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
                    <Button class="w-full h-11" onclick={beginCheckout}
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

<Dialog.Root bind:open={checkoutDialogOpen}>
    <Dialog.Content class="max-w-lg max-h-[90vh] overflow-y-auto">
        <Dialog.Header>
            <Dialog.Title>Cash Payment</Dialog.Title>
            <Dialog.Description>Fast checkout for cash sales. Add buyer or statutory discount details only when needed.</Dialog.Description>
        </Dialog.Header>

        <div class="space-y-4">
            <div class="grid grid-cols-2 gap-3">
                <div class="rounded-xl bg-muted/50 border p-4">
                    <p class="text-xs text-muted-foreground">Amount due</p>
                    <p class="text-2xl font-bold text-primary">PHP {payableTotal.toFixed(2)}</p>
                </div>
                <div class="rounded-xl bg-muted/50 border p-4">
                    <p class="text-xs text-muted-foreground">Change</p>
                    <p class="text-2xl font-bold">PHP {changeAmount.toFixed(2)}</p>
                </div>
            </div>

            <div class="space-y-2">
                <Label for="cash-tendered">Cash received</Label>
                <Input id="cash-tendered" type="number" min={payableTotal} step="0.01" bind:value={cashTendered} class="h-12 text-lg font-semibold" />
            </div>

            <div class="grid grid-cols-4 gap-2" aria-label="Quick cash amounts">
                {#each quickCashAmounts as amount}
                    <Button type="button" variant="outline" onclick={() => cashTendered = amount.toFixed(2)}>
                        {amount === Math.ceil(payableTotal) ? "Exact" : `₱${amount}`}
                    </Button>
                {/each}
            </div>

            <div class="grid grid-cols-2 gap-2">
                <Button type="button" variant={showBuyerFields ? "default" : "outline"} onclick={() => showBuyerFields = !showBuyerFields}>
                    Buyer Info
                </Button>
                <Button type="button" variant={showDiscountFields ? "default" : "outline"} onclick={() => showDiscountFields = !showDiscountFields}>
                    Discount
                </Button>
            </div>

            {#if showBuyerFields}
                <Separator />
                <div class="space-y-3">
                    <div>
                        <p class="text-sm font-medium">Buyer information</p>
                        <p class="text-xs text-muted-foreground">Use only when the buyer requests named tax documentation.</p>
                    </div>
                    <div class="grid sm:grid-cols-2 gap-3">
                        <div class="space-y-2">
                            <Label for="buyer-name">Registered name</Label>
                            <Input id="buyer-name" bind:value={buyerName} />
                        </div>
                        <div class="space-y-2">
                            <Label for="buyer-tin">TIN</Label>
                            <Input id="buyer-tin" bind:value={buyerTin} />
                        </div>
                    </div>
                    <div class="space-y-2">
                        <Label for="buyer-address">Address</Label>
                        <Input id="buyer-address" bind:value={buyerAddress} />
                    </div>
                    <div class="space-y-2">
                        <Label for="buyer-style">Business style</Label>
                        <Input id="buyer-style" bind:value={buyerBusinessStyle} />
                    </div>
                </div>
            {/if}

            {#if showDiscountFields}
                <Separator />
                <div class="space-y-3">
                    <div>
                        <p class="text-sm font-medium">Statutory discount</p>
                        <p class="text-xs text-muted-foreground">Choose a verified discount and record the required ID details.</p>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        {#each [
                            ["senior_citizen", "Senior"],
                            ["pwd", "PWD"],
                            ["naac", "Athlete/Coach"],
                            ["solo_parent", "Solo Parent"],
                        ] as option}
                            <Button
                                type="button"
                                variant={discountType === option[0] ? "default" : "outline"}
                                onclick={() => discountType = discountType === option[0] ? "" : option[0]}
                                aria-pressed={discountType === option[0]}
                            >
                                {option[1]}
                            </Button>
                        {/each}
                    </div>
                    <div class="space-y-2">
                        <Label for="discount-amount">Discount amount</Label>
                        <Input id="discount-amount" type="number" min="0" max={total} step="0.01"
                            bind:value={discountAmount} disabled={!discountType} />
                    </div>
                    {#if discountType}
                        <div class="grid sm:grid-cols-2 gap-3">
                            <div class="space-y-2">
                                <Label for="beneficiary-name">Beneficiary name</Label>
                                <Input id="beneficiary-name" bind:value={discountBeneficiaryName} />
                            </div>
                            <div class="space-y-2">
                                <Label for="discount-id">ID number</Label>
                                <Input id="discount-id" bind:value={discountIdNo} />
                            </div>
                        </div>
                        <div class="space-y-2">
                            <Label for="beneficiary-tin">Beneficiary TIN, if any</Label>
                            <Input id="beneficiary-tin" bind:value={discountBeneficiaryTin} />
                        </div>
                    {/if}
                </div>
            {/if}
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => checkoutDialogOpen = false}>Cancel</Button>
            <Button
                onclick={checkout}
                disabled={checkoutLoading || (Number(cashTendered) || 0) < payableTotal ||
                    (!!discountType && (!discountBeneficiaryName.trim() || !discountIdNo.trim()))}
                aria-busy={checkoutLoading}
            >
                {#if checkoutLoading}<Loader2 class="size-4 animate-spin mr-2" />{/if}
                Complete Sale
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<Dialog.Root bind:open={receiptDialogOpen}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Receipt Preview</Dialog.Title>
            <Dialog.Description>Review the completed sale, then print or start the next transaction.</Dialog.Description>
        </Dialog.Header>

        {#if lastInvoice}
            <div class="rounded-xl border bg-background p-4 font-mono text-xs space-y-3">
                <div class="text-center border-b pb-3">
                    <p class="font-bold text-sm">{lastInvoice.seller?.business_name ?? user?.business_name}</p>
                    <p>Invoice #{lastInvoice.display_invoice_number ?? lastInvoice.invoice_number}</p>
                    <p>{new Date(lastInvoice.date_time).toLocaleString("en-PH", { timeZone: "Asia/Manila" })}</p>
                </div>
                <ul class="space-y-2">
                    {#each lastInvoice.items as item}
                        <li>
                            <div class="flex justify-between gap-3">
                                <span>{item.description}</span>
                                <span>PHP {Number(item.line_total).toFixed(2)}</span>
                            </div>
                            <p class="text-muted-foreground">{Number(item.quantity).toFixed(3)} x PHP {Number(item.unit_cost).toFixed(2)}</p>
                        </li>
                    {/each}
                </ul>
                <Separator />
                <div class="space-y-1">
                    <div class="flex justify-between"><span>Subtotal</span><span>PHP {Number(lastInvoice.subtotal).toFixed(2)}</span></div>
                    <div class="flex justify-between"><span>Discount</span><span>PHP {Number(lastInvoice.discount_amount).toFixed(2)}</span></div>
                    <div class="flex justify-between font-bold text-sm"><span>Total</span><span>PHP {Number(lastInvoice.total_amount).toFixed(2)}</span></div>
                    <div class="flex justify-between"><span>Cash</span><span>PHP {Number(lastInvoice.cash_tendered).toFixed(2)}</span></div>
                    <div class="flex justify-between"><span>Change</span><span>PHP {Number(lastInvoice.change_amount).toFixed(2)}</span></div>
                </div>
            </div>
        {/if}

        <Dialog.Footer>
            <Button variant="outline" onclick={nextTransaction}>Next Transaction</Button>
            <Button onclick={printLastReceipt}>Print Receipt</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
