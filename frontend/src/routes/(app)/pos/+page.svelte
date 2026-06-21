<script lang="ts">
    import { onMount } from "svelte";
    import { tick } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { cart, cartSummary } from "$lib/stores/cart";
    import { apiJson, apiFetch, API_BASE, revokeCurrentSession } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Separator } from "$lib/components/ui/separator";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import { subscribeQueueCount } from "$lib/offline-queue";
    import * as Select from "$lib/components/ui/select";
    import * as Sheet from "$lib/components/ui/sheet";
    import * as Dialog from "$lib/components/ui/dialog";
    import {
        ShoppingBasket, ShoppingCart, Trash2, Loader2, Search,
        Scale, FileBarChart, LayoutDashboard, LayoutGrid, Package, ReceiptText,
        Users, LogOut, Settings, Plus, Minus,
        ScanLine, X, Ban, CloudOff
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
    let voidDialogOpen = $state(false);
    let voidLoading = $state(false);
    let voidReason = $state("");
    let showBuyerFields = $state(false);
    let discountDialogOpen = $state(false);
    let discountError = $state("");
    let discountDraftType = $state("");
    let discountDraftIdNo = $state("");
    let lastInvoice = $state<any>(null);
    let lastCompletedInvoice = $state<any>(null);
    let receiptHtml = $state("");
    let receiptLoading = $state(false);
    let receiptFrame = $state<HTMLIFrameElement | null>(null);
    let cashTendered = $state("");
    let buyerName = $state("");
    let buyerTin = $state("");
    let buyerAddress = $state("");
    let buyerBusinessStyle = $state("");
    let discountType = $state("");
    let discountIdNo = $state("");
    let weightInputElement = $state<HTMLInputElement | null>(null);
    let weightInputActive = $state(false);
    let queuedInvoiceCount = $state(0);

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

    let cartItems = $derived($cartSummary.items);
    let total = $derived($cartSummary.total);
    let itemCount = $derived($cartSummary.count);
    const discountLabels: Record<string, string> = {
        senior_citizen: "Senior Citizen",
        pwd: "PWD",
        naac: "National Athlete",
        solo_parent: "Solo Parent",
    };
    let estimatedVatAmount = $derived.by(() => {
        if (user?.vat_status !== "vat") return 0;
        return cartItems.reduce((sum, item) => {
            const product = products.find((candidate) => candidate.id === item.product_id);
            if (product?.tax_classification !== "standard") return sum;
            return sum + (item.line_total - item.line_total / 1.12);
        }, 0);
    });
    let estimatedDiscountAmount = $derived.by(() => {
        if (!discountType) return 0;
        if (discountType === "senior_citizen" || discountType === "pwd") {
            return Math.max(0, total - estimatedVatAmount) * 0.20;
        }
        if (discountType === "naac") return total * 0.20;
        if (discountType === "solo_parent") return total * 0.10;
        return 0;
    });
    let estimatedVatDeduction = $derived(
        discountType === "senior_citizen" || discountType === "pwd"
            ? estimatedVatAmount
            : 0
    );
    let estimatedTotalDeduction = $derived(
        Number((estimatedDiscountAmount + estimatedVatDeduction).toFixed(2))
    );
    let payableTotal = $derived(Math.max(0, total - estimatedTotalDeduction));
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

    $effect(() => {
        if (cartItems.length === 0 && discountType) {
            removeDiscount();
        }
    });

    // --- Load ---
    onMount(() => {
        const token = localStorage.getItem("access_token");
        if (!token) { goto("/login"); return; }
        const refresh = () => loadProducts(false);
        const unsubscribeQueue = subscribeQueueCount((count) => queuedInvoiceCount = count);
        window.addEventListener("focus", refresh);
        loadProducts();
        return () => {
            unsubscribeQueue();
            window.removeEventListener("focus", refresh);
        };
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
        weightInputActive = false;
        selectedProduct = null;
        weightInput = "";
    }

    async function readScale() {
        scaleLoading = true;
        try {
            const res = await apiFetch("/scale/read");
            const data = await res.json();
            if (!res.ok) {
                error = data.error || "Could not read scale";
                setTimeout(() => error = "", 3000);
            } else if (data.weight_kg !== undefined && Number(data.weight_kg) >= 0) {
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
        checkoutDialogOpen = true;
    }

    function setRetailQuantity(item: any, value: string) {
        const quantity = Math.floor(Number(value));
        if (!Number.isFinite(quantity) || quantity < 1) {
            error = "Quantity must be at least 1";
            setTimeout(() => error = "", 3000);
            return false;
        }
        if (quantity > Number(item.stock_quantity)) {
            error = `Only ${item.stock_quantity} ${item.unit} of ${item.name} available`;
            setTimeout(() => error = "", 3000);
            return false;
        }
        cart.setQuantity(item.product_id, quantity);
        return true;
    }

    function openDiscountDialog() {
        discountDraftType = discountType;
        discountDraftIdNo = discountIdNo;
        discountError = "";
        discountDialogOpen = true;
    }

    function applyDiscount() {
        if (!discountDraftType) {
            discountError = "Select a discount type";
            return;
        }
        if (!discountDraftIdNo.trim()) {
            discountError = "ID number is required";
            return;
        }
        discountType = discountDraftType;
        discountIdNo = discountDraftIdNo.trim();
        discountDialogOpen = false;
    }

    function removeDiscount() {
        discountType = "";
        discountIdNo = "";
        discountDraftType = "";
        discountDraftIdNo = "";
        discountError = "";
    }

    function resetOptionalCheckoutFields() {
        buyerName = "";
        buyerTin = "";
        buyerAddress = "";
        buyerBusinessStyle = "";
        removeDiscount();
        showBuyerFields = false;
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
                    discount_id_no: discountIdNo.trim() || null,
                }),
            });
            lastInvoice = invoice;
            lastCompletedInvoice = invoice;
            cart.clear();
            cartOpen = false;
            checkoutDialogOpen = false;
            receiptDialogOpen = true;
            resetOptionalCheckoutFields();
            await loadReceiptPreview(invoice.id);
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
            if (!receiptHtml) await loadReceiptPreview(lastInvoice.id);
            const previewWindow = receiptFrame?.contentWindow;
            if (!previewWindow) throw new Error("Receipt preview is not ready");
            previewWindow.focus();
            previewWindow.print();
        } catch (e: any) {
            error = e.message || "Could not print receipt";
        }
    }

    async function loadReceiptPreview(invoiceId: number) {
        receiptLoading = true;
        try {
            const response = await apiFetch(`/invoices/${invoiceId}/print`);
            const html = await response.text();
            if (!response.ok) throw new Error("Could not load receipt preview");
            receiptHtml = html.replace(
                /<button onclick="window\.print\(\)">Print<\/button>/,
                ""
            );
        } catch (e: any) {
            receiptHtml = "";
            error = e.message || "Could not load receipt preview";
            setTimeout(() => error = "", 4000);
        } finally {
            receiptLoading = false;
        }
    }

    function nextTransaction() {
        receiptDialogOpen = false;
        lastInvoice = null;
        receiptHtml = "";
        weightInputActive = false;
        selectedProduct = null;
        weightInput = "";
    }

    function selectVoidReason(reason: string) {
        voidReason = reason;
    }

    function openVoidLastTransaction() {
        if (!lastCompletedInvoice) {
            error = "No completed transaction to void yet";
            setTimeout(() => error = "", 3000);
            return;
        }
        if (lastCompletedInvoice.status === "voided") {
            error = "Last transaction is already voided";
            setTimeout(() => error = "", 3000);
            return;
        }
        voidReason = "";
        voidDialogOpen = true;
    }

    async function voidLastTransaction() {
        if (!lastCompletedInvoice || !voidReason.trim()) return;
        voidLoading = true;
        error = "";
        try {
            const response = await apiJson<any>(`/invoices/${lastCompletedInvoice.id}/void`, {
                method: "POST",
                body: JSON.stringify({ reason: voidReason.trim() }),
            });
            lastCompletedInvoice = response.invoice;
            if (lastInvoice?.id === response.invoice.id) {
                lastInvoice = response.invoice;
            }
            voidDialogOpen = false;
            await loadProducts(false);
            successMessage = `Voided invoice #${response.invoice.display_invoice_number ?? response.invoice.invoice_number}`;
            setTimeout(() => successMessage = "", 5000);
        } catch (e: any) {
            error = e.message || "Could not void last transaction";
        } finally {
            voidLoading = false;
        }
    }

    async function logout() {
        await revokeCurrentSession();
        auth.logout();
        goto("/login");
    }

    const categoryLabels: Record<string, string> = {
        all: "All", beef: "Beef", pork: "Pork",
        chicken: "Chicken", fish: "Fish", retail: "Retail", veggies: "Veggies"
    };

    const quickVoidReasons = ["Wrong item", "Wrong quantity", "Customer cancelled"];

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
    <header class="bg-card border-b border-border px-2 sm:px-4 min-h-14 flex items-center justify-between gap-2 shrink-0 shadow-sm">
        <div class="flex min-w-0 items-center gap-2">
            <ShoppingBasket class="size-4 text-primary" />
            <span class="max-w-28 truncate text-sm font-semibold tracking-tight sm:max-w-48">
                {user?.business_name ?? "UpScale POS"}
            </span>
        </div>
        <nav class="flex min-w-0 items-center overflow-x-auto scrollbar-none" aria-label="Main navigation">
            {#if queuedInvoiceCount > 0}
                <div
                    class="mr-2 flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-700"
                    role="status"
                    aria-label="{queuedInvoiceCount} queued offline invoices"
                >
                    <CloudOff class="size-3.5" />
                    <span>{queuedInvoiceCount}</span>
                </div>
            {/if}
            <Button variant="ghost" size="icon" class="size-11 hover:bg-primary! hover:text-primary-foreground!" aria-label="Dashboard" onclick={() => goto("/dashboard")}>
                <LayoutDashboard class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-11 hover:bg-primary! hover:text-primary-foreground!" aria-label="Inventory" onclick={() => goto("/inventory")}>
                <Package class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-11 hover:bg-primary! hover:text-primary-foreground!" aria-label="Sales history" onclick={() => goto("/invoices")}>
                <ReceiptText class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-11 hover:bg-primary! hover:text-primary-foreground!" aria-label="BIR reports" onclick={() => goto("/reports")}>
                <FileBarChart class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-11 hover:bg-primary! hover:text-primary-foreground!" aria-label="Suppliers" onclick={() => goto("/suppliers")}>
                <Users class="size-4" />
            </Button>
            <Button variant="ghost" size="icon" class="size-11 hover:bg-primary! hover:text-primary-foreground!" aria-label="Settings" onclick={() => goto("/settings")}>
                <Settings class="size-4" />
            </Button>
            <div class="w-px h-4 bg-border mx-1"></div>
            <Button variant="ghost" size="icon" class="size-11 hover:bg-primary! hover:text-primary-foreground!" aria-label="Log out" onclick={logout}>
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
            <div class="bg-card border-b border-border px-2 sm:px-3 shrink-0">
                <div class="flex gap-2 overflow-x-auto py-2 scrollbar-none snap-x" role="tablist" aria-label="Product categories">
                    {#each categories() as cat}
                        <button
                            role="tab"
                            aria-selected={activeCategory === cat}
                            onclick={() => activeCategory = cat}
                            class="min-h-11 snap-start px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors
                                focus:outline-none focus-visible:ring-2 focus-visible:ring-ring shrink-0 touch-manipulation
                                {activeCategory === cat
                                    ? 'bg-primary text-primary-foreground'
                                    : 'text-muted-foreground hover:text-foreground hover:bg-accent'}"
                        >
                            {categoryLabels[cat] ?? cat}
                        </button>
                    {/each}
                </div>
            </div>

            <div class="bg-card border-b border-border px-2 py-2 sm:px-3 shrink-0">
                <div class="relative w-full sm:max-w-md">
                    <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                    <Input
                        class="h-11 pl-9"
                        placeholder="Search products, cuts, or SKU"
                        bind:value={searchTerm}
                        aria-label="Search products"
                    />
                </div>
            </div>

            <!-- Product grid -->
            <div class="flex-1 overflow-y-auto p-2 sm:p-3 {selectedProduct ? 'pb-52 lg:pb-24' : 'pb-28 lg:pb-3'}">
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
                    <ul class="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 md:grid-cols-4 xl:grid-cols-5"
                        aria-label="Products">
                        {#each filteredProducts as product (product.id)}
                            <li>
                                <button
                                    onclick={() => selectProduct(product)}
                                    aria-label="{product.name}, ₱{product.price} per {product.unit}"
                                    aria-pressed={selectedProduct?.id === product.id}
                                    disabled={availableStock(product) <= 0}
                                    class="w-full min-h-40 rounded-xl border-2 overflow-hidden text-left transition-all
                                        focus:outline-none focus-visible:ring-2 focus-visible:ring-ring relative
                                        disabled:opacity-50 disabled:cursor-not-allowed
                                        touch-manipulation active:scale-[0.98]
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
                                        {#if availableStock(product) <= 0}
                                            <div class="absolute top-1.5 right-1.5">
                                                <span class="rounded bg-destructive px-1.5 py-0.5 text-[9px] font-bold text-destructive-foreground">
                                                    OUT OF STOCK
                                                </span>
                                            </div>
                                        {:else if availableStock(product) <= Number(product.low_stock_threshold) && Number(product.low_stock_threshold) > 0}
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
                {#if weightInputActive}
                    <button
                        type="button"
                        class="fixed inset-0 z-40 cursor-default bg-black/10 backdrop-blur-[1px]"
                        aria-label="Return weight input to bottom"
                        onclick={() => {
                            weightInputActive = false;
                            weightInputElement?.blur();
                        }}
                    ></button>
                {/if}
                <div
                    class="fixed left-0 right-0 z-[60] border-t border-border bg-card p-3
                        transition-[bottom,box-shadow,border-radius] duration-300 ease-out
                        lg:right-80
                        {weightInputActive
                            ? 'bottom-[max(6rem,calc(50dvh-7rem))] rounded-t-2xl shadow-2xl'
                            : 'bottom-[5.25rem] shadow-[0_-2px_8px_rgba(0,0,0,0.06)] lg:bottom-0'}"
                    aria-live="polite">
                    <div class="mx-auto flex max-w-2xl flex-wrap items-center gap-2 sm:gap-3">

                        <!-- Product info -->
			<div class="w-28 min-w-0 shrink-0 sm:w-36">
				<p class="w-full truncate text-sm leading-tight font-semibold">
					{selectedProduct.name}
				</p>
				<p class="text-muted-foreground text-xs">₱{selectedProduct.price}/kg</p>
			</div>

			<!-- Weight input -->
			<div
				class="flex w-full min-w-0 items-center gap-2 sm:w-auto sm:min-w-72 sm:flex-1"
			>
				<div class="relative min-w-32 flex-1">
                                <input
                                    bind:this={weightInputElement}
                                    type="number"
                                    min="0"
                                    max={selectedProduct.stock_quantity}
                                    step="0.001"
                                    placeholder="0.000 kg"
                                    bind:value={weightInput}
                                    onfocus={() => weightInputActive = true}
                                    onblur={() => weightInputActive = false}
                                    aria-label="Weight in kilograms"
                                    class="h-11 w-full rounded-lg border border-input bg-background px-3 py-2 text-base
                                        font-mono focus:outline-none focus:ring-2 focus:ring-ring pr-16"
                                />
                                <span class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">
                                    kg
                                </span>
                            </div>

                            <Button
                                variant="outline"
                                size="icon"
                                class="size-11"
                                onclick={() => adjustWeight(-1)}
                                disabled={!weightInput || parseFloat(weightInput) <= 0}
                                aria-label="Decrease quantity by one kilogram"
                            >
                                <Minus class="size-4" />
                            </Button>
                            <Button
                                variant="outline"
                                size="icon"
                                class="size-11"
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
                                class="h-11 shrink-0 gap-1.5 px-3"
                            >
                                {#if scaleLoading}
                                    <Loader2 class="size-3.5 animate-spin" />
                                {:else}
                                    <ScanLine class="size-3.5" />
                                {/if}
                                <span class="hidden sm:inline">Read Scale</span>
                            </Button>
                        </div>

                        <div class="ml-auto flex shrink-0 items-center gap-2 sm:gap-3">
                            <!-- Price preview -->
                            <div class="min-w-20 shrink-0 text-right">
                                <p class="text-xs text-muted-foreground">Total</p>
                                <p class="text-base font-bold text-primary">
                                    ₱{computedPrice().toFixed(2)}
                                </p>
                            </div>

                            <!-- Add to cart -->
                            <Button
                                onpointerdown={(event) => event.preventDefault()}
                                onclick={addToCart}
                                disabled={!weightInput || parseFloat(weightInput) <= 0 || parseFloat(weightInput) > Number(selectedProduct.stock_quantity)}
                                class="h-11 shrink-0 px-4"
                                aria-label="Add {selectedProduct.name} to cart"
                            >
                                <Plus class="mr-1 size-4" />
                                Add
                            </Button>

                            <!-- Dismiss -->
                            <button
                                onclick={clearSelected}
                                aria-label="Cancel selection"
                                class="flex size-11 items-center justify-center rounded text-muted-foreground transition-colors
                                    hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                <X class="size-4" />
                            </button>
                        </div>
                    </div>
                </div>
            {/if}
        </div>

        <!-- RIGHT: Cart (desktop) -->
        <aside class="hidden lg:flex flex-col w-80 bg-card border-l border-border" aria-label="Shopping cart">
            <div class="px-4 py-3 border-b border-border flex items-center justify-between">
                <h2 class="font-semibold text-sm flex items-center gap-1.5">
                    <ShoppingCart class="size-4" />
                    <Button
                        variant="ghost"
                        size="icon"
                        class="size-9 hover:bg-destructive! hover:text-destructive-foreground!"
                        aria-label="Void last transaction"
                        title="Void last transaction"
                        onclick={openVoidLastTransaction}
                        disabled={!lastCompletedInvoice || lastCompletedInvoice.status === "voided"}
                    >
                        <Ban class="size-4" />
                    </Button>
                    Cart
                    {#if cartItems.length > 0}
                        <span class="bg-primary text-primary-foreground text-[10px] font-bold
                            rounded-full size-4 flex items-center justify-center">
                            {itemCount}
                        </span>
                    {/if}
                </h2>
                {#if cartItems.length > 0}
                    <button
                        onclick={() => cart.clear()}
                        aria-label="Clear cart"
                        class="min-h-11 rounded px-2 text-xs text-muted-foreground hover:text-destructive transition-colors
                            focus:outline-none focus-visible:ring-2 focus-visible:ring-ring">
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
                            <li class="flex flex-wrap items-start gap-3 px-4 py-3">
                                <div class="text-base shrink-0">
                                    {categoryEmoji[item.category] ?? "📦"}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <p class="font-medium text-xs leading-tight truncate">{item.name}</p>
                                    <p class="text-muted-foreground text-[11px] mt-0.5">
                                        {item.quantity}{item.unit} × ₱{item.unit_cost.toFixed(2)}
                                    </p>
                                </div>
                                <div class="ml-auto flex shrink-0 items-center gap-1.5">
                                    {#if item.pricing_type === "fixed"}
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            class="size-9"
                                            onclick={() => cart.setQuantity(item.product_id, item.quantity - 1)}
                                            aria-label="Decrease {item.name} quantity"
                                        ><Minus class="size-3" /></Button>
                                        <Input
                                            type="number"
                                            min="1"
                                            max={item.stock_quantity}
                                            step="1"
                                            value={item.quantity}
                                            class="h-9 w-14 px-1 text-center text-xs"
                                            aria-label="Quantity for {item.name}"
                                            onchange={(event) => {
                                                if (!setRetailQuantity(item, event.currentTarget.value)) {
                                                    event.currentTarget.value = String(item.quantity);
                                                }
                                            }}
                                            onkeydown={(event) => {
                                                if (event.key === "Enter") event.currentTarget.blur();
                                            }}
                                        />
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            class="size-9"
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
                                        class="flex size-9 items-center justify-center text-muted-foreground hover:text-destructive transition-colors
                                            focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded">
                                        <X class="size-4" />
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
                {#if discountType}
                    <div class="rounded-lg border border-primary/20 bg-primary/5 p-2.5 text-xs">
                        <div class="flex items-start justify-between gap-2">
                            <div>
                                <p class="font-medium text-primary">{discountLabels[discountType]}</p>
                                <p class="text-muted-foreground">ID: {discountIdNo}</p>
                            </div>
                            <button
                                type="button"
                                onclick={removeDiscount}
                                aria-label="Remove applied discount"
                                class="flex size-11 items-center justify-center rounded text-muted-foreground hover:bg-primary hover:text-primary-foreground"
                            >
                                <X class="size-3.5" />
                            </button>
                        </div>
                        <div class="mt-2 flex justify-between font-medium">
                            <span>Estimated deduction</span>
                            <span>-₱{estimatedTotalDeduction.toFixed(2)}</span>
                        </div>
                    </div>
                {:else}
                    <Button
                        type="button"
                        variant="outline"
                        class="h-11 w-full border-primary/40 bg-primary/5 font-semibold text-primary hover:bg-primary! hover:text-primary-foreground!"
                        onclick={openDiscountDialog}
                        disabled={cartItems.length === 0}
                    >
                        Apply Discount
                    </Button>
                {/if}
                {#if discountType}
                    <div class="flex justify-between text-sm font-semibold">
                        <span>Amount due</span>
                        <span class="text-primary">₱{payableTotal.toFixed(2)}</span>
                    </div>
                {/if}
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
                        Charge ₱{payableTotal.toFixed(2)}
                    {/if}
                </Button>
            </div>
        </aside>
    </div>

    <!-- Mobile: bottom cart action bar -->
    <div class="lg:hidden fixed bottom-0 left-0 right-0 z-50 border-t bg-background/95 px-3 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] shadow-lg backdrop-blur">
        <Sheet.Root bind:open={cartOpen}>
            <div class="grid grid-cols-[1fr_auto_auto] items-center gap-2">
                <Sheet.Trigger>
                    <Button variant="outline" class="h-14 w-full justify-start gap-3 px-3" aria-label="Open cart, {itemCount} items, total ₱{payableTotal.toFixed(2)}">
                        <span class="relative">
                            <ShoppingCart class="size-5" />
                            {#if itemCount > 0}
                                <span class="absolute -right-2 -top-2 flex size-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-primary-foreground">
                                    {itemCount}
                                </span>
                            {/if}
                        </span>
                        <span class="min-w-0 text-left">
                            <span class="block text-[10px] text-muted-foreground">View cart</span>
                            <span class="block truncate text-base font-bold text-primary">₱{payableTotal.toFixed(2)}</span>
                        </span>
                    </Button>
                </Sheet.Trigger>
                <Button
                    variant="outline"
                    size="icon"
                    class="size-14 border-destructive/30 text-destructive hover:bg-destructive! hover:text-destructive-foreground!"
                    aria-label="Void last transaction"
                    title="Void last transaction"
                    onclick={openVoidLastTransaction}
                    disabled={!lastCompletedInvoice || lastCompletedInvoice.status === "voided"}
                >
                    <Ban class="size-5" />
                </Button>
                <Button class="h-14 px-5" onclick={beginCheckout} disabled={cartItems.length === 0 || checkoutLoading}>
                    Charge
                </Button>
            </div>
            <Sheet.Content side="bottom" showCloseButton={false} class="h-[82dvh] max-h-[52rem] rounded-t-2xl px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
                <Sheet.Header>
                    <Sheet.Title class="flex items-center gap-2 text-sm">
                        <ShoppingCart class="size-4" />
                        Cart ({itemCount})
                        <span class="ml-auto flex items-center gap-1">
                            {#if cartItems.length > 0}
                                <button onclick={() => cart.clear()}
                                    class="min-h-11 rounded px-2 text-xs text-muted-foreground hover:bg-muted hover:text-destructive">
                                    Clear
                                </button>
                            {/if}
                            <Sheet.Close
                                class="flex size-11 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
                                aria-label="Close cart"
                            >
                                <X class="size-5" />
                            </Sheet.Close>
                        </span>
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
                                <li class="flex flex-wrap items-start gap-3 py-3">
                                    <div class="flex-1 min-w-0">
                                        <p class="font-medium text-sm">{item.name}</p>
                                        <p class="text-muted-foreground text-xs mt-0.5">
                                            {item.quantity}{item.unit} × ₱{item.unit_cost.toFixed(2)}
                                        </p>
                                    </div>
                                    <div class="ml-auto flex shrink-0 items-center gap-2">
                                        {#if item.pricing_type === "fixed"}
                                            <Button variant="outline" size="icon" class="size-11" onclick={() => cart.setQuantity(item.product_id, item.quantity - 1)} aria-label="Decrease {item.name}">
                                                <Minus class="size-4" />
                                            </Button>
                                            <Input
                                                type="number"
                                                min="1"
                                                max={item.stock_quantity}
                                                step="1"
                                                value={item.quantity}
                                                class="h-11 w-16 px-1 text-center text-sm"
                                                aria-label="Quantity for {item.name}"
                                                onchange={(event) => {
                                                    if (!setRetailQuantity(item, event.currentTarget.value)) {
                                                        event.currentTarget.value = String(item.quantity);
                                                    }
                                                }}
                                                onkeydown={(event) => {
                                                    if (event.key === "Enter") event.currentTarget.blur();
                                                }}
                                            />
                                            <Button variant="outline" size="icon" class="size-11" onclick={() => cart.setQuantity(item.product_id, item.quantity + 1)} disabled={item.quantity >= item.stock_quantity} aria-label="Increase {item.name}">
                                                <Plus class="size-4" />
                                            </Button>
                                        {/if}
                                        <span class="font-semibold text-sm text-primary">
                                            ₱{item.line_total.toFixed(2)}
                                        </span>
                                        <button
                                            onclick={() => cart.removeItem(item.product_id)}
                                            aria-label="Remove {item.name}"
                                            class="flex size-11 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-destructive"
                                        >
                                            <X class="size-4" />
                                        </button>
                                    </div>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
                <div class="pt-3 border-t space-y-3">
                    <div class="flex justify-between font-bold">
                        <span>Subtotal</span>
                        <span class="text-primary">₱{total.toFixed(2)}</span>
                    </div>
                    {#if discountType}
                        <div class="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs">
                            <div class="flex items-start justify-between gap-2">
                                <div>
                                    <p class="font-medium text-primary">{discountLabels[discountType]}</p>
                                    <p class="text-muted-foreground">ID: {discountIdNo}</p>
                                </div>
                                <button
                                    type="button"
                                    onclick={removeDiscount}
                                    aria-label="Remove applied discount"
                                    class="flex size-11 items-center justify-center rounded text-muted-foreground hover:bg-primary hover:text-primary-foreground"
                                >
                                    <X class="size-3.5" />
                                </button>
                            </div>
                            <div class="mt-2 flex justify-between font-medium">
                                <span>Estimated deduction</span>
                                <span>-₱{estimatedTotalDeduction.toFixed(2)}</span>
                            </div>
                        </div>
                        <div class="flex justify-between font-bold">
                            <span>Amount due</span>
                            <span class="text-primary">₱{payableTotal.toFixed(2)}</span>
                        </div>
                    {:else}
                        <Button
                            type="button"
                            variant="outline"
                            class="h-11 w-full border-primary/40 bg-primary/5 font-semibold text-primary hover:bg-primary! hover:text-primary-foreground!"
                            onclick={openDiscountDialog}
                            disabled={cartItems.length === 0}
                        >
                            Apply Discount
                        </Button>
                    {/if}
                    <Button class="w-full h-11" onclick={beginCheckout}
                        disabled={cartItems.length === 0 || checkoutLoading}>
                        {#if checkoutLoading}
                            <Loader2 class="size-4 animate-spin mr-2" />
                        {/if}
                        Charge ₱{payableTotal.toFixed(2)}
                    </Button>
                </div>
            </Sheet.Content>
        </Sheet.Root>
    </div>
</div>

<Dialog.Root bind:open={discountDialogOpen}>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Apply Discount</Dialog.Title>
            <Dialog.Description>
                Select the verified statutory discount and enter the customer ID before charging.
            </Dialog.Description>
        </Dialog.Header>

        <div class="space-y-4">
            {#if discountError}
                <div class="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
                    {discountError}
                </div>
            {/if}

            <div class="space-y-2">
                <Label for="discount-type">Discount type</Label>
                <Select.Root type="single" bind:value={discountDraftType}>
                    <Select.Trigger id="discount-type" class="h-11 w-full" aria-label="Discount type">
                        <span data-slot="select-value">
                            {discountDraftType ? discountLabels[discountDraftType] : "Select discount type"}
                        </span>
                    </Select.Trigger>
                    <Select.Content>
                        <Select.Item value="senior_citizen">Senior Citizen (SC)</Select.Item>
                        <Select.Item value="pwd">Person with Disability (PWD)</Select.Item>
                        <Select.Item value="naac">National Athlete (NAAC)</Select.Item>
                        <Select.Item value="solo_parent">Solo Parent</Select.Item>
                    </Select.Content>
                </Select.Root>
            </div>

            <div class="space-y-2">
                <Label for="precharge-discount-id">ID number</Label>
                <Input
                    id="precharge-discount-id"
                    class="h-11"
                    placeholder="Enter the card or ID number"
                    bind:value={discountDraftIdNo}
                    autocomplete="off"
                />
            </div>

            {#if discountDraftType}
                <div class="rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                    Estimated deduction: <span class="font-semibold text-foreground">₱{(
                        discountDraftType === "senior_citizen" || discountDraftType === "pwd"
                            ? Math.max(0, total - estimatedVatAmount) * 0.20 +
                                estimatedVatAmount
                            : discountDraftType === "naac"
                                ? total * 0.20
                                : total * 0.10
                    ).toFixed(2)}</span>
                    <span class="mt-1 block">The server verifies the final amount when the sale is completed.</span>
                </div>
            {/if}
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => discountDialogOpen = false}>Cancel</Button>
            <Button onclick={applyDiscount} disabled={!discountDraftType || !discountDraftIdNo.trim()}>
                Apply Discount
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<Dialog.Root bind:open={checkoutDialogOpen}>
    <Dialog.Content class="max-w-lg max-h-[90vh] overflow-y-auto">
        <Dialog.Header>
            <Dialog.Title>Cash Payment</Dialog.Title>
            <Dialog.Description>Confirm cash received and complete the sale. Discounts must be applied from the cart before charging.</Dialog.Description>
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

            <div>
                <Button type="button" variant={showBuyerFields ? "default" : "outline"} onclick={() => showBuyerFields = !showBuyerFields}>
                    Buyer Info
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

        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => checkoutDialogOpen = false}>Cancel</Button>
            <Button
                onclick={checkout}
                disabled={checkoutLoading || (Number(cashTendered) || 0) < payableTotal ||
                    (!!discountType && !discountIdNo.trim())}
                aria-busy={checkoutLoading}
            >
                {#if checkoutLoading}<Loader2 class="size-4 animate-spin mr-2" />{/if}
                Complete Sale
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<Dialog.Root bind:open={voidDialogOpen}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Void Last Transaction</Dialog.Title>
            <Dialog.Description>
                This voids the most recent completed sale and restores its stock. A reason is required.
            </Dialog.Description>
        </Dialog.Header>

        {#if lastCompletedInvoice}
            <div class="rounded-xl border bg-muted/40 p-3 text-sm">
                <div class="flex items-center justify-between gap-3">
                    <span class="font-medium">Invoice #{lastCompletedInvoice.display_invoice_number ?? lastCompletedInvoice.invoice_number}</span>
                    <Badge variant={lastCompletedInvoice.status === "voided" ? "destructive" : "outline"}>
                        {lastCompletedInvoice.status}
                    </Badge>
                </div>
                <p class="text-xs text-muted-foreground mt-1">
                    Total: ₱{Number(lastCompletedInvoice.total_amount).toFixed(2)}
                </p>
            </div>
        {/if}

        <div class="space-y-3">
            <div class="space-y-2">
                <Label>Common reasons</Label>
                <div class="flex flex-wrap gap-2">
                    {#each quickVoidReasons as reason}
                        <Button
                            type="button"
                            variant={voidReason === reason ? "default" : "outline"}
                            size="sm"
                            onclick={() => selectVoidReason(reason)}
                            aria-pressed={voidReason === reason}
                        >
                            {reason}
                        </Button>
                    {/each}
                </div>
            </div>
            <div class="space-y-2">
                <Label for="void-reason">Reason</Label>
                <textarea
                    id="void-reason"
                    placeholder="Add or edit the void reason..."
                    bind:value={voidReason}
                    rows="3"
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                    aria-label="Void reason"
                    required
                ></textarea>
            </div>
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => voidDialogOpen = false}>Cancel</Button>
            <Button
                variant="destructive"
                onclick={voidLastTransaction}
                disabled={!voidReason.trim() || voidLoading}
                aria-busy={voidLoading}
            >
                {#if voidLoading}<Loader2 class="size-4 animate-spin mr-2" />{/if}
                Void Sale
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<Dialog.Root bind:open={receiptDialogOpen}>
    <Dialog.Content class="flex max-h-[92dvh] max-w-2xl grid-rows-[auto_1fr_auto] flex-col overflow-hidden">
        <Dialog.Header>
            <Dialog.Title>Receipt Preview</Dialog.Title>
            <Dialog.Description>This is the same receipt layout that will be sent to the printer.</Dialog.Description>
        </Dialog.Header>

        <div class="min-h-0 flex-1 overflow-hidden rounded-xl border bg-muted/30 p-2">
            {#if receiptLoading}
                <div class="flex h-[55dvh] items-center justify-center gap-2 text-muted-foreground">
                    <Loader2 class="size-5 animate-spin" />
                    <span>Preparing receipt preview...</span>
                </div>
            {:else if receiptHtml}
                <iframe
                    bind:this={receiptFrame}
                    title="Receipt print preview"
                    srcdoc={receiptHtml}
                    class="h-[55dvh] w-full rounded-lg bg-white"
                ></iframe>
            {:else}
                <div class="flex h-[55dvh] flex-col items-center justify-center gap-3 text-center text-muted-foreground">
                    <ReceiptText class="size-8 opacity-40" />
                    <p>Receipt preview could not be loaded.</p>
                    {#if lastInvoice}
                        <Button variant="outline" onclick={() => loadReceiptPreview(lastInvoice.id)}>Try Again</Button>
                    {/if}
                </div>
            {/if}
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={nextTransaction}>Next Transaction</Button>
            <Button onclick={printLastReceipt} disabled={receiptLoading || !receiptHtml}>Print Receipt</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
