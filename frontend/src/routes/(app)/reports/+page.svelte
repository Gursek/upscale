<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import { apiFetch, apiJson } from "$lib/api";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Input } from "$lib/components/ui/input";
    import * as Dialog from "$lib/components/ui/dialog";
    import * as Tabs from "$lib/components/ui/tabs";
    import * as Table from "$lib/components/ui/table";
    import AppQuickNav from "$lib/components/AppQuickNav.svelte";
    import {
        ArrowLeft, BookOpenText, ChevronDown, ChevronUp, Download,
        FileBarChart, FileClock, Loader2, LockKeyhole, Play, ReceiptText
    } from "lucide-svelte";

    let activeTab = $state("daily");
    let invoices = $state<any[]>([]);
    let zReadings = $state<any[]>([]);
    let xReadings = $state<any[]>([]);
    let loading = $state(true);
    let error = $state("");
    let successMessage = $state("");
    let selectedDate = $state(phDateString());
    let journalStartDate = $state(phDateString());
    let journalEndDate = $state(phDateString());
    let expandedZ = $state<number | null>(null);
    let expandedX = $state<number | null>(null);
    let zDialogOpen = $state(false);
    let password = $state("");
    let passwordError = $state("");
    let zLoading = $state(false);
    let xLoading = $state(false);

    let dailyInvoices = $derived(
        invoices.filter((invoice) => phDateString(new Date(invoice.date_time)) === selectedDate)
    );
    let dailySales = $derived(
        dailyInvoices
            .filter((invoice) => invoice.status === "active")
            .reduce((sum, invoice) => sum + Number(invoice.total_amount), 0)
    );
    let dailyTransactions = $derived(dailyInvoices.filter((invoice) => invoice.status === "active").length);
    let dailyVoids = $derived(dailyInvoices.filter((invoice) => invoice.status === "voided").length);
    let selectedDateZ = $derived(zReadings.find((reading) => reading.business_date === selectedDate));

    onMount(loadReports);

    function phDateString(value = new Date()) {
        return new Intl.DateTimeFormat("en-CA", {
            timeZone: "Asia/Manila",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
        }).format(value);
    }

    function formatDateTime(value: string) {
        return new Intl.DateTimeFormat("en-PH", {
            timeZone: "Asia/Manila",
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        }).format(new Date(value));
    }

    function money(value: number) {
        return new Intl.NumberFormat("en-PH", {
            style: "currency",
            currency: "PHP",
        }).format(Number(value || 0));
    }

    async function loadReports() {
        loading = true;
        try {
            [invoices, zReadings, xReadings] = await Promise.all([
                apiJson<any[]>("/invoices/"),
                apiJson<any[]>("/readings/z"),
                apiJson<any[]>("/readings/x"),
            ]);
        } catch (e: any) {
            error = e.message || "Failed to load reports";
        } finally {
            loading = false;
        }
    }

    function flash(message: string, isError = false) {
        if (isError) {
            error = message;
            setTimeout(() => error = "", 5000);
        } else {
            successMessage = message;
            setTimeout(() => successMessage = "", 4000);
        }
    }

    async function downloadFile(path: string, fallbackName: string) {
        try {
            const response = await apiFetch(path);
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || "Download failed");
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

    async function generateZReading() {
        passwordError = "";
        zLoading = true;
        try {
            await apiJson("/auth/verify-password", {
                method: "POST",
                body: JSON.stringify({ password }),
            });
            const reading = await apiJson<any>("/readings/z", {
                method: "POST",
                body: JSON.stringify({ password }),
            });
            zDialogOpen = false;
            password = "";
            flash(`Z-Reading #${reading.z_counter} generated`);
            await loadReports();
        } catch (e: any) {
            passwordError = e.message === "Incorrect password" || e.message === "Password confirmation failed"
                ? "Incorrect password"
                : e.message;
        } finally {
            zLoading = false;
        }
    }

    async function generateXReading() {
        xLoading = true;
        try {
            const reading = await apiJson<any>("/readings/x", {
                method: "POST",
                body: JSON.stringify({}),
            });
            flash(`X-Reading generated at ${formatDateTime(reading.generated_at)}`);
            await loadReports();
        } catch (e: any) {
            flash(e.message, true);
        } finally {
            xLoading = false;
        }
    }

    async function downloadJournalRange() {
        const start = new Date(`${journalStartDate}T00:00:00+08:00`);
        const end = new Date(`${journalEndDate}T00:00:00+08:00`);
        if (end < start) {
            flash("End date must be on or after start date", true);
            return;
        }
        const dayCount = Math.floor((end.getTime() - start.getTime()) / 86400000) + 1;
        if (dayCount > 31) {
            flash("Download a maximum of 31 days at a time", true);
            return;
        }
        for (let offset = 0; offset < dayCount; offset += 1) {
            const date = new Date(start.getTime() + offset * 86400000);
            const dateString = phDateString(date);
            await downloadFile(`/readings/ejournal/export?date=${dateString}`, `ejournal-${dateString}.txt`);
        }
    }
</script>

<div class="min-h-screen bg-muted/30">
    <header class="bg-background border-b px-4 py-3 flex items-center gap-3 sticky top-0 z-20">
        <Button variant="ghost" size="icon" aria-label="Go back" onclick={() => history.back()}>
            <ArrowLeft class="size-4" />
        </Button>
        <FileBarChart class="size-5 text-primary" />
        <div class="flex-1">
            <h1 class="font-semibold text-sm">BIR Reports</h1>
            <p class="text-xs text-muted-foreground">Compliance reports and electronic journals</p>
        </div>
        <AppQuickNav current="/reports" />
    </header>

    {#if error}<div class="bg-destructive/10 text-destructive text-sm px-4 py-2 text-center" role="alert">{error}</div>{/if}
    {#if successMessage}<div class="bg-green-500/10 text-green-700 text-sm px-4 py-2 text-center" role="status">{successMessage}</div>{/if}

    <main class="max-w-6xl mx-auto p-4">
        {#if loading}
            <div class="h-64 flex items-center justify-center"><Loader2 class="size-6 animate-spin text-muted-foreground" /></div>
        {:else}
            <Tabs.Root bind:value={activeTab}>
                <Tabs.List class="grid w-full grid-cols-2 md:grid-cols-4 mb-4">
                    <Tabs.Trigger value="daily"><ReceiptText /> POS Daily</Tabs.Trigger>
                    <Tabs.Trigger value="z"><FileBarChart /> Z-Reading</Tabs.Trigger>
                    <Tabs.Trigger value="journal"><BookOpenText /> E-Journal</Tabs.Trigger>
                    <Tabs.Trigger value="x"><FileClock /> X-Reading</Tabs.Trigger>
                </Tabs.List>

                <Tabs.Content value="daily" class="space-y-4">
                    <section class="bg-background border rounded-xl p-4 flex flex-col md:flex-row md:items-end gap-3">
                        <div class="flex-1">
                            <h2 class="font-semibold">POS Daily Report</h2>
                            <p class="text-sm text-muted-foreground">All invoices and voids recorded for a Philippine business date.</p>
                        </div>
                        <div class="space-y-1">
                            <label for="daily-date" class="text-xs font-medium">Report date</label>
                            <Input id="daily-date" type="date" bind:value={selectedDate} />
                        </div>
                        <Button
                            variant="outline"
                            disabled={!selectedDateZ}
                            title={selectedDateZ ? "Export Z-Reading Excel" : "Generate a Z-Reading for this date before exporting"}
                            onclick={() => selectedDateZ && downloadFile(`/readings/z/${selectedDateZ.id}/export`, `z-reading-${selectedDate}.xlsx`)}
                        >
                            <Download /> Export Excel
                        </Button>
                    </section>

                    <section class="bg-background border rounded-xl overflow-hidden">
                        {#if dailyInvoices.length === 0}
                            <div class="py-16 text-center text-muted-foreground">
                                <ReceiptText class="size-8 mx-auto mb-2" />
                                <p class="font-medium text-sm">No invoices for this date</p>
                                <p class="text-xs mt-1">Completed and voided transactions will appear here.</p>
                            </div>
                        {:else}
                            <Table.Root>
                                <Table.Header>
                                    <Table.Row>
                                        <Table.Head>Invoice</Table.Head><Table.Head>Time</Table.Head>
                                        <Table.Head>Items</Table.Head><Table.Head class="text-right">Total</Table.Head>
                                        <Table.Head>Status</Table.Head>
                                    </Table.Row>
                                </Table.Header>
                                <Table.Body>
                                    {#each dailyInvoices as invoice}
                                        <Table.Row>
                                            <Table.Cell class="font-mono">#{invoice.invoice_number}</Table.Cell>
                                            <Table.Cell>{formatDateTime(invoice.date_time)}</Table.Cell>
                                            <Table.Cell>{invoice.items.length}</Table.Cell>
                                            <Table.Cell class="text-right font-medium">{money(invoice.total_amount)}</Table.Cell>
                                            <Table.Cell><Badge variant={invoice.status === "active" ? "default" : "destructive"}>{invoice.status}</Badge></Table.Cell>
                                        </Table.Row>
                                    {/each}
                                </Table.Body>
                                <Table.Footer>
                                    <Table.Row>
                                        <Table.Cell colspan={2} class="font-semibold">Totals</Table.Cell>
                                        <Table.Cell>{dailyTransactions} transactions / {dailyVoids} voids</Table.Cell>
                                        <Table.Cell class="text-right font-bold">{money(dailySales)}</Table.Cell>
                                        <Table.Cell></Table.Cell>
                                    </Table.Row>
                                </Table.Footer>
                            </Table.Root>
                        {/if}
                    </section>
                </Tabs.Content>

                <Tabs.Content value="z" class="space-y-4">
                    <section class="bg-background border rounded-xl p-4 flex items-center gap-3">
                        <div class="flex-1">
                            <h2 class="font-semibold">Z-Reading Report</h2>
                            <p class="text-sm text-muted-foreground">Final end-of-day sales closure. Only one can be generated per business date.</p>
                        </div>
                        <Button onclick={() => { password = ""; passwordError = ""; zDialogOpen = true; }}>
                            <LockKeyhole /> Generate Z-Reading
                        </Button>
                    </section>
                    <section class="bg-background border rounded-xl overflow-hidden">
                        {#if zReadings.length === 0}
                            <div class="py-16 text-center text-muted-foreground">
                                <FileBarChart class="size-8 mx-auto mb-2" />
                                <p class="font-medium text-sm">No Z-Readings yet</p>
                                <p class="text-xs mt-1">Generate one after closing sales for the day.</p>
                            </div>
                        {:else}
                            <Table.Root>
                                <Table.Header><Table.Row>
                                    <Table.Head>Date</Table.Head><Table.Head>Z-Counter</Table.Head>
                                    <Table.Head class="text-right">Total Sales</Table.Head><Table.Head>Transactions</Table.Head>
                                    <Table.Head class="text-right">Accumulated Total</Table.Head><Table.Head>Actions</Table.Head>
                                </Table.Row></Table.Header>
                                <Table.Body>
                                    {#each zReadings as reading}
                                        <Table.Row>
                                            <Table.Cell>{reading.business_date}</Table.Cell>
                                            <Table.Cell>#{reading.z_counter}</Table.Cell>
                                            <Table.Cell class="text-right">{money(reading.total_sales)}</Table.Cell>
                                            <Table.Cell>{reading.transaction_count}</Table.Cell>
                                            <Table.Cell class="text-right font-semibold">{money(reading.accumulated_grand_total)}</Table.Cell>
                                            <Table.Cell>
                                                <div class="flex gap-1">
                                                    <Button variant="ghost" size="icon" aria-label="Toggle Z-Reading details" onclick={() => expandedZ = expandedZ === reading.id ? null : reading.id}>
                                                        {#if expandedZ === reading.id}<ChevronUp />{:else}<ChevronDown />{/if}
                                                    </Button>
                                                    <Button variant="outline" size="sm" onclick={() => downloadFile(`/readings/z/${reading.id}/export`, `z-reading-${reading.business_date}.xlsx`)}>
                                                        <Download /> Export Excel
                                                    </Button>
                                                </div>
                                            </Table.Cell>
                                        </Table.Row>
                                        {#if expandedZ === reading.id}
                                            <Table.Row>
                                                <Table.Cell colspan={6}>
                                                    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 bg-muted/40 rounded-lg p-4 text-sm">
                                                        <div><p class="text-muted-foreground text-xs">VAT-Exempt</p><p class="font-medium">{money(reading.vat_exempt_sales)}</p></div>
                                                        <div><p class="text-muted-foreground text-xs">VATable</p><p class="font-medium">{money(reading.vatable_sales)}</p></div>
                                                        <div><p class="text-muted-foreground text-xs">SSPT Sales</p><p class="font-medium">{money(reading.sspt_sales)}</p></div>
                                                        <div><p class="text-muted-foreground text-xs">Discounts</p><p class="font-medium">{money(reading.discount_amount)}</p></div>
                                                        <div><p class="text-muted-foreground text-xs">VAT Amount</p><p class="font-medium">{money(reading.vat_amount)}</p></div>
                                                        <div><p class="text-muted-foreground text-xs">Net Total</p><p class="font-medium">{money(reading.net_total)}</p></div>
                                                        <div><p class="text-muted-foreground text-xs">Voids</p><p class="font-medium">{reading.void_count}</p></div>
                                                        <div><p class="text-muted-foreground text-xs">Invoice Range</p><p class="font-medium">{reading.starting_invoice_no ?? "-"} to {reading.ending_invoice_no ?? "-"}</p></div>
                                                    </div>
                                                </Table.Cell>
                                            </Table.Row>
                                        {/if}
                                    {/each}
                                </Table.Body>
                            </Table.Root>
                        {/if}
                    </section>
                </Tabs.Content>

                <Tabs.Content value="journal" class="space-y-4">
                    <section class="bg-background border rounded-xl p-5 space-y-4">
                        <div>
                            <h2 class="font-semibold">E-Journal</h2>
                            <p class="text-sm text-muted-foreground mt-1">The E-Journal is a BIR-mandated electronic record compiling all invoices, voids, X-readings, and Z-readings in chronological order. Required for BIR compliance under RMO 24-2023.</p>
                        </div>
                        <div class="flex flex-col sm:flex-row sm:items-end gap-3">
                            <div class="space-y-1"><label for="journal-start" class="text-xs font-medium">Start date</label><Input id="journal-start" type="date" bind:value={journalStartDate} /></div>
                            <div class="space-y-1"><label for="journal-end" class="text-xs font-medium">End date</label><Input id="journal-end" type="date" bind:value={journalEndDate} /></div>
                            <Button onclick={downloadJournalRange}><Download /> Download E-Journal (.txt)</Button>
                        </div>
                    </section>
                </Tabs.Content>

                <Tabs.Content value="x" class="space-y-4">
                    <section class="bg-background border rounded-xl p-4 flex items-center gap-3">
                        <div class="flex-1">
                            <h2 class="font-semibold">X-Reading</h2>
                            <p class="text-sm text-muted-foreground">Interim shift snapshot that can be generated multiple times without closing sales.</p>
                        </div>
                        <Button onclick={generateXReading} disabled={xLoading} aria-busy={xLoading}>
                            {#if xLoading}<Loader2 class="animate-spin" />{:else}<Play />{/if} Generate X-Reading
                        </Button>
                    </section>
                    <section class="bg-background border rounded-xl overflow-hidden">
                        {#if xReadings.length === 0}
                            <div class="py-16 text-center text-muted-foreground">
                                <FileClock class="size-8 mx-auto mb-2" />
                                <p class="font-medium text-sm">No X-Readings yet</p>
                                <p class="text-xs mt-1">Generate one to record the current shift totals.</p>
                            </div>
                        {:else}
                            <Table.Root>
                                <Table.Header><Table.Row>
                                    <Table.Head>Date / Time</Table.Head><Table.Head class="text-right">Total Sales</Table.Head>
                                    <Table.Head>Transactions</Table.Head><Table.Head>Voids</Table.Head>
                                    <Table.Head>Invoice Range</Table.Head><Table.Head>Details</Table.Head>
                                </Table.Row></Table.Header>
                                <Table.Body>
                                    {#each xReadings as reading}
                                        <Table.Row>
                                            <Table.Cell>{formatDateTime(reading.generated_at)}</Table.Cell>
                                            <Table.Cell class="text-right">{money(reading.total_sales)}</Table.Cell>
                                            <Table.Cell>{reading.transaction_count}</Table.Cell>
                                            <Table.Cell>{reading.void_count}</Table.Cell>
                                            <Table.Cell>{reading.starting_invoice_no ?? "-"} to {reading.ending_invoice_no ?? "-"}</Table.Cell>
                                            <Table.Cell><Button variant="ghost" size="icon" aria-label="Toggle X-Reading details" onclick={() => expandedX = expandedX === reading.id ? null : reading.id}>{#if expandedX === reading.id}<ChevronUp />{:else}<ChevronDown />{/if}</Button></Table.Cell>
                                        </Table.Row>
                                        {#if expandedX === reading.id}
                                            <Table.Row><Table.Cell colspan={6}>
                                                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 bg-muted/40 rounded-lg p-4 text-sm">
                                                    <div><p class="text-xs text-muted-foreground">VAT-Exempt</p><p>{money(reading.vat_exempt_sales)}</p></div>
                                                    <div><p class="text-xs text-muted-foreground">VATable</p><p>{money(reading.vatable_sales)}</p></div>
                                                    <div><p class="text-xs text-muted-foreground">SSPT Sales</p><p>{money(reading.sspt_sales)}</p></div>
                                                    <div><p class="text-xs text-muted-foreground">Discounts</p><p>{money(reading.discount_amount)}</p></div>
                                                </div>
                                            </Table.Cell></Table.Row>
                                        {/if}
                                    {/each}
                                </Table.Body>
                            </Table.Root>
                        {/if}
                    </section>
                </Tabs.Content>
            </Tabs.Root>
        {/if}
    </main>
</div>

<Dialog.Root bind:open={zDialogOpen}>
    <Dialog.Content>
        <Dialog.Header>
            <Dialog.Title>Confirm Z-Reading</Dialog.Title>
            <Dialog.Description>Enter your password to close the current Philippine business date.</Dialog.Description>
        </Dialog.Header>
        <div class="space-y-2">
            <Input type="password" bind:value={password} autocomplete="current-password" placeholder="Current password" aria-label="Password confirmation" />
            {#if passwordError}<p class="text-sm text-destructive" role="alert">{passwordError}</p>{/if}
        </div>
        <Dialog.Footer>
            <Button variant="outline" onclick={() => zDialogOpen = false}>Cancel</Button>
            <Button onclick={generateZReading} disabled={!password || zLoading} aria-busy={zLoading}>
                {#if zLoading}<Loader2 class="animate-spin" />{:else}<LockKeyhole />{/if} Generate Z-Reading
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
