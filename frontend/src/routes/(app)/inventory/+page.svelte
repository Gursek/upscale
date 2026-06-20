<script lang="ts">
    import { onMount } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { apiFetch, apiJson, API_BASE } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import { Badge } from "$lib/components/ui/badge";
    import * as Select from "$lib/components/ui/select";
    import * as Dialog from "$lib/components/ui/dialog";
    import * as AlertDialog from "$lib/components/ui/alert-dialog";
    import AppQuickNav from "$lib/components/AppQuickNav.svelte";
    import {
        Plus, Pencil, Archive, RotateCcw, Trash2,
        Loader2, Package, AlertTriangle,
        Search, PackagePlus, PackageMinus, SlidersHorizontal, History, ImagePlus,
        ChevronLeft, ChevronRight, X
    } from "lucide-svelte";

    interface HistoryEntry {
        id: number;
        action: string;
        product_id: number;
        product_name: string;
        unit: string;
        before_stock: number | null;
        after_stock: number | null;
        quantity_added?: number;
        adjustment_delta?: number;
        reason?: string;
        notes?: string;
        reverted: boolean;
        created_at: string;
    }

    // --- State ---
    let products = $state<any[]>([]);
    let archivedProducts = $state<any[]>([]);
    let history = $state<HistoryEntry[]>([]);
    let loading = $state(true);
    let historyLoading = $state(false);
    let error = $state("");
    let successMessage = $state("");
    let searchQuery = $state("");
    let activeTab = $state<"active" | "archived" | "history">("active");
    let categoryFilter = $state("all");
    let stockFilter = $state("all");
    let pricingFilter = $state("all");
    let sortBy = $state("name_asc");
    let currentPage = $state(1);
    const productsPerPage = 25;

    // --- Dialog state ---
    let productDialogOpen = $state(false);
    let archiveDialogOpen = $state(false);
    let deleteDialogOpen = $state(false);
    let restockDialogOpen = $state(false);
    let adjustDialogOpen = $state(false);
    let selectedProduct = $state<any>(null);
    let isEditing = $state(false);
    let restockQuantity = $state("");
    let restockNotes = $state("");
    let adjustQuantity = $state("");
    let adjustReason = $state("");
    let adjustMode = $state<"set" | "deduct">("set");
    let uploadingImage = $state(false);
    let cutTypeSelection = $state("");

    // --- Form state ---
    let form = $state({
        name: "",
        category: "pork",
        cut_type: "",
        pricing_type: "per_kg",
        price: "",
        unit: "kg",
        sku: "",
        stock_quantity: "",
        low_stock_threshold: "",
        tax_classification: "exempt",
        image_url: "",
    });

    // --- Derived ---
    let user = $derived($auth);
    const cutTypesByCategory: Record<string, string[]> = {
        chicken: ["Breast", "Thigh", "Drumstick", "Wing", "Liver", "Gizzard", "Feet", "Neck", "Whole", "Other"],
        pork: ["Belly (Liempo)", "Kasim (Shoulder)", "Pigue (Ham)", "Chop", "Ribs", "Liver", "Tenderloin", "Whole", "Other"],
        beef: ["Brisket", "Chuck", "Sirloin", "Short Rib", "Shank", "Tenderloin", "Ground", "Whole", "Other"],
    };
    let availableCutTypes = $derived(cutTypesByCategory[form.category] ?? []);

    let availableCategories = $derived(
        [...new Set(products.map((product) => product.category))].sort()
    );

    function stockStatus(product: any) {
        const stock = Number(product.stock_quantity);
        const threshold = Number(product.low_stock_threshold);
        if (stock <= 0) return "out";
        if (threshold > 0 && stock <= threshold) return "low";
        return "in";
    }

    let filteredProducts = $derived.by(() => {
        const query = searchQuery.trim().toLowerCase();
        const result = products.filter((product) => {
            const matchesSearch = !query ||
                product.name.toLowerCase().includes(query) ||
                (product.sku ?? "").toLowerCase().includes(query) ||
                (product.cut_type ?? "").toLowerCase().includes(query);
            const matchesCategory = categoryFilter === "all" || product.category === categoryFilter;
            const matchesStock = stockFilter === "all" || stockStatus(product) === stockFilter;
            const matchesPricing = pricingFilter === "all" || product.pricing_type === pricingFilter;
            return matchesSearch && matchesCategory && matchesStock && matchesPricing;
        });

        return result.sort((a, b) => {
            if (sortBy === "name_desc") return b.name.localeCompare(a.name);
            if (sortBy === "stock_asc") return Number(a.stock_quantity) - Number(b.stock_quantity);
            if (sortBy === "stock_desc") return Number(b.stock_quantity) - Number(a.stock_quantity);
            if (sortBy === "price_asc") return Number(a.price) - Number(b.price);
            if (sortBy === "price_desc") return Number(b.price) - Number(a.price);
            if (sortBy === "updated_desc") {
                return new Date(b.updated_at ?? 0).getTime() - new Date(a.updated_at ?? 0).getTime();
            }
            return a.name.localeCompare(b.name);
        });
    });

    let totalPages = $derived(Math.max(1, Math.ceil(filteredProducts.length / productsPerPage)));
    let paginatedProducts = $derived(
        filteredProducts.slice((currentPage - 1) * productsPerPage, currentPage * productsPerPage)
    );
    let pageStart = $derived(filteredProducts.length === 0 ? 0 : (currentPage - 1) * productsPerPage + 1);
    let pageEnd = $derived(Math.min(currentPage * productsPerPage, filteredProducts.length));
    let lowStockCount = $derived(products.filter((product) => stockStatus(product) === "low").length);
    let hasActiveFilters = $derived(
        categoryFilter !== "all" ||
        stockFilter !== "all" ||
        pricingFilter !== "all" ||
        searchQuery.trim() !== ""
    );

    $effect(() => {
        searchQuery;
        categoryFilter;
        stockFilter;
        pricingFilter;
        sortBy;
        currentPage = 1;
    });

    $effect(() => {
        if (currentPage > totalPages) currentPage = totalPages;
    });

    let filteredArchived = $derived(
        archivedProducts.filter((p) =>
            p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (p.sku ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
            (p.cut_type ?? "").toLowerCase().includes(searchQuery.toLowerCase())
        )
    );

    function clearFilters() {
        searchQuery = "";
        categoryFilter = "all";
        stockFilter = "all";
        pricingFilter = "all";
    }

    function toggleLowStockFilter() {
        stockFilter = stockFilter === "low" ? "all" : "low";
    }

    function formatUpdated(value: string | null | undefined) {
        if (!value) return "Not recorded";
        return new Date(value).toLocaleDateString("en-PH", {
            timeZone: "Asia/Manila",
            month: "short",
            day: "numeric",
            year: "numeric",
        });
    }

    // --- Load ---
    onMount(async () => {
        const token = localStorage.getItem("access_token");
        if (!token) { goto("/login"); return; }
        await loadProducts();
    });

    async function loadProducts() {
        loading = true;
        try {
            [products, archivedProducts] = await Promise.all([
                apiJson<any[]>("/products/"),
                apiJson<any[]>("/products/archived"),
            ]);
        } catch {
            error = "Failed to load products";
        } finally {
            loading = false;
        }
    }

    async function loadHistory() {
        historyLoading = true;
        try {
            history = await apiJson<HistoryEntry[]>("/inventory/history?limit=50");
        } catch {
            error = "Failed to load history";
        } finally {
            historyLoading = false;
        }
    }

    async function switchTab(tab: "active" | "archived" | "history") {
        activeTab = tab;
        if (tab === "history") await loadHistory();
    }

    function openRestockDialog(product: any) {
        selectedProduct = product;
        restockQuantity = "";
        restockNotes = "";
        restockDialogOpen = true;
    }

    function openAdjustDialog(product: any, mode: "set" | "deduct" = "set") {
        selectedProduct = product;
        adjustMode = mode;
        adjustQuantity = mode === "set" ? String(product.stock_quantity) : "";
        adjustReason = "";
        adjustDialogOpen = true;
    }

    function selectRestockReason(reason: string) {
        restockNotes = reason;
    }

    function selectAdjustReason(reason: string) {
        adjustReason = reason;
    }

    async function restockProduct() {
        const qty = parseFloat(restockQuantity);
        if (!qty || qty <= 0) {
            flash("Enter a valid quantity", true);
            return;
        }
        if (!restockNotes.trim()) {
            flash("Reason is required for stock additions", true);
            return;
        }
        try {
            await apiJson("/inventory/restock", {
                method: "POST",
                body: JSON.stringify({
                    product_id: selectedProduct.id,
                    quantity: qty,
                    notes: restockNotes.trim(),
                }),
            });
            flash(`Restocked ${selectedProduct.name}`);
            restockDialogOpen = false;
            await loadProducts();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    async function adjustProduct() {
        const enteredQty = parseFloat(adjustQuantity);
        if (isNaN(enteredQty) || enteredQty < 0) {
            flash(adjustMode === "deduct" ? "Enter a valid quantity to deduct" : "Enter a valid stock quantity", true);
            return;
        }
        if (!adjustReason.trim()) {
            flash("Reason is required", true);
            return;
        }
        const currentStock = Number(selectedProduct.stock_quantity);
        const newQty = adjustMode === "deduct" ? currentStock - enteredQty : enteredQty;
        if (newQty < 0) {
            flash(`Cannot deduct more than current stock (${formatStock(currentStock, selectedProduct.unit)})`, true);
            return;
        }
        try {
            await apiJson("/inventory/adjust", {
                method: "POST",
                body: JSON.stringify({
                    product_id: selectedProduct.id,
                    new_quantity: newQty,
                    reason: adjustReason.trim(),
                }),
            });
            flash(adjustMode === "deduct" ? `Deducted stock for ${selectedProduct.name}` : `Adjusted stock for ${selectedProduct.name}`);
            adjustDialogOpen = false;
            await loadProducts();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    function formatStock(value: number | null | undefined, unit: string) {
        if (value == null) return "—";
        return `${Number(value).toFixed(unit === "kg" ? 3 : 0)} ${unit}`;
    }

    const actionLabels: Record<string, string> = {
        restock: "Restock",
        adjustment: "Adjustment",
        sale_deduction: "Sale",
        void_restock: "Void restock",
    };

    const restockReasons = ["Supplier delivery", "Opening inventory", "Returned item"];
    const stockDeductionReasons = ["Mistake", "Theft", "Spoilage"];
    const stockAdjustmentReasons = ["Physical count correction", "Wrong previous entry", "Unit conversion correction"];

    // --- Form helpers ---
    function openCreateDialog() {
        isEditing = false;
        form = {
            name: "", category: defaultCategory(), cut_type: "",
            pricing_type: "per_kg", price: "", unit: "kg",
            sku: "", stock_quantity: "", low_stock_threshold: "",
            tax_classification: "exempt",
            image_url: "",
        };
        cutTypeSelection = "";
        productDialogOpen = true;
    }

    function openEditDialog(product: any) {
        isEditing = true;
        selectedProduct = product;
        form = {
            name: product.name,
            category: product.category,
            cut_type: product.cut_type ?? "",
            pricing_type: product.pricing_type,
            price: String(product.price),
            unit: product.unit,
            sku: product.sku ?? "",
            stock_quantity: String(product.stock_quantity),
            low_stock_threshold: String(product.low_stock_threshold),
            tax_classification: product.tax_classification,
            image_url: product.image_url ?? "",
        };
        const categoryCuts = cutTypesByCategory[product.category] ?? [];
        cutTypeSelection = categoryCuts.includes(product.cut_type) ? product.cut_type : (product.cut_type ? "Other" : "");
        productDialogOpen = true;
    }

    // Auto-set unit and tax_classification when category changes
    function onCategoryChange() {
        if (form.category === "retail") {
            form.pricing_type = "fixed";
            form.unit = "pcs";
            form.tax_classification = "standard";
            form.cut_type = "";
            cutTypeSelection = "";
        } else {
            form.pricing_type = "per_kg";
            form.unit = "kg";
            form.tax_classification = "exempt";
            form.cut_type = "";
            cutTypeSelection = "";
        }
    }

    function onCutTypeChange(value: string) {
        cutTypeSelection = value;
        form.cut_type = value === "Other" ? "" : value;
    }

    function defaultCategory() {
        if (user?.sells_meat) return "pork";
        if (user?.sells_fish) return "fish";
        if (user?.sells_retail) return "retail";
        return "veggies";
    }

    function productImageUrl(path: string | null) {
        if (!path) return null;
        return path.startsWith("http") ? path : `${API_BASE.replace("/api", "")}${path}`;
    }

    async function uploadImage(event: Event) {
        const input = event.currentTarget as HTMLInputElement;
        const file = input.files?.[0];
        if (!file) return;
        uploadingImage = true;
        try {
            const body = new FormData();
            body.append("image", file);
            const response = await apiFetch("/products/upload-image", { method: "POST", body });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Image upload failed");
            form.image_url = data.image_url;
        } catch (e: any) {
            flash(e.message, true);
        } finally {
            uploadingImage = false;
            input.value = "";
        }
    }

    function flash(msg: string, isError = false) {
        if (isError) { error = msg; setTimeout(() => error = "", 4000); }
        else { successMessage = msg; setTimeout(() => successMessage = "", 3000); }
    }

    // --- CRUD ---
    async function saveProduct() {
        try {
            const payload: Record<string, unknown> = {
                ...form,
                price: parseFloat(form.price),
                low_stock_threshold: parseFloat(form.low_stock_threshold || "0"),
            };
            if (!isEditing) {
                payload.stock_quantity = parseFloat(form.stock_quantity || "0");
            } else {
                delete payload.stock_quantity;
            }
            if (isEditing) {
                await apiJson(`/products/${selectedProduct.id}`, {
                    method: "PUT",
                    body: JSON.stringify(payload),
                });
                flash("Product updated");
            } else {
                await apiJson("/products/", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });
                flash("Product created");
            }
            productDialogOpen = false;
            await loadProducts();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    async function archiveProduct() {
        try {
            await apiJson(`/products/${selectedProduct.id}/archive`, { method: "POST" });
            flash("Product archived");
            archiveDialogOpen = false;
            await loadProducts();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    async function restoreProduct(product: any) {
        try {
            await apiJson(`/products/${product.id}/restore`, { method: "POST" });
            flash("Product restored");
            await loadProducts();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    async function deleteProduct() {
        try {
            await apiJson(`/products/${selectedProduct.id}`, { method: "DELETE" });
            flash("Product permanently deleted");
            deleteDialogOpen = false;
            await loadProducts();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    const categoryLabels: Record<string, string> = {
        beef: "Beef", pork: "Pork", chicken: "Chicken", fish: "Fish", retail: "Retail", veggies: "Veggies"
    };

    const categoryEmoji: Record<string, string> = {
        beef: "🥩", pork: "🥓", chicken: "🍗", fish: "🐟", retail: "📦", veggies: "🥕"
    };
</script>

<div class="min-h-screen bg-muted/30">

    <!-- Header -->
    <header class="bg-background border-b px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <Package class="size-5 text-primary" />
        <h1 class="font-semibold text-sm flex-1">Inventory</h1>
        <Button size="sm" onclick={openCreateDialog} aria-label="Add new product">
            <Plus class="size-4 mr-1" /> Add Product
        </Button>
        <AppQuickNav current="/inventory" />
    </header>

    <!-- Alerts -->
    {#if error}
        <div class="bg-destructive/10 text-destructive text-sm px-4 py-2 text-center" role="alert">{error}</div>
    {/if}
    {#if successMessage}
        <div class="bg-green-500/10 text-green-700 text-sm px-4 py-2 text-center" role="status">{successMessage}</div>
    {/if}

    <div class="mx-auto max-w-7xl space-y-4 p-3 sm:p-4">

        <!-- Tabs -->
        <div class="overflow-x-auto">
            <div class="flex min-w-max rounded-md border bg-background text-sm">
                <button
                    onclick={() => switchTab("active")}
                    class="min-h-11 px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'active' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "active"}
                >
                    Active ({products.length})
                </button>
                <button
                    onclick={() => switchTab("archived")}
                    class="min-h-11 border-l px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'archived' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "archived"}
                >
                    Archived ({archivedProducts.length})
                </button>
                <button
                    onclick={() => switchTab("history")}
                    class="min-h-11 border-l px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'history' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "history"}
                >
                    History
                </button>
            </div>
        </div>

        {#if activeTab === "active"}
            <section class="rounded-xl border bg-background p-3 shadow-sm" aria-label="Inventory filters">
                <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(16rem,1fr)_repeat(4,minmax(9rem,auto))]">
                    <div class="relative">
                        <Search class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Search name, SKU, or cut type"
                            bind:value={searchQuery}
                            class="h-11 pl-9"
                            aria-label="Search products by name, SKU, or cut type"
                        />
                    </div>

                    <Select.Root type="single" bind:value={categoryFilter}>
                        <Select.Trigger class="h-11 w-full" aria-label="Filter by category">
                            <span data-slot="select-value">
                                {categoryFilter === "all" ? "All categories" : categoryLabels[categoryFilter] ?? categoryFilter}
                            </span>
                        </Select.Trigger>
                        <Select.Content>
                            <Select.Item value="all">All categories</Select.Item>
                            {#each availableCategories as category}
                                <Select.Item value={category}>{categoryLabels[category] ?? category}</Select.Item>
                            {/each}
                        </Select.Content>
                    </Select.Root>

                    <Select.Root type="single" bind:value={stockFilter}>
                        <Select.Trigger class="h-11 w-full" aria-label="Filter by stock status">
                            <span data-slot="select-value">
                                {stockFilter === "all" ? "All stock" :
                                    stockFilter === "in" ? "In stock" :
                                    stockFilter === "low" ? "Low stock" : "Out of stock"}
                            </span>
                        </Select.Trigger>
                        <Select.Content>
                            <Select.Item value="all">All stock</Select.Item>
                            <Select.Item value="in">In stock</Select.Item>
                            <Select.Item value="low">Low stock</Select.Item>
                            <Select.Item value="out">Out of stock</Select.Item>
                        </Select.Content>
                    </Select.Root>

                    <Select.Root type="single" bind:value={pricingFilter}>
                        <Select.Trigger class="h-11 w-full" aria-label="Filter by pricing type">
                            <span data-slot="select-value">
                                {pricingFilter === "all" ? "All pricing" :
                                    pricingFilter === "per_kg" ? "Per kilogram" : "Fixed price"}
                            </span>
                        </Select.Trigger>
                        <Select.Content>
                            <Select.Item value="all">All pricing</Select.Item>
                            <Select.Item value="per_kg">Per kilogram</Select.Item>
                            <Select.Item value="fixed">Fixed price</Select.Item>
                        </Select.Content>
                    </Select.Root>

                    <Select.Root type="single" bind:value={sortBy}>
                        <Select.Trigger class="h-11 w-full" aria-label="Sort products">
                            <span data-slot="select-value">
                                {sortBy === "name_asc" ? "Name A-Z" :
                                    sortBy === "name_desc" ? "Name Z-A" :
                                    sortBy === "stock_asc" ? "Stock: low first" :
                                    sortBy === "stock_desc" ? "Stock: high first" :
                                    sortBy === "price_asc" ? "Price: low first" :
                                    sortBy === "price_desc" ? "Price: high first" : "Recently updated"}
                            </span>
                        </Select.Trigger>
                        <Select.Content>
                            <Select.Item value="name_asc">Name A-Z</Select.Item>
                            <Select.Item value="name_desc">Name Z-A</Select.Item>
                            <Select.Item value="stock_asc">Stock: low first</Select.Item>
                            <Select.Item value="stock_desc">Stock: high first</Select.Item>
                            <Select.Item value="price_asc">Price: low first</Select.Item>
                            <Select.Item value="price_desc">Price: high first</Select.Item>
                            <Select.Item value="updated_desc">Recently updated</Select.Item>
                        </Select.Content>
                    </Select.Root>
                </div>

                <div class="mt-3 flex flex-wrap items-center gap-2">
                    <Button
                        type="button"
                        variant={stockFilter === "low" ? "default" : "outline"}
                        class="h-10"
                        onclick={toggleLowStockFilter}
                        aria-pressed={stockFilter === "low"}
                    >
                        <AlertTriangle class="mr-2 size-4" />
                        Low stock ({lowStockCount})
                    </Button>
                    {#if hasActiveFilters}
                        <Button type="button" variant="ghost" class="h-10" onclick={clearFilters}>
                            <X class="mr-2 size-4" /> Clear filters
                        </Button>
                    {/if}
                    <p class="ml-auto text-xs text-muted-foreground">
                        {filteredProducts.length} of {products.length} products
                    </p>
                </div>
            </section>
        {:else if activeTab === "archived"}
            <div class="relative max-w-md">
                <Search class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                    placeholder="Search archived products"
                    bind:value={searchQuery}
                    class="h-11 pl-9"
                    aria-label="Search archived products"
                />
            </div>
        {/if}

        <!-- Product list -->
        {#if loading}
            <div class="flex items-center justify-center h-40">
                <Loader2 class="size-6 animate-spin text-muted-foreground" />
            </div>
        {:else}
            {#if activeTab === "active"}
                {#if filteredProducts.length === 0}
                    <div class="flex min-h-56 flex-col items-center justify-center gap-2 rounded-xl border bg-background text-muted-foreground">
                        <Package class="size-8" />
                        <p class="text-sm font-medium">
                            {products.length === 0 ? "No products yet" : "No products match these filters"}
                        </p>
                        {#if products.length === 0}
                            <Button variant="outline" size="sm" onclick={openCreateDialog}>Add your first product</Button>
                        {:else}
                            <Button variant="outline" size="sm" onclick={clearFilters}>Clear filters</Button>
                        {/if}
                    </div>
                {:else}
                    <div class="overflow-hidden rounded-xl border bg-background shadow-sm">
                        <div class="overflow-x-auto">
                            <div class="grid min-w-[960px] grid-cols-[minmax(260px,1.4fr)_110px_110px_130px_120px_110px_260px] gap-3 border-b bg-muted/50 px-4 py-3 text-xs font-medium text-muted-foreground">
                                <span>Product</span>
                                <span>Category</span>
                                <span>Pricing</span>
                                <span>Stock</span>
                                <span>Low alert</span>
                                <span>Price</span>
                                <span class="text-right">Actions</span>
                            </div>
                            <div class="min-w-[960px] divide-y" role="list" aria-label="Active products">
                        {#each paginatedProducts as product (product.id)}
                            <div role="listitem"
                                class="grid grid-cols-[minmax(260px,1.4fr)_110px_110px_130px_120px_110px_260px] items-center gap-3 bg-background px-4 py-3">
                                <div class="flex min-w-0 items-center gap-3">
                                <div class="size-12 rounded-lg bg-muted overflow-hidden flex items-center justify-center text-2xl shrink-0">
                                    {#if productImageUrl(product.image_url)}
                                        <img src={productImageUrl(product.image_url)} alt="" class="size-full object-cover" />
                                    {:else}
                                        {categoryEmoji[product.category] ?? "📦"}
                                    {/if}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 flex-wrap">
                                        <p class="font-medium text-sm">{product.name}</p>
                                        {#if product.cut_type}
                                            <span class="text-muted-foreground text-xs">({product.cut_type})</span>
                                        {/if}
                                    </div>
                                    <div class="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                                        {#if product.sku}
                                            <span>SKU: {product.sku}</span>
                                        {/if}
                                    </div>
                                    <p class="mt-0.5 text-[11px] text-muted-foreground">Updated {formatUpdated(product.updated_at)}</p>
                                </div>
                                </div>
                                <div>
                                    <Badge variant="outline">{categoryLabels[product.category] ?? product.category}</Badge>
                                </div>
                                <p class="text-sm">{product.pricing_type === "per_kg" ? "Per kg" : "Fixed"}</p>
                                <div class="space-y-1">
                                    <p class="whitespace-nowrap text-sm font-semibold">{formatStock(product.stock_quantity, product.unit)}</p>
                                    {#if stockStatus(product) === "out"}
                                        <Badge variant="destructive">Out</Badge>
                                    {:else if stockStatus(product) === "low"}
                                        <Badge variant="destructive" class="gap-1"><AlertTriangle class="size-3" /> Low</Badge>
                                    {:else}
                                        <Badge variant="secondary">In stock</Badge>
                                    {/if}
                                </div>
                                <p class="whitespace-nowrap text-sm">{formatStock(product.low_stock_threshold, product.unit)}</p>
                                <p class="whitespace-nowrap text-sm font-medium">₱{Number(product.price).toFixed(2)}</p>
                                <div class="flex items-center justify-end gap-1 shrink-0">
                                    <Button variant="ghost" size="icon" class="size-10"
                                        aria-label="Restock {product.name}"
                                        onclick={() => openRestockDialog(product)}>
                                        <PackagePlus class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" class="size-10"
                                        aria-label="Deduct stock for {product.name}"
                                        onclick={() => openAdjustDialog(product, "deduct")}>
                                        <PackageMinus class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" class="size-10"
                                        aria-label="Adjust stock for {product.name}"
                                        onclick={() => openAdjustDialog(product)}>
                                        <SlidersHorizontal class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" class="size-10"
                                        aria-label="Edit {product.name}"
                                        onclick={() => openEditDialog(product)}>
                                        <Pencil class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" class="size-10"
                                        aria-label="Archive {product.name}"
                                        onclick={() => { selectedProduct = product; archiveDialogOpen = true; }}>
                                        <Archive class="size-4" />
                                    </Button>
                                </div>
                            </div>
                        {/each}
                            </div>
                        </div>
                        <div class="flex flex-col gap-3 border-t px-3 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                            <p class="text-muted-foreground">
                                Showing {pageStart}-{pageEnd} of {filteredProducts.length}
                            </p>
                            <div class="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    size="icon"
                                    class="size-10"
                                    onclick={() => currentPage = Math.max(1, currentPage - 1)}
                                    disabled={currentPage === 1}
                                    aria-label="Previous product page"
                                >
                                    <ChevronLeft class="size-4" />
                                </Button>
                                <span class="min-w-24 text-center">Page {currentPage} of {totalPages}</span>
                                <Button
                                    variant="outline"
                                    size="icon"
                                    class="size-10"
                                    onclick={() => currentPage = Math.min(totalPages, currentPage + 1)}
                                    disabled={currentPage === totalPages}
                                    aria-label="Next product page"
                                >
                                    <ChevronRight class="size-4" />
                                </Button>
                            </div>
                        </div>
                    </div>
                {/if}

            {:else if activeTab === "archived"}
                {#if filteredArchived.length === 0}
                    <div class="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                        <Archive class="size-8" />
                        <p class="text-sm">No archived products</p>
                    </div>
                {:else}
                    <div class="space-y-2" role="list" aria-label="Archived products">
                        {#each filteredArchived as product (product.id)}
                            <div role="listitem"
                                class="bg-background rounded-xl border border-dashed p-4 flex items-center gap-4 opacity-75">
                                <div class="text-2xl grayscale">{categoryEmoji[product.category] ?? "📦"}</div>
                                <div class="flex-1 min-w-0">
                                    <p class="font-medium text-sm line-through text-muted-foreground">{product.name}</p>
                                    <p class="text-xs text-muted-foreground mt-0.5">
                                        Archived {product.archived_at ? new Date(product.archived_at).toLocaleDateString() : ""}
                                    </p>
                                </div>
                                <div class="flex items-center gap-1 shrink-0">
                                    <Button variant="ghost" size="icon"
                                        aria-label="Restore {product.name}"
                                        onclick={() => restoreProduct(product)}>
                                        <RotateCcw class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon"
                                        aria-label="Permanently delete {product.name}"
                                        onclick={() => { selectedProduct = product; deleteDialogOpen = true; }}>
                                        <Trash2 class="size-4 text-destructive" />
                                    </Button>
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}

            {:else}
                {#if historyLoading}
                    <div class="flex items-center justify-center h-40">
                        <Loader2 class="size-6 animate-spin text-muted-foreground" />
                    </div>
                {:else if history.length === 0}
                    <div class="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                        <History class="size-8" />
                        <p class="text-sm">No stock movements yet</p>
                    </div>
                {:else}
                    <ul class="space-y-2" aria-label="Stock movement history">
                        {#each history as entry (entry.id)}
                            <li class="bg-background rounded-xl border p-4 {entry.reverted ? 'opacity-60' : ''}">
                                <div class="flex items-start justify-between gap-3">
                                    <div class="min-w-0">
                                        <div class="flex items-center gap-2 flex-wrap">
                                            <p class="font-medium text-sm">{entry.product_name}</p>
                                            <Badge variant="outline" class="text-xs">
                                                {actionLabels[entry.action] ?? entry.action}
                                            </Badge>
                                            {#if entry.reverted}
                                                <Badge variant="secondary" class="text-xs">Undone</Badge>
                                            {/if}
                                        </div>
                                        <p class="text-xs text-muted-foreground mt-1">
                                            {formatStock(entry.before_stock, entry.unit)}
                                            →
                                            {formatStock(entry.after_stock, entry.unit)}
                                            {#if entry.quantity_added}
                                                <span class="text-green-700"> (+{entry.quantity_added})</span>
                                            {/if}
                                            {#if entry.adjustment_delta != null && entry.action === "adjustment"}
                                                <span class={entry.adjustment_delta >= 0 ? "text-green-700" : "text-destructive"}>
                                                    ({entry.adjustment_delta >= 0 ? "+" : ""}{entry.adjustment_delta})
                                                </span>
                                            {/if}
                                        </p>
                                        {#if entry.reason}
                                            <p class="text-xs text-muted-foreground mt-0.5">Reason: {entry.reason}</p>
                                        {/if}
                                        {#if entry.notes}
                                            <p class="text-xs text-muted-foreground mt-0.5">Notes: {entry.notes}</p>
                                        {/if}
                                    </div>
                                    <p class="text-xs text-muted-foreground shrink-0">
                                        {new Date(entry.created_at).toLocaleString("en-PH", { timeZone: "Asia/Manila" })}
                                    </p>
                                </div>
                            </li>
                        {/each}
                    </ul>
                {/if}
            {/if}
        {/if}
    </div>
</div>

<!-- Add/Edit Product Dialog -->
<Dialog.Root bind:open={productDialogOpen}>
    <Dialog.Content class="max-w-md max-h-[90vh] overflow-y-auto">
        <Dialog.Header>
            <Dialog.Title>{isEditing ? "Edit Product" : "Add Product"}</Dialog.Title>
            <Dialog.Description>
                {isEditing ? "Update product details." : "Add a new product to your inventory."}
            </Dialog.Description>
        </Dialog.Header>

        <div class="space-y-4 py-2">

            <div class="space-y-2">
                <Label for="category">Category</Label>
                <select id="category" bind:value={form.category}
                    onchange={onCategoryChange}
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    aria-label="Product category">
                    {#if user?.sells_meat}
                        <option value="beef">🥩 Beef</option>
                        <option value="pork">🥓 Pork</option>
                        <option value="chicken">🍗 Chicken</option>
                    {/if}
                    {#if user?.sells_fish}
                        <option value="fish">🐟 Fish</option>
                    {/if}
                    {#if user?.sells_retail}
                        <option value="retail">📦 Retail</option>
                    {/if}
                    {#if user?.sells_veggies}
                        <option value="veggies">🥕 Veggies</option>
                    {/if}
                </select>
            </div>

            <div class="space-y-2">
                <Label for="prod-name">Product Name</Label>
                <Input id="prod-name" placeholder="e.g. Pork Belly" bind:value={form.name} />
            </div>

            <div class="space-y-2">
                <Label for="product-image">Product Image <span class="text-muted-foreground">(optional)</span></Label>
                <div class="flex items-center gap-3">
                    <div class="size-16 rounded-lg border bg-muted overflow-hidden flex items-center justify-center">
                        {#if productImageUrl(form.image_url)}
                            <img src={productImageUrl(form.image_url)} alt="Product preview" class="size-full object-cover" />
                        {:else}
                            <ImagePlus class="size-5 text-muted-foreground" />
                        {/if}
                    </div>
                    <div class="flex-1">
                        <Input id="product-image" type="file" accept="image/png,image/jpeg,image/webp" onchange={uploadImage} disabled={uploadingImage} />
                        <p class="text-xs text-muted-foreground mt-1">PNG, JPG, or WEBP up to 5 MB.</p>
                    </div>
                    {#if uploadingImage}<Loader2 class="size-4 animate-spin" />{/if}
                </div>
            </div>

            {#if availableCutTypes.length > 0}
                <div class="space-y-2">
                    <Label for="cut-type">Cut Type</Label>
                    <Select.Root type="single" value={cutTypeSelection} onValueChange={onCutTypeChange}>
                        <Select.Trigger id="cut-type" class="h-10 w-full" aria-label="Cut type">
                            <span data-slot="select-value">
                                {cutTypeSelection || "Select a cut type"}
                            </span>
                        </Select.Trigger>
                        <Select.Content>
                            {#each availableCutTypes as cutType}
                                <Select.Item value={cutType}>{cutType}</Select.Item>
                            {/each}
                        </Select.Content>
                    </Select.Root>
                    {#if cutTypeSelection === "Other"}
                        <Input
                            id="custom-cut-type"
                            placeholder="Specify the cut type"
                            bind:value={form.cut_type}
                            aria-label="Custom cut type"
                        />
                    {/if}
                </div>
            {/if}

            <div class="grid grid-cols-2 gap-3">
                <div class="space-y-2">
                    <Label for="price">Price (₱)</Label>
                    <Input id="price" type="number" min="0" step="0.01"
                        placeholder="0.00" bind:value={form.price} />
                </div>
                <div class="space-y-2">
                    <Label for="unit">Unit</Label>
                    <select id="unit" bind:value={form.unit}
                        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                        aria-label="Unit of measurement">
                        <option value="kg">kg</option>
                        <option value="pcs">pcs</option>
                        <option value="g">g</option>
                        <option value="pack">pack</option>
                    </select>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
                {#if isEditing}
                    <div class="space-y-2 rounded-lg border bg-muted/30 px-3 py-2">
                        <p class="text-sm font-medium">Current Stock</p>
                        <p class="text-lg font-semibold">
                            {selectedProduct ? formatStock(selectedProduct.stock_quantity, selectedProduct.unit) : "0"}
                        </p>
                        <p class="text-xs text-muted-foreground">
                            Use Restock, Deduct, or Adjust from the product list to change stock with an audit reason.
                        </p>
                    </div>
                {:else}
                    <div class="space-y-2">
                        <Label for="stock">Opening Stock Quantity</Label>
                        <Input id="stock" type="number" min="0" step="0.001"
                            placeholder="0" bind:value={form.stock_quantity} />
                    </div>
                {/if}
                <div class="space-y-2">
                    <Label for="threshold">Low Stock Alert</Label>
                    <Input id="threshold" type="number" min="0" step="0.001"
                        placeholder="0" bind:value={form.low_stock_threshold} />
                </div>
            </div>

            {#if form.category === "retail"}
                <div class="space-y-2">
                    <Label for="sku">SKU <span class="text-muted-foreground">(optional)</span></Label>
                    <Input id="sku" placeholder="e.g. SARD-001" bind:value={form.sku} />
                </div>
            {/if}

        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => productDialogOpen = false}>Cancel</Button>
            <Button
                onclick={saveProduct}
                disabled={!form.name || !form.price || (availableCutTypes.length > 0 && !form.cut_type.trim())}
            >
                {isEditing ? "Save Changes" : "Add Product"}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<!-- Restock Dialog -->
<Dialog.Root bind:open={restockDialogOpen}>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Restock {selectedProduct?.name}</Dialog.Title>
            <Dialog.Description>
                Current stock: {selectedProduct ? formatStock(selectedProduct.stock_quantity, selectedProduct.unit) : ""}
            </Dialog.Description>
        </Dialog.Header>
        <div class="space-y-4 py-2">
            <div class="space-y-2">
                <Label for="restock-qty">Quantity to add</Label>
                <Input id="restock-qty" type="number" min="0.001" step="0.001"
                    placeholder="0" bind:value={restockQuantity} />
            </div>
            <div class="space-y-2">
                <Label>Common reasons</Label>
                <div class="flex flex-wrap gap-2">
                    {#each restockReasons as reason}
                        <Button
                            type="button"
                            variant={restockNotes === reason ? "default" : "outline"}
                            size="sm"
                            onclick={() => selectRestockReason(reason)}
                            aria-pressed={restockNotes === reason}
                        >
                            {reason}
                        </Button>
                    {/each}
                </div>
            </div>
            <div class="space-y-2">
                <Label for="restock-notes">Reason</Label>
                <Input id="restock-notes" placeholder="e.g. Delivery from supplier"
                    bind:value={restockNotes} required />
            </div>
        </div>
        <Dialog.Footer>
            <Button variant="outline" onclick={() => restockDialogOpen = false}>Cancel</Button>
            <Button onclick={restockProduct} disabled={!restockQuantity || !restockNotes.trim()}>Restock</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<!-- Adjust Stock Dialog -->
<Dialog.Root bind:open={adjustDialogOpen}>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>{adjustMode === "deduct" ? "Deduct Stock" : "Adjust Stock"} - {selectedProduct?.name}</Dialog.Title>
            <Dialog.Description>
                {adjustMode === "deduct"
                    ? "Record shrinkage, spoilage, theft, or mistakes. A reason is required for audit trail."
                    : "Set the correct stock level. A reason is required for audit trail."}
            </Dialog.Description>
        </Dialog.Header>
        <div class="space-y-4 py-2">
            <div class="space-y-2">
                <Label for="adjust-qty">{adjustMode === "deduct" ? "Quantity to deduct" : "New stock quantity"}</Label>
                <Input id="adjust-qty" type="number" min="0" step="0.001"
                    placeholder="0" bind:value={adjustQuantity} />
                {#if adjustMode === "deduct" && selectedProduct}
                    <p class="text-xs text-muted-foreground">
                        Current stock: {formatStock(selectedProduct.stock_quantity, selectedProduct.unit)}
                    </p>
                {/if}
            </div>
            <div class="space-y-2">
                <Label>Common reasons</Label>
                <div class="flex flex-wrap gap-2">
                    {#each (adjustMode === "deduct" ? stockDeductionReasons : stockAdjustmentReasons) as reason}
                        <Button
                            type="button"
                            variant={adjustReason === reason ? "default" : "outline"}
                            size="sm"
                            onclick={() => selectAdjustReason(reason)}
                            aria-pressed={adjustReason === reason}
                        >
                            {reason}
                        </Button>
                    {/each}
                </div>
            </div>
            <div class="space-y-2">
                <Label for="adjust-reason">Reason</Label>
                <textarea
                    id="adjust-reason"
                    placeholder="e.g. Spoilage, physical count correction..."
                    bind:value={adjustReason}
                    rows="2"
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                    aria-label="Adjustment reason"
                    required
                ></textarea>
            </div>
        </div>
        <Dialog.Footer>
            <Button variant="outline" onclick={() => adjustDialogOpen = false}>Cancel</Button>
            <Button onclick={adjustProduct} disabled={!adjustQuantity || !adjustReason.trim()}>
                {adjustMode === "deduct" ? "Deduct" : "Adjust"}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<!-- Archive Confirmation -->
<AlertDialog.Root bind:open={archiveDialogOpen}>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>Archive Product?</AlertDialog.Title>
            <AlertDialog.Description>
                "{selectedProduct?.name}" will be moved to the archive and removed from the POS.
                You can restore it at any time.
            </AlertDialog.Description>
        </AlertDialog.Header>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
            <AlertDialog.Action onclick={archiveProduct}>Archive</AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>

<!-- Permanent Delete Confirmation -->
<AlertDialog.Root bind:open={deleteDialogOpen}>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>Permanently Delete?</AlertDialog.Title>
            <AlertDialog.Description>
                This will permanently delete "{selectedProduct?.name}". This action cannot be undone.
                Make sure you really want to remove this product forever.
            </AlertDialog.Description>
        </AlertDialog.Header>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
            <AlertDialog.Action
                class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onclick={deleteProduct}>
                Delete Forever
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>
