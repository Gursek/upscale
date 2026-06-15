<script lang="ts">
    import { onMount } from "svelte";
    import { apiFetch, apiJson } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Input } from "$lib/components/ui/input";
    import { Separator } from "$lib/components/ui/separator";
    import * as Dialog from "$lib/components/ui/dialog";
    import * as AlertDialog from "$lib/components/ui/alert-dialog";
    import AppQuickNav from "$lib/components/AppQuickNav.svelte";
    import {
        ReceiptText, Search, Eye,
        Ban, Loader2, ChevronDown, ChevronUp,
        Download, FileText, LockKeyhole, Printer
    } from "lucide-svelte";

    // --- State ---
    let invoices = $state<any[]>([]);
    let loading = $state(true);
    let error = $state("");
    let successMessage = $state("");
    let searchQuery = $state("");
    let period = $state<"all" | "6h" | "24h" | "7d" | "30d" | "12m" | "date">("all");
    let selectedDate = $state(new Date().toLocaleDateString("en-CA"));

    // --- Dialog state ---
    let viewDialogOpen = $state(false);
    let voidDialogOpen = $state(false);
    let selectedInvoice = $state<any>(null);
    let voidReason = $state("");
    let voidLoading = $state(false);
    let zReadings = $state<any[]>([]);
    let zDialogOpen = $state(false);
    let zPassword = $state("");
    let zLoading = $state(false);

    // --- Derived ---
    let filteredInvoices = $derived(
        invoices.filter((inv) =>
            inv.invoice_number.includes(searchQuery) ||
            inv.status.includes(searchQuery.toLowerCase()) ||
            inv.invoice_type.includes(searchQuery.toLowerCase())
        )
    );

    let totalSales = $derived(
        invoices
            .filter((inv) => inv.status === "active")
            .reduce((sum, inv) => sum + inv.total_amount, 0)
    );

    let totalTransactions = $derived(
        invoices.filter((inv) => inv.status === "active").length
    );
    let voidCount = $derived(invoices.filter((inv) => inv.status === "voided").length);

    // --- Load ---
    onMount(async () => {
        const token = localStorage.getItem("access_token");
        if (!token) { goto("/login"); return; }
        await loadInvoices();
    });

    async function loadInvoices() {
        loading = true;
        try {
            let invoicePath = "/invoices/";
            if (period === "date") {
                invoicePath += `?date=${selectedDate}`;
            } else if (period !== "all") {
                const durations: Record<string, number> = {
                    "6h": 6 * 60 * 60 * 1000,
                    "24h": 24 * 60 * 60 * 1000,
                    "7d": 7 * 24 * 60 * 60 * 1000,
                    "30d": 30 * 24 * 60 * 60 * 1000,
                    "12m": 365 * 24 * 60 * 60 * 1000,
                };
                invoicePath += `?start=${encodeURIComponent(new Date(Date.now() - durations[period]).toISOString())}`;
            }
            [invoices, zReadings] = await Promise.all([
                apiJson<any[]>(invoicePath),
                apiJson<any[]>("/readings/z"),
            ]);
        } catch {
            error = "Failed to load invoices";
        } finally {
            loading = false;
        }
    }

    function flash(msg: string, isError = false) {
        if (isError) { error = msg; setTimeout(() => error = "", 4000); }
        else { successMessage = msg; setTimeout(() => successMessage = "", 3000); }
    }

    function openViewDialog(invoice: any) {
        selectedInvoice = invoice;
        viewDialogOpen = true;
    }

    function openVoidDialog(invoice: any) {
        selectedInvoice = invoice;
        voidReason = "";
        voidDialogOpen = true;
    }

    async function voidInvoice() {
        voidLoading = true;
        try {
            await apiJson(`/invoices/${selectedInvoice.id}/void`, {
                method: "POST",
                body: JSON.stringify({ reason: voidReason }),
            });
            flash(`Invoice #${selectedInvoice.invoice_number} voided`);
            voidDialogOpen = false;
            viewDialogOpen = false;
            await loadInvoices();
        } catch (e: any) {
            flash(e.message, true);
        } finally {
            voidLoading = false;
        }
    }

    async function selectPeriod(value: typeof period) {
        period = value;
        await loadInvoices();
    }

    async function generateZReading() {
        if (!zPassword) return;
        zLoading = true;
        try {
            await apiJson("/auth/verify-password", {
                method: "POST",
                body: JSON.stringify({ password: zPassword }),
            });
            const reading = await apiJson<any>("/readings/z", {
                method: "POST",
                body: JSON.stringify({ password: zPassword }),
            });
            flash(`Z-Reading #${reading.z_counter} generated`);
            zDialogOpen = false;
            zPassword = "";
            await loadInvoices();
        } catch (e: any) {
            flash(e.message, true);
        } finally {
            zLoading = false;
        }
    }

    async function downloadFile(path: string, fallbackName: string) {
        try {
            const response = await apiFetch(path);
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || "Export failed");
            }
            const blob = await response.blob();
            const disposition = response.headers.get("Content-Disposition") ?? "";
            const match = disposition.match(/filename="?([^"]+)"?/);
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = match?.[1] ?? fallbackName;
            anchor.click();
            URL.revokeObjectURL(url);
        } catch (e: any) {
            flash(e.message, true);
        }
    }

    async function openInvoiceDocument(invoice: any, reprint = false) {
        const popup = window.open("", "_blank");
        try {
            const response = await apiFetch(
                `/invoices/${invoice.id}/${reprint ? "reprint" : "print"}`,
                { method: reprint ? "POST" : "GET" }
            );
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || "Unable to open invoice");
            }
            const html = await response.text();
            if (!popup) throw new Error("Allow popups to print invoices");
            popup.document.open();
            popup.document.write(html);
            popup.document.close();
            if (reprint) {
                flash(`Invoice #${invoice.invoice_number} reprint recorded`);
                await loadInvoices();
            }
        } catch (e: any) {
            popup?.close();
            flash(e.message, true);
        }
    }

    function formatDate(iso: string) {
        return new Date(iso).toLocaleString("en-PH", {
            timeZone: "Asia/Manila",
            year: "numeric", month: "short", day: "numeric",
            hour: "2-digit", minute: "2-digit",
        });
    }
</script>

<div class="min-h-screen bg-muted/30">

    <!-- Header -->
    <header class="bg-background border-b px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <ReceiptText class="size-5 text-primary" />
        <h1 class="font-semibold text-sm flex-1">Sales History</h1>
        <AppQuickNav current="/invoices" />
    </header>

    <!-- Alerts -->
    {#if error}
        <div class="bg-destructive/10 text-destructive text-sm px-4 py-2 text-center" role="alert">{error}</div>
    {/if}
    {#if successMessage}
        <div class="bg-green-500/10 text-green-700 text-sm px-4 py-2 text-center" role="status">{successMessage}</div>
    {/if}

    <div class="max-w-4xl mx-auto p-4 space-y-4">

        <!-- Summary cards -->
        <div class="grid grid-cols-3 gap-3">
            <div class="bg-background rounded-xl border p-4">
                <p class="text-xs text-muted-foreground">Total Sales</p>
                <p class="text-2xl font-semibold mt-1">₱{totalSales.toFixed(2)}</p>
            </div>
            <div class="bg-background rounded-xl border p-4">
                <p class="text-xs text-muted-foreground">Transactions</p>
                <p class="text-2xl font-semibold mt-1">{totalTransactions}</p>
            </div>
            <div class="bg-background rounded-xl border p-4">
                <p class="text-xs text-muted-foreground">Voids</p>
                <p class="text-2xl font-semibold mt-1">{voidCount}</p>
            </div>
        </div>

        <section class="bg-background rounded-xl border p-4 space-y-3" aria-label="Sales period">
            <div class="flex flex-wrap gap-2">
                {#each [
                    ["all", "All"],
                    ["6h", "Last 6 hours"],
                    ["24h", "Last 24 hours"],
                    ["7d", "Last 7 days"],
                    ["30d", "Last 30 days"],
                    ["12m", "Last 12 months"],
                    ["date", "Specific day"],
                ] as option}
                    <Button
                        variant={period === option[0] ? "default" : "outline"}
                        size="sm"
                        onclick={() => selectPeriod(option[0] as typeof period)}
                        aria-pressed={period === option[0]}
                    >{option[1]}</Button>
                {/each}
            </div>
            {#if period === "date"}
                <div class="flex flex-wrap items-end gap-2">
                    <div class="space-y-1">
                        <label for="invoice-date" class="text-xs font-medium">Business date</label>
                        <Input id="invoice-date" type="date" bind:value={selectedDate} onchange={loadInvoices} />
                    </div>
                    <Button variant="outline" size="sm" onclick={() => downloadFile(`/invoices/export?date=${selectedDate}`, `invoices-${selectedDate}.xlsx`)}>
                        <Download class="size-4 mr-1" />
                        Export Invoices and Voids
                    </Button>
                    <Button variant="outline" size="sm" onclick={() => downloadFile(`/readings/ejournal/export?date=${selectedDate}`, `ejournal-${selectedDate}.txt`)}>
                        <Download class="size-4 mr-1" />
                        Export E-Journal
                    </Button>
                    <Button variant="outline" size="sm" onclick={() => downloadFile(`/readings/statutory-discounts/export?date=${selectedDate}`, `statutory-discount-books-${selectedDate}.xlsx`)}>
                        <Download class="size-4 mr-1" />
                        Export Discount Books
                    </Button>
                    <Button variant="outline" size="sm" onclick={() => downloadFile(`/compliance/audit-log/export?date=${selectedDate}`, `activity-log-${selectedDate}.xlsx`)}>
                        <Download class="size-4 mr-1" />
                        Export Activity Log
                    </Button>
                </div>
            {/if}
            <div class="relative">
                <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                    placeholder="Search by invoice number, status, or type..."
                    bind:value={searchQuery}
                    class="pl-9"
                    aria-label="Search invoices"
                />
            </div>
        </section>

        <!-- Invoice list -->
        {#if loading}
            <div class="flex items-center justify-center h-40">
                <Loader2 class="size-6 animate-spin text-muted-foreground" />
            </div>
        {:else if filteredInvoices.length === 0}
            <div class="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                <FileText class="size-8" />
                <p class="text-sm">No invoices yet</p>
            </div>
        {:else}
            <ul class="space-y-2" aria-label="Invoice list">
                {#each filteredInvoices as invoice (invoice.id)}
                    <li
                        class="bg-background rounded-xl border p-4 flex items-center gap-4
                            {invoice.status === 'voided' ? 'opacity-60' : ''}">
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 flex-wrap">
                                <p class="font-mono font-semibold text-sm">#{invoice.invoice_number}</p>
                                <Badge
                                    variant={invoice.status === "active" ? "default" : "destructive"}
                                    class="text-xs capitalize">
                                    {invoice.status}
                                </Badge>
                                <Badge variant="outline" class="text-xs capitalize">
                                    {invoice.invoice_type}
                                </Badge>
                            </div>
                            <div class="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                                <span>{formatDate(invoice.date_time)}</span>
                                <span>{invoice.items.length} item{invoice.items.length !== 1 ? "s" : ""}</span>
                            </div>
                            {#if invoice.status === "voided" && invoice.voided_reason}
                                <p class="text-xs text-muted-foreground mt-1 italic">
                                    Void reason: {invoice.voided_reason}
                                </p>
                            {/if}
                        </div>
                        <div class="text-right shrink-0">
                            <p class="font-semibold text-sm">₱{Number(invoice.total_amount).toFixed(2)}</p>
                            <div class="flex items-center gap-1 mt-1 justify-end">
                                <Button variant="ghost" size="icon"
                                    aria-label="View invoice #{invoice.invoice_number}"
                                    onclick={() => openViewDialog(invoice)}>
                                    <Eye class="size-4" />
                                </Button>
                                {#if invoice.status === "active"}
                                    <Button variant="ghost" size="icon"
                                        aria-label="Void invoice #{invoice.invoice_number}"
                                        onclick={() => openVoidDialog(invoice)}>
                                        <Ban class="size-4 text-destructive" />
                                    </Button>
                                {/if}
                            </div>
                        </div>
                    </li>
                {/each}
            </ul>
        {/if}

        <!-- X/Z Reading section -->
        <div class="bg-background rounded-xl border p-4 space-y-3">
            <h2 class="font-semibold text-sm">BIR Reports</h2>
            <p class="text-xs text-muted-foreground">
                Generate end-of-shift (X-Reading) or end-of-day (Z-Reading) reports as required by BIR RMO 24-2023.
            </p>
            <div class="flex gap-2 flex-wrap">
                <Button variant="outline" size="sm" onclick={async () => {
                    try {
                        const r = await apiJson<any>("/readings/x", { method: "POST", body: JSON.stringify({}) });
                        flash(`X-Reading generated — ₱${Number(r.total_sales).toFixed(2)} total sales, ${r.transaction_count} transactions`);
                    } catch (e: any) { flash(e.message, true); }
                }}>
                    X-Reading (End of Shift)
                </Button>
                <Button variant="outline" size="sm" onclick={() => { zPassword = ""; zDialogOpen = true; }}>
                    <LockKeyhole class="size-4 mr-1" />
                    Z-Reading (End of Day)
                </Button>
                <Button variant="outline" size="sm" onclick={() => downloadFile(
                    `/readings/ejournal/export?date=${new Date().toISOString().slice(0, 10)}`,
                    `ejournal-${new Date().toISOString().slice(0, 10)}.txt`
                )}>
                    <Download class="size-4 mr-1" />
                    Export Today's E-Journal
                </Button>
            </div>
            {#if zReadings.length > 0}
                <ul class="divide-y border rounded-lg" aria-label="Z-Reading entries">
                    {#each zReadings as reading}
                        <li class="p-3 flex items-center gap-3">
                            <div class="flex-1">
                                <p class="text-sm font-medium">Z-Reading #{reading.z_counter}</p>
                                <p class="text-xs text-muted-foreground">
                                    {reading.business_date} - PHP {Number(reading.total_sales).toFixed(2)}
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onclick={() => downloadFile(`/readings/z/${reading.id}/export`, `z-reading-${reading.business_date}.xlsx`)}
                            >
                                <Download class="size-4 mr-1" />
                                Export Excel
                            </Button>
                        </li>
                    {/each}
                </ul>
            {/if}
        </div>

    </div>
</div>

<!-- View Invoice Dialog -->
<Dialog.Root bind:open={viewDialogOpen}>
    <Dialog.Content class="max-w-md max-h-[90vh] overflow-y-auto">
        <Dialog.Header>
            <Dialog.Title class="flex items-center gap-2">
                <span class="font-mono">Invoice #{selectedInvoice?.invoice_number}</span>
                {#if selectedInvoice}
                    <Badge
                        variant={selectedInvoice.status === "active" ? "default" : "destructive"}
                        class="text-xs capitalize">
                        {selectedInvoice.status}
                    </Badge>
                {/if}
            </Dialog.Title>
            {#if selectedInvoice}
                <Dialog.Description>{formatDate(selectedInvoice.date_time)}</Dialog.Description>
            {/if}
        </Dialog.Header>

        {#if selectedInvoice}
            <div class="space-y-4 py-2">

                <!-- Line items -->
                <div class="space-y-2">
                    <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Items</p>
                    {#each selectedInvoice.items as item}
                        <div class="flex justify-between text-sm">
                            <div>
                                <p class="font-medium">{item.description}</p>
                                <p class="text-xs text-muted-foreground">
                                    {item.quantity} × ₱{Number(item.unit_cost).toFixed(2)}
                                    <Badge variant="outline" class="text-xs ml-1 capitalize">
                                        {item.tax_line_classification.replace("_", " ")}
                                    </Badge>
                                </p>
                            </div>
                            <span class="font-medium shrink-0">₱{Number(item.line_total).toFixed(2)}</span>
                        </div>
                    {/each}
                </div>

                <Separator />

                <!-- Tax breakdown -->
                <div class="space-y-1 text-sm">
                    <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Breakdown</p>
                    {#if selectedInvoice.vat_exempt_sales > 0}
                        <div class="flex justify-between text-muted-foreground">
                            <span>VAT-Exempt Sales</span>
                            <span>₱{Number(selectedInvoice.vat_exempt_sales).toFixed(2)}</span>
                        </div>
                    {/if}
                    {#if selectedInvoice.vatable_sales > 0}
                        <div class="flex justify-between text-muted-foreground">
                            <span>VATable Sales</span>
                            <span>₱{Number(selectedInvoice.vatable_sales).toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between text-muted-foreground">
                            <span>VAT (12%)</span>
                            <span>₱{Number(selectedInvoice.vat_amount).toFixed(2)}</span>
                        </div>
                    {/if}
                    {#if selectedInvoice.sspt_sales > 0}
                        <div class="flex justify-between text-muted-foreground">
                            <span>SSPT Sales (3%)</span>
                            <span>₱{Number(selectedInvoice.sspt_sales).toFixed(2)}</span>
                        </div>
                    {/if}
                    {#if selectedInvoice.discount_amount > 0}
                        <div class="flex justify-between text-muted-foreground">
                            <span>Discount ({selectedInvoice.discount_type?.toUpperCase()})</span>
                            <span>-₱{Number(selectedInvoice.discount_amount).toFixed(2)}</span>
                        </div>
                    {/if}
                </div>

                <Separator />

                <div class="flex justify-between font-semibold">
                    <span>Total</span>
                    <span>₱{Number(selectedInvoice.total_amount).toFixed(2)}</span>
                </div>

                {#if selectedInvoice.status === "voided"}
                    <div class="bg-destructive/10 text-destructive text-xs rounded-md px-3 py-2">
                        Voided {selectedInvoice.voided_at ? formatDate(selectedInvoice.voided_at) : ""}
                        {#if selectedInvoice.voided_reason}— {selectedInvoice.voided_reason}{/if}
                    </div>
                {/if}

            </div>

            <Dialog.Footer>
                <Button variant="outline" size="sm" onclick={() => openInvoiceDocument(selectedInvoice)}>
                    <Printer class="size-4 mr-1" /> Print
                </Button>
                <Button variant="outline" size="sm" onclick={() => openInvoiceDocument(selectedInvoice, true)}>
                    <Printer class="size-4 mr-1" /> Reprint
                </Button>
                {#if selectedInvoice.status === "active"}
                    <Button variant="destructive" size="sm"
                        onclick={() => { viewDialogOpen = false; openVoidDialog(selectedInvoice); }}>
                        <Ban class="size-4 mr-1" /> Void Invoice
                    </Button>
                {/if}
                <Button variant="outline" onclick={() => viewDialogOpen = false}>Close</Button>
            </Dialog.Footer>
        {/if}
    </Dialog.Content>
</Dialog.Root>

<!-- Void Confirmation -->
<AlertDialog.Root bind:open={voidDialogOpen}>
    <AlertDialog.Content>
        <AlertDialog.Header>
            <AlertDialog.Title>Void Invoice #{selectedInvoice?.invoice_number}?</AlertDialog.Title>
            <AlertDialog.Description>
                This will void the invoice and restore stock for all items.
                Per BIR requirements, voided invoices are retained in records.
            </AlertDialog.Description>
        </AlertDialog.Header>
        <div class="px-6 pb-2">
            <Input
                placeholder="Reason for voiding"
                bind:value={voidReason}
                aria-label="Void reason"
            />
        </div>
        <AlertDialog.Footer>
            <AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
            <AlertDialog.Action
                class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onclick={voidInvoice}
                disabled={voidLoading || !voidReason.trim()}
                aria-busy={voidLoading}>
                {#if voidLoading}
                    <Loader2 class="size-4 animate-spin mr-1" />
                {/if}
                Void Invoice
            </AlertDialog.Action>
        </AlertDialog.Footer>
    </AlertDialog.Content>
</AlertDialog.Root>

<Dialog.Root bind:open={zDialogOpen}>
    <Dialog.Content>
        <Dialog.Header>
            <Dialog.Title>Confirm Z-Reading</Dialog.Title>
            <Dialog.Description>
                Enter your password to close today's business date. New invoices will be blocked after generation.
            </Dialog.Description>
        </Dialog.Header>
        <Input
            type="password"
            bind:value={zPassword}
            placeholder="Current password"
            autocomplete="current-password"
            aria-label="Password confirmation"
            onkeydown={(event) => { if (event.key === "Enter") generateZReading(); }}
        />
        <Dialog.Footer>
            <Button variant="outline" onclick={() => zDialogOpen = false}>Cancel</Button>
            <Button onclick={generateZReading} disabled={!zPassword || zLoading} aria-busy={zLoading}>
                {#if zLoading}<Loader2 class="size-4 animate-spin mr-1" />{/if}
                Generate Z-Reading
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
