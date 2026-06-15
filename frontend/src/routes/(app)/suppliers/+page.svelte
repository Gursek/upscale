<script lang="ts">
    import { onMount } from "svelte";
    import { apiJson } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import * as Dialog from "$lib/components/ui/dialog";
    import * as AlertDialog from "$lib/components/ui/alert-dialog";
    import AppQuickNav from "$lib/components/AppQuickNav.svelte";
    import {
        Plus, Pencil, Archive, RotateCcw, Trash2,
        Loader2, Users, Search, Phone, Package
    } from "lucide-svelte";

    interface Supplier {
        id: number;
        name: string;
        contact_info: string | null;
        products_supplied: string | null;
        is_archived: boolean;
        archived_at: string | null;
        created_at: string;
    }

    let suppliers = $state<Supplier[]>([]);
    let archivedSuppliers = $state<Supplier[]>([]);
    let loading = $state(true);
    let error = $state("");
    let successMessage = $state("");
    let searchQuery = $state("");
    let activeTab = $state<"active" | "archived">("active");

    let supplierDialogOpen = $state(false);
    let archiveDialogOpen = $state(false);
    let deleteDialogOpen = $state(false);
    let selectedSupplier = $state<Supplier | null>(null);
    let isEditing = $state(false);

    let form = $state({
        name: "",
        contact_info: "",
        products_supplied: "",
    });

    let filteredSuppliers = $derived(
        suppliers.filter((s) =>
            s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (s.contact_info ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
            (s.products_supplied ?? "").toLowerCase().includes(searchQuery.toLowerCase())
        )
    );

    let filteredArchived = $derived(
        archivedSuppliers.filter((s) =>
            s.name.toLowerCase().includes(searchQuery.toLowerCase())
        )
    );

    onMount(async () => {
        const token = localStorage.getItem("access_token");
        if (!token) { goto("/login"); return; }
        await loadSuppliers();
    });

    async function loadSuppliers() {
        loading = true;
        try {
            [suppliers, archivedSuppliers] = await Promise.all([
                apiJson<Supplier[]>("/suppliers/"),
                apiJson<Supplier[]>("/suppliers/archived"),
            ]);
        } catch {
            error = "Failed to load suppliers";
        } finally {
            loading = false;
        }
    }

    function openCreateDialog() {
        isEditing = false;
        form = { name: "", contact_info: "", products_supplied: "" };
        supplierDialogOpen = true;
    }

    function openEditDialog(supplier: Supplier) {
        isEditing = true;
        selectedSupplier = supplier;
        form = {
            name: supplier.name,
            contact_info: supplier.contact_info ?? "",
            products_supplied: supplier.products_supplied ?? "",
        };
        supplierDialogOpen = true;
    }

    function flash(msg: string, isError = false) {
        if (isError) { error = msg; setTimeout(() => error = "", 4000); }
        else { successMessage = msg; setTimeout(() => successMessage = "", 3000); }
    }

    async function saveSupplier() {
        try {
            const payload = {
                name: form.name.trim(),
                contact_info: form.contact_info.trim() || null,
                products_supplied: form.products_supplied.trim() || null,
            };
            if (isEditing && selectedSupplier) {
                await apiJson(`/suppliers/${selectedSupplier.id}`, {
                    method: "PUT",
                    body: JSON.stringify(payload),
                });
                flash("Supplier updated");
            } else {
                await apiJson("/suppliers/", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });
                flash("Supplier created");
            }
            supplierDialogOpen = false;
            await loadSuppliers();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    async function archiveSupplier() {
        if (!selectedSupplier) return;
        try {
            await apiJson(`/suppliers/${selectedSupplier.id}/archive`, { method: "POST" });
            flash("Supplier archived");
            archiveDialogOpen = false;
            await loadSuppliers();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    async function restoreSupplier(supplier: Supplier) {
        try {
            await apiJson(`/suppliers/${supplier.id}/restore`, { method: "POST" });
            flash("Supplier restored");
            await loadSuppliers();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    async function deleteSupplier() {
        if (!selectedSupplier) return;
        try {
            await apiJson(`/suppliers/${selectedSupplier.id}`, { method: "DELETE" });
            flash("Supplier permanently deleted");
            deleteDialogOpen = false;
            await loadSuppliers();
        } catch (e: any) {
            flash(e.message, true);
        }
    }

</script>

<div class="min-h-screen bg-muted/30">

    <header class="bg-background border-b px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <Users class="size-5 text-primary" />
        <h1 class="font-semibold text-sm flex-1">Suppliers</h1>
        <Button size="sm" onclick={openCreateDialog} aria-label="Add new supplier">
            <Plus class="size-4 mr-1" /> Add Supplier
        </Button>
        <AppQuickNav current="/suppliers" />
    </header>

    {#if error}
        <div class="bg-destructive/10 text-destructive text-sm px-4 py-2 text-center" role="alert">{error}</div>
    {/if}
    {#if successMessage}
        <div class="bg-green-500/10 text-green-700 text-sm px-4 py-2 text-center" role="status">{successMessage}</div>
    {/if}

    <div class="max-w-4xl mx-auto p-4 space-y-4">

        <div class="flex flex-col sm:flex-row gap-3">
            <div class="relative flex-1">
                <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                    placeholder="Search suppliers..."
                    bind:value={searchQuery}
                    class="pl-9"
                    aria-label="Search suppliers"
                />
            </div>
            <div class="flex rounded-md border overflow-hidden text-sm">
                <button
                    onclick={() => activeTab = "active"}
                    class="px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'active' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "active"}
                >
                    Active ({suppliers.length})
                </button>
                <button
                    onclick={() => activeTab = "archived"}
                    class="px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                        {activeTab === 'archived' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                    aria-pressed={activeTab === "archived"}
                >
                    Archived ({archivedSuppliers.length})
                </button>
            </div>
        </div>

        {#if loading}
            <div class="flex items-center justify-center h-40">
                <Loader2 class="size-6 animate-spin text-muted-foreground" />
            </div>
        {:else}
            {#if activeTab === "active"}
                {#if filteredSuppliers.length === 0}
                    <div class="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                        <Users class="size-8" />
                        <p class="text-sm">No suppliers yet</p>
                        <Button variant="outline" size="sm" onclick={openCreateDialog}>Add your first supplier</Button>
                    </div>
                {:else}
                    <ul class="space-y-2" aria-label="Active suppliers">
                        {#each filteredSuppliers as supplier (supplier.id)}
                        <li class="bg-background rounded-xl border overflow-hidden">
                        <button
                            class="w-full p-4 flex items-center gap-4 hover:bg-muted/50 transition-colors text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            onclick={() => openEditDialog(supplier)}
                            aria-label="Edit {supplier.name}"
                            >
                                <div class="bg-primary/10 rounded-full p-2 shrink-0">
                                    <Users class="size-5 text-primary" />
                                </div>
                                <div class="flex-1 min-w-0">
                                    <p class="font-medium text-sm">{supplier.name}</p>
                                    <div class="flex flex-col gap-0.5 mt-1 text-xs text-muted-foreground">
                                        {#if supplier.contact_info}
                                            <span class="flex items-center gap-1">
                                                <Phone class="size-3 shrink-0" />
                                                {supplier.contact_info}
                                            </span>
                                        {/if}
                                        {#if supplier.products_supplied}
                                            <span class="flex items-start gap-1">
                                                <Package class="size-3 shrink-0 mt-0.5" />
                                                <span class="line-clamp-2">{supplier.products_supplied}</span>
                                            </span>
                                        {/if}
                                    </div>
                                </div>
                                <div class="flex items-center gap-1 shrink-0">
                                    <Button variant="ghost" size="icon"
                                        aria-label="Edit {supplier.name}"
                                        onclick={(e) => { e.stopPropagation(); openEditDialog(supplier); }}>
                                        <Pencil class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon"
                                        aria-label="Archive {supplier.name}"
                                        onclick={(e) => { e.stopPropagation(); selectedSupplier = supplier; archiveDialogOpen = true; }}>
                                        <Archive class="size-4" />
                                    </Button>
                                </div>
                        </button>
                         </li>
                        {/each}
                    </ul>
                {/if}

            {:else}
                {#if filteredArchived.length === 0}
                    <div class="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                        <Archive class="size-8" />
                        <p class="text-sm">No archived suppliers</p>
                    </div>
                {:else}
                    <ul class="space-y-2" aria-label="Archived suppliers">
                        {#each filteredArchived as supplier (supplier.id)}
                            <li class="bg-background rounded-xl border border-dashed p-4 flex items-center gap-4 opacity-75">
                                <div class="bg-muted rounded-full p-2 shrink-0">
                                    <Users class="size-5 text-muted-foreground" />
                                </div>
                                <div class="flex-1 min-w-0">
                                    <p class="font-medium text-sm line-through text-muted-foreground">{supplier.name}</p>
                                    <p class="text-xs text-muted-foreground mt-0.5">
                                        Archived {supplier.archived_at ? new Date(supplier.archived_at).toLocaleDateString() : ""}
                                    </p>
                                </div>
                                <div class="flex items-center gap-1 shrink-0">
                                    <Button variant="ghost" size="icon"
                                        aria-label="Restore {supplier.name}"
                                        onclick={() => restoreSupplier(supplier)}>
                                        <RotateCcw class="size-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon"
                                        aria-label="Permanently delete {supplier.name}"
                                        onclick={() => { selectedSupplier = supplier; deleteDialogOpen = true; }}>
                                        <Trash2 class="size-4 text-destructive" />
                                    </Button>
                                </div>
                            </li>
                        {/each}
                    </ul>
                {/if}
            {/if}
        {/if}
    </div>
</div>

<Dialog.Root bind:open={supplierDialogOpen}>
    <Dialog.Content class="max-w-md max-h-[90vh] overflow-y-auto">
        <Dialog.Header>
            <Dialog.Title>{isEditing ? "Edit Supplier" : "Add Supplier"}</Dialog.Title>
            <Dialog.Description>
                {isEditing ? "Update supplier details." : "Add a new supplier to your records."}
            </Dialog.Description>
        </Dialog.Header>

        <div class="space-y-4 py-2">
            <div class="space-y-2">
                <Label for="supplier-name">Supplier Name</Label>
                <Input id="supplier-name" placeholder="e.g. Bataan Livestock" bind:value={form.name} />
            </div>

            <div class="space-y-2">
                <Label for="contact-info">Contact Info <span class="text-muted-foreground">(optional)</span></Label>
                <textarea
                    id="contact-info"
                    placeholder="Phone, email, address..."
                    bind:value={form.contact_info}
                    rows="2"
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                    aria-label="Contact information"
                ></textarea>
            </div>

            <div class="space-y-2">
                <Label for="products-supplied">Products Supplied <span class="text-muted-foreground">(optional)</span></Label>
                <textarea
                    id="products-supplied"
                    placeholder="e.g. Pork belly, ribs, chicken cuts..."
                    bind:value={form.products_supplied}
                    rows="3"
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                    aria-label="Products supplied"
                ></textarea>
            </div>
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => supplierDialogOpen = false}>Cancel</Button>
            <Button onclick={saveSupplier} disabled={!form.name.trim()}>
                {isEditing ? "Save Changes" : "Add Supplier"}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<AlertDialog.Root bind:open={archiveDialogOpen}>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>Archive Supplier?</AlertDialog.Title>
            <AlertDialog.Description>
                "{selectedSupplier?.name}" will be moved to the archive.
                You can restore it at any time.
            </AlertDialog.Description>
        </AlertDialog.Header>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
            <AlertDialog.Action onclick={archiveSupplier}>Archive</AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>

<AlertDialog.Root bind:open={deleteDialogOpen}>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>Permanently Delete?</AlertDialog.Title>
            <AlertDialog.Description>
                This will permanently delete "{selectedSupplier?.name}". This action cannot be undone.
            </AlertDialog.Description>
        </AlertDialog.Header>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
            <AlertDialog.Action
                class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onclick={deleteSupplier}>
                Delete Forever
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>
