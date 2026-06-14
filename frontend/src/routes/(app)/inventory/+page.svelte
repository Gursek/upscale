<script lang="ts">
    import { onMount } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import { Badge } from "$lib/components/ui/badge";
    import * as Dialog from "$lib/components/ui/dialog";
    import * as AlertDialog from "$lib/components/ui/alert-dialog";
    import {
        Plus, Pencil, Archive, RotateCcw, Trash2,
        Loader2, ArrowLeft, Package, AlertTriangle,
        Search
    } from "lucide-svelte";

    // --- State ---
    let products = $state<any[]>([]);
    let archivedProducts = $state<any[]>([]);
    let loading = $state(true);
    let error = $state("");
    let successMessage = $state("");
    let searchQuery = $state("");
    let activeTab = $state<"active" | "archived">("active");

    // --- Dialog state ---
    let productDialogOpen = $state(false);
    let archiveDialogOpen = $state(false);
    let deleteDialogOpen = $state(false);
    let selectedProduct = $state<any>(null);
    let isEditing = $state(false);

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

    // --- Form helpers ---
    function openCreateDialog() {
        isEditing = false;
        form = {
            name: "", category: "pork", cut_type: "",
            pricing_type: "per_kg", price: "", unit: "kg",
            sku: "", stock_quantity: "", low_stock_threshold: "",
            tax_classification: "exempt",
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

    function flash(msg: string, isError = false) {
        if (isError) { error = msg; setTimeout(() => error = "", 4000); }
        else { successMessage = msg; setTimeout(() => successMessage = "", 3000); }
    }

    // --- CRUD ---
    async function saveProduct() {
        try {
            const payload = {
                ...form,
                price: parseFloat(form.price),
                stock_quantity: parseFloat(form.stock_quantity || "0"),
                low_stock_threshold: parseFloat(form.low_stock_threshold || "0"),
            };
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
        beef: "Beef", pork: "Pork", chicken: "Chicken", retail: "Retail"
    };

    const categoryEmoji: Record<string, string> = {
        beef: "🥩", pork: "🥓", chicken: "🍗", retail: "📦"
    };
</script>

<div class="min-h-screen bg-muted/30">

    <!-- Header -->
    <header class="bg-background border-b px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <Button variant="ghost" size="icon" aria-label="Back to POS" onclick={() => goto("/pos")}>
            <ArrowLeft class="size-4" />
        </Button>
        <Package class="size-5 text-primary" />
        <h1 class="font-semibold text-sm flex-1">Inventory</h1>
        <Button size="sm" onclick={openCreateDialog} aria-label="Add new product">
            <Plus class="size-4 mr-1" /> Add Product
        </Button>
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
                    onclick={() => activeTab = "active"}
                    class="px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'active' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "active"}
                >
                    Active ({products.length})
                </button>
                <button
                    onclick={() => activeTab = "archived"}
                    class="px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'archived' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "archived"}
                >
                    Archived ({archivedProducts.length})
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
                                <div class="text-2xl">{categoryEmoji[product.category] ?? "📦"}</div>
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

            {:else}
                <!-- Archived -->
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
                    {#if user?.sells_retail}
                        <option value="retail">📦 Retail</option>
                    {/if}
                </select>
            </div>

            <div class="space-y-2">
                <Label for="prod-name">Product Name</Label>
                <Input id="prod-name" placeholder="e.g. Pork Belly" bind:value={form.name} />
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
                <div class="space-y-2">
                    <Label for="stock">Stock Quantity</Label>
                    <Input id="stock" type="number" min="0" step="0.001"
                        placeholder="0" bind:value={form.stock_quantity} />
                </div>
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