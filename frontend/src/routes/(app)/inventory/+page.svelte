<script lang="ts">
    import { onMount } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { apiFetch, apiJson, API_BASE } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import { Badge } from "$lib/components/ui/badge";
    import * as Dialog from "$lib/components/ui/dialog";
    import * as AlertDialog from "$lib/components/ui/alert-dialog";
    import AppQuickNav from "$lib/components/AppQuickNav.svelte";
    import {
        Plus, Pencil, Archive, RotateCcw, Trash2,
        Loader2, Package, AlertTriangle,
        Search, PackagePlus, PackageMinus, SlidersHorizontal, History, ImagePlus
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

    let filteredProducts = $derived(
        products.filter((p) =>
            p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            p.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (p.cut_type ?? "").toLowerCase().includes(searchQuery.toLowerCase())
        )
    );

    let filteredArchived = $derived(
        archivedProducts.filter((p) =>
            p.name.toLowerCase().includes(searchQuery.toLowerCase())
        )
    );

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
        productDialogOpen = true;
    }

    // Auto-set unit and tax_classification when category changes
    function onCategoryChange() {
        if (form.category === "retail") {
            form.pricing_type = "fixed";
            form.unit = "pcs";
            form.tax_classification = "standard";
            form.cut_type = "";
        } else {
            form.pricing_type = "per_kg";
            form.unit = "kg";
            form.tax_classification = "exempt";
        }
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

    <div class="max-w-4xl mx-auto p-4 space-y-4">

        <!-- Search + Tabs -->
        <div class="flex flex-col sm:flex-row gap-3">
            <div class="relative flex-1">
                <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                    placeholder="Search products..."
                    bind:value={searchQuery}
                    class="pl-9"
                    aria-label="Search products"
                />
            </div>
            <div class="flex rounded-md border overflow-hidden text-sm">
                <button
                    onclick={() => switchTab("active")}
                    class="px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'active' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "active"}
                >
                    Active ({products.length})
                </button>
                <button
                    onclick={() => switchTab("archived")}
                    class="px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'archived' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "archived"}
                >
                    Archived ({archivedProducts.length})
                </button>
                <button
                    onclick={() => switchTab("history")}
                    class="px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'history' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "history"}
                >
                    History
                </button>
            </div>
        </div>

        <!-- Product list -->
        {#if loading}
            <div class="flex items-center justify-center h-40">
                <Loader2 class="size-6 animate-spin text-muted-foreground" />
            </div>
        {:else}
            {#if activeTab === "active"}
                {#if filteredProducts.length === 0}
                    <div class="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                        <Package class="size-8" />
                        <p class="text-sm">No products yet</p>
                        <Button variant="outline" size="sm" onclick={openCreateDialog}>Add your first product</Button>
                    </div>
                {:else}
                    <div class="space-y-2" role="list" aria-label="Active products">
                        {#each filteredProducts as product (product.id)}
                            <div role="listitem"
                                class="bg-background rounded-xl border p-4 flex items-center gap-4">
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
                                        <Badge variant="outline" class="text-xs capitalize">
                                            {categoryLabels[product.category] ?? product.category}
                                        </Badge>
                                        {#if product.stock_quantity <= product.low_stock_threshold && product.low_stock_threshold > 0}
                                            <Badge variant="destructive" class="text-xs gap-1">
                                                <AlertTriangle class="size-3" /> Low stock
                                            </Badge>
                                        {/if}
                                    </div>
                                    <div class="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                                        <span>₱{Number(product.price).toFixed(2)}/{product.unit}</span>
                                        <span>Stock: {Number(product.stock_quantity).toFixed(product.unit === 'kg' ? 3 : 0)} {product.unit}</span>
                                        {#if product.sku}
                                            <span>SKU: {product.sku}</span>
                                        {/if}
                                    </div>
                                </div>
                                <div class="flex items-center gap-1 shrink-0">
                                    <Button variant="ghost" size="icon"
                                        aria-label="Restock {product.name}"
                                        onclick={() => openRestockDialog(product)}>
                                        <PackagePlus class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon"
                                        aria-label="Deduct stock for {product.name}"
                                        onclick={() => openAdjustDialog(product, "deduct")}>
                                        <PackageMinus class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon"
                                        aria-label="Adjust stock for {product.name}"
                                        onclick={() => openAdjustDialog(product)}>
                                        <SlidersHorizontal class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon"
                                        aria-label="Edit {product.name}"
                                        onclick={() => openEditDialog(product)}>
                                        <Pencil class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon"
                                        aria-label="Archive {product.name}"
                                        onclick={() => { selectedProduct = product; archiveDialogOpen = true; }}>
                                        <Archive class="size-4" />
                                    </Button>
                                </div>
                            </div>
                        {/each}
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

            {#if form.category !== "retail"}
                <div class="space-y-2">
                    <Label for="cut-type">Cut Type <span class="text-muted-foreground">(optional)</span></Label>
                    <Input id="cut-type" placeholder="e.g. Belly, Ribs, Loin" bind:value={form.cut_type} />
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
            <Button onclick={saveProduct} disabled={!form.name || !form.price}>
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
