<script lang="ts">
    import { onMount } from "svelte";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import { Badge } from "$lib/components/ui/badge";
    import { Separator } from "$lib/components/ui/separator";
    import AppQuickNav from "$lib/components/AppQuickNav.svelte";
    import {
        Settings, Loader2, Beef, Carrot, Fish, ShoppingBag, Check, Building2,
        ShieldCheck, Store, KeyRound, Mail, Save
    } from "lucide-svelte";

    let loading = $state(true);
    let saving = $state(false);
    let error = $state("");
    let successMessage = $state("");

    let email = $state("");
    let businessName = $state("");
    let registeredName = $state("");
    let businessAddress = $state("");
    let tin = $state("");
    let vatStatus = $state("non_vat");
    let branchCode = $state("00000");
    let machineIdentificationNumber = $state("");
    let machineSerialNumber = $state("");
    let softwareLicenseNumber = $state("");
    let accreditationNumber = $state("");
    let accreditationDateIssued = $state("");
    let accreditationValidUntil = $state("");
    let ptuNumber = $state("");
    let ptuDateIssued = $state("");
    let accreditedSupplierName = $state("");
    let accreditedSupplierAddress = $state("");
    let accreditedSupplierTin = $state("");
    let softwareVersion = $state("1.0.0");
    let businessDayCutoff = $state("00:00");
    let complianceReady = $state(false);
    let missingComplianceFields = $state<string[]>([]);
    let sellsMeat = $state(false);
    let sellsFish = $state(false);
    let sellsRetail = $state(false);
    let sellsVeggies = $state(false);
    let currentPassword = $state("");
    let newPassword = $state("");
    let confirmNewPassword = $state("");
    let changingPassword = $state(false);
    let newPasswordIsStrong = $derived(
        newPassword.length >= 8 &&
        /[A-Z]/.test(newPassword) &&
        /\d/.test(newPassword) &&
        /[^A-Za-z0-9]/.test(newPassword)
    );

    onMount(async () => {
        const token = localStorage.getItem("access_token");
        if (!token) { goto("/login"); return; }

        try {
            const user = await apiJson<any>("/auth/me");
            email = user.email;
            businessName = user.business_name ?? "";
            registeredName = user.registered_name ?? user.business_name ?? "";
            businessAddress = user.business_address ?? "";
            tin = user.tin ?? "";
            vatStatus = user.vat_status ?? "non_vat";
            branchCode = user.branch_code ?? "00000";
            machineIdentificationNumber = user.machine_identification_number ?? "";
            machineSerialNumber = user.machine_serial_number ?? "";
            softwareLicenseNumber = user.software_license_number ?? "";
            accreditationNumber = user.accreditation_number ?? "";
            accreditationDateIssued = user.accreditation_date_issued ?? "";
            accreditationValidUntil = user.accreditation_valid_until ?? "";
            ptuNumber = user.ptu_number ?? "";
            ptuDateIssued = user.ptu_date_issued ?? "";
            accreditedSupplierName = user.accredited_supplier_name ?? "";
            accreditedSupplierAddress = user.accredited_supplier_address ?? "";
            accreditedSupplierTin = user.accredited_supplier_tin ?? "";
            softwareVersion = user.software_version ?? "1.0.0";
            businessDayCutoff = user.business_day_cutoff ?? "00:00";
            complianceReady = user.compliance?.ready ?? false;
            missingComplianceFields = user.compliance?.missing_fields ?? [];
            sellsMeat = user.sells_meat ?? false;
            sellsFish = user.sells_fish ?? false;
            sellsRetail = user.sells_retail ?? false;
            sellsVeggies = user.sells_veggies ?? false;
        } catch {
            error = "Failed to load settings";
        } finally {
            loading = false;
        }
    });

    function flash(msg: string, isError = false) {
        if (isError) { error = msg; setTimeout(() => error = "", 4000); }
        else { successMessage = msg; setTimeout(() => successMessage = "", 3000); }
    }

    async function saveSettings() {
        if (!businessName.trim()) {
            flash("Business name is required", true);
            return;
        }
        if (!sellsMeat && !sellsFish && !sellsRetail && !sellsVeggies) {
            flash("Please select at least one product type", true);
            return;
        }

        saving = true;
        error = "";
        try {
            const user = await apiJson<any>("/auth/me", {
                method: "PUT",
                body: JSON.stringify({
                    business_name: businessName.trim(),
                    registered_name: registeredName.trim() || null,
                    business_address: businessAddress.trim() || null,
                    tin: tin.trim() || null,
                    vat_status: vatStatus,
                    branch_code: branchCode,
                    machine_identification_number: machineIdentificationNumber.trim() || null,
                    machine_serial_number: machineSerialNumber.trim() || null,
                    software_license_number: softwareLicenseNumber.trim() || null,
                    accreditation_number: accreditationNumber.trim() || null,
                    accreditation_date_issued: accreditationDateIssued || null,
                    accreditation_valid_until: accreditationValidUntil || null,
                    ptu_number: ptuNumber.trim() || null,
                    ptu_date_issued: ptuDateIssued || null,
                    accredited_supplier_name: accreditedSupplierName.trim() || null,
                    accredited_supplier_address: accreditedSupplierAddress.trim() || null,
                    accredited_supplier_tin: accreditedSupplierTin.trim() || null,
                    software_version: softwareVersion.trim() || "1.0.0",
                    business_day_cutoff: businessDayCutoff,
                    sells_meat: sellsMeat,
                    sells_fish: sellsFish,
                    sells_retail: sellsRetail,
                    sells_veggies: sellsVeggies,
                }),
            });
            auth.update((u) => u ? { ...u, ...user } : u);
            complianceReady = user.compliance?.ready ?? false;
            missingComplianceFields = user.compliance?.missing_fields ?? [];
            flash("Settings saved");
        } catch (e: any) {
            flash(e.message, true);
        } finally {
            saving = false;
        }
    }

    async function changePassword() {
        if (!newPasswordIsStrong) {
            flash("New password must have 8 characters, an uppercase letter, a number, and a special character", true);
            return;
        }
        if (newPassword !== confirmNewPassword) {
            flash("New passwords do not match", true);
            return;
        }

        changingPassword = true;
        try {
            await apiJson("/auth/change-password", {
                method: "POST",
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            });
            currentPassword = "";
            newPassword = "";
            confirmNewPassword = "";
            flash("Password changed");
        } catch (e: any) {
            flash(e.message, true);
        } finally {
            changingPassword = false;
        }
    }
</script>

<div class="min-h-screen bg-muted/30">

    <header class="bg-background border-b px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <Settings class="size-5 text-primary" />
        <h1 class="font-semibold text-sm flex-1">Settings</h1>
        <AppQuickNav current="/settings" />
    </header>

    {#if error}
        <div class="bg-destructive/10 text-destructive text-sm px-4 py-2 text-center" role="alert">{error}</div>
    {/if}
    {#if successMessage}
        <div class="bg-green-500/10 text-green-700 text-sm px-4 py-2 text-center" role="status">{successMessage}</div>
    {/if}

    <div class="max-w-5xl mx-auto p-4">
        {#if loading}
            <div class="flex items-center justify-center h-40">
                <Loader2 class="size-6 animate-spin text-muted-foreground" />
            </div>
        {:else}
            <div class="mb-5 rounded-2xl border bg-background p-5 shadow-sm">
                <div class="flex flex-col sm:flex-row sm:items-center gap-3">
                    <div class="size-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                        <Settings class="size-5" />
                    </div>
                    <div class="flex-1">
                        <h2 class="text-lg font-semibold">Business Settings</h2>
                        <p class="text-sm text-muted-foreground">Manage your store identity, POS categories, and account security.</p>
                    </div>
                    <Badge variant="outline" class="gap-1.5">
                        <Mail class="size-3" /> {email}
                    </Badge>
                </div>
            </div>

            <form class="space-y-4 pb-24" onsubmit={(e) => { e.preventDefault(); saveSettings(); }}>
                <div class="grid lg:grid-cols-2 gap-4 items-start">
                    <div class="space-y-4">

                <section class="bg-background rounded-2xl border shadow-sm overflow-hidden">
                    <div class="flex items-center gap-3 border-b bg-muted/30 px-5 py-4">
                        <div class="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                            <Building2 class="size-4" />
                        </div>
                        <div>
                            <h2 class="font-semibold text-sm">Business Information</h2>
                            <p class="text-xs text-muted-foreground">Displayed on receipts and BIR reports.</p>
                        </div>
                    </div>

                    <div class="p-5 space-y-4">
                        <div class="space-y-2">
                            <Label for="registered-name">Registered Taxpayer Name</Label>
                            <Input id="registered-name" placeholder="Juan Dela Cruz" bind:value={registeredName} />
                        </div>

                        <div class="space-y-2">
                            <Label for="business-name">Business/Trade Name</Label>
                            <Input id="business-name" placeholder="VDA Meat Shop" bind:value={businessName} />
                        </div>

                        <div class="space-y-2">
                            <Label for="business-address">Business Address</Label>
                            <textarea
                                id="business-address"
                                placeholder="Bagac, Bataan, Philippines"
                                bind:value={businessAddress}
                                rows="3"
                                class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                                aria-label="Business address"
                            ></textarea>
                        </div>

                        <div class="grid sm:grid-cols-2 gap-4">
                            <div class="space-y-2">
                                <Label for="tin">TIN</Label>
                                <Input id="tin" placeholder="000-000-000-000" bind:value={tin} />
                            </div>

                            <div class="space-y-2">
                                <Label for="vat-status">VAT Status</Label>
                                <select
                                    id="vat-status"
                                    bind:value={vatStatus}
                                    class="w-full h-8 rounded-lg border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                                    aria-label="VAT status"
                                >
                                    <option value="non_vat">Non-VAT Registered</option>
                                    <option value="vat">VAT Registered (12%)</option>
                                </select>
                            </div>
                        </div>
                        <div class="rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                            VAT status controls tax treatment on retail goods. Basic food categories remain VAT-exempt where applicable.
                        </div>
                    </div>
                </section>

                <section class="bg-background rounded-2xl border shadow-sm overflow-hidden">
                    <div class="flex items-center gap-3 border-b bg-muted/30 px-5 py-4">
                        <div class="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                            <ShieldCheck class="size-4" />
                        </div>
                        <div class="flex-1">
                            <h2 class="font-semibold text-sm">BIR POS Registration</h2>
                            <p class="text-xs text-muted-foreground">Values printed on invoices and accreditation reports.</p>
                        </div>
                        <Badge variant={complianceReady ? "default" : "destructive"}>
                            {complianceReady ? "Configured" : "Incomplete"}
                        </Badge>
                    </div>
                    <div class="p-5 space-y-4">
                        {#if !complianceReady && missingComplianceFields.length}
                            <div class="rounded-lg bg-destructive/10 text-destructive px-3 py-2 text-xs" role="alert">
                                Missing: {missingComplianceFields.join(", ").replaceAll("_", " ")}
                            </div>
                        {/if}
                        <div class="grid sm:grid-cols-2 gap-4">
                            <div class="space-y-2">
                                <Label for="branch-code">Branch Code</Label>
                                <Input id="branch-code" maxlength={5} bind:value={branchCode} />
                            </div>
                            <div class="space-y-2">
                                <Label for="software-version">Accredited Software Version</Label>
                                <Input id="software-version" bind:value={softwareVersion} />
                            </div>
                            <div class="space-y-2">
                                <Label for="min">Machine Identification Number</Label>
                                <Input id="min" bind:value={machineIdentificationNumber} />
                            </div>
                            <div class="space-y-2">
                                <Label for="machine-serial">Machine Serial Number</Label>
                                <Input id="machine-serial" bind:value={machineSerialNumber} />
                            </div>
                            <div class="space-y-2">
                                <Label for="software-license">Software License Number</Label>
                                <Input id="software-license" bind:value={softwareLicenseNumber} />
                            </div>
                            <div class="space-y-2">
                                <Label for="business-cutoff">Business Day Rollover</Label>
                                <Input id="business-cutoff" type="time" bind:value={businessDayCutoff} />
                            </div>
                            <div class="space-y-2">
                                <Label for="accreditation-number">Accreditation Number</Label>
                                <Input id="accreditation-number" bind:value={accreditationNumber} />
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <div class="space-y-2">
                                    <Label for="accreditation-issued">Issued</Label>
                                    <Input id="accreditation-issued" type="date" bind:value={accreditationDateIssued} />
                                </div>
                                <div class="space-y-2">
                                    <Label for="accreditation-valid">Valid Until</Label>
                                    <Input id="accreditation-valid" type="date" bind:value={accreditationValidUntil} />
                                </div>
                            </div>
                            <div class="space-y-2">
                                <Label for="ptu-number">Permit to Use Number</Label>
                                <Input id="ptu-number" bind:value={ptuNumber} />
                            </div>
                            <div class="space-y-2">
                                <Label for="ptu-issued">PTU Date Issued</Label>
                                <Input id="ptu-issued" type="date" bind:value={ptuDateIssued} />
                            </div>
                        </div>
                        <Separator />
                        <p class="text-sm font-medium">Accredited supplier/developer</p>
                        <div class="grid sm:grid-cols-2 gap-4">
                            <div class="space-y-2">
                                <Label for="supplier-name">Registered Name</Label>
                                <Input id="supplier-name" bind:value={accreditedSupplierName} />
                            </div>
                            <div class="space-y-2">
                                <Label for="supplier-tin">TIN</Label>
                                <Input id="supplier-tin" bind:value={accreditedSupplierTin} />
                            </div>
                        </div>
                        <div class="space-y-2">
                            <Label for="supplier-address">Address</Label>
                            <Input id="supplier-address" bind:value={accreditedSupplierAddress} />
                        </div>
                    </div>
                </section>

                <section class="bg-background rounded-2xl border shadow-sm overflow-hidden">
                    <div class="flex items-center gap-3 border-b bg-muted/30 px-5 py-4">
                        <div class="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                            <ShieldCheck class="size-4" />
                        </div>
                        <div>
                            <h2 class="font-semibold text-sm">Account</h2>
                            <p class="text-xs text-muted-foreground">Your sign-in identity.</p>
                        </div>
                    </div>
                    <div class="p-5 space-y-2">
                        <Label for="email">Email Address</Label>
                        <div class="relative">
                            <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                            <Input id="email" class="pl-9" type="email" value={email} disabled aria-label="Email address" />
                        </div>
                        <p class="text-xs text-muted-foreground">Contact support if this email needs to be changed.</p>
                    </div>
                </section>
                    </div>

                    <div class="space-y-4">
                <section class="bg-background rounded-2xl border shadow-sm overflow-hidden">
                    <div class="flex items-center gap-3 border-b bg-muted/30 px-5 py-4">
                        <div class="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                            <Store class="size-4" />
                        </div>
                        <div>
                            <h2 class="font-semibold text-sm">Product Types</h2>
                            <p class="text-xs text-muted-foreground">Choose the categories visible in your POS.</p>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-3 p-5">
                        <button
                            type="button"
                            onclick={() => sellsMeat = !sellsMeat}
                            aria-pressed={sellsMeat}
                            aria-label="Toggle meat products"
                            class="relative min-h-24 rounded-xl border-2 p-4 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                                {sellsMeat
                                    ? 'border-primary bg-primary/5'
                                    : 'border-border bg-background hover:border-primary/40'}"
                        >
                            {#if sellsMeat}
                                <div class="absolute top-2 right-2 bg-primary text-primary-foreground rounded-full p-0.5">
                                    <Check class="size-3" />
                                </div>
                            {/if}
                            <Beef class="size-6 mb-2 {sellsMeat ? 'text-primary' : 'text-muted-foreground'}" />
                            <p class="font-medium text-xs">Meat Products</p>
                        </button>
                        <button
                            type="button"
                            onclick={() => sellsFish = !sellsFish}
                            aria-pressed={sellsFish}
                            aria-label="Toggle fish products"
                            class="relative min-h-24 rounded-xl border-2 p-4 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring {sellsFish ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}"
                        >
                            {#if sellsFish}<Check class="absolute top-2 right-2 size-3 text-primary" />{/if}
                            <Fish class="size-6 mb-2 {sellsFish ? 'text-primary' : 'text-muted-foreground'}" />
                            <p class="font-medium text-xs">Fish</p>
                        </button>

                        <button
                            type="button"
                            onclick={() => sellsRetail = !sellsRetail}
                            aria-pressed={sellsRetail}
                            aria-label="Toggle retail products"
                            class="relative min-h-24 rounded-xl border-2 p-4 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                                {sellsRetail
                                    ? 'border-primary bg-primary/5'
                                    : 'border-border bg-background hover:border-primary/40'}"
                        >
                            {#if sellsRetail}
                                <div class="absolute top-2 right-2 bg-primary text-primary-foreground rounded-full p-0.5">
                                    <Check class="size-3" />
                                </div>
                            {/if}
                            <ShoppingBag class="size-6 mb-2 {sellsRetail ? 'text-primary' : 'text-muted-foreground'}" />
                            <p class="font-medium text-xs">Retail Products</p>
                        </button>
                        <button
                            type="button"
                            onclick={() => sellsVeggies = !sellsVeggies}
                            aria-pressed={sellsVeggies}
                            aria-label="Toggle vegetable products"
                            class="relative min-h-24 rounded-xl border-2 p-4 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring {sellsVeggies ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}"
                        >
                            {#if sellsVeggies}<Check class="absolute top-2 right-2 size-3 text-primary" />{/if}
                            <Carrot class="size-6 mb-2 {sellsVeggies ? 'text-primary' : 'text-muted-foreground'}" />
                            <p class="font-medium text-xs">Veggies</p>
                        </button>
                    </div>
                </section>

                <section class="bg-background rounded-2xl border shadow-sm overflow-hidden">
                    <div class="flex items-center gap-3 border-b bg-muted/30 px-5 py-4">
                        <div class="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                            <KeyRound class="size-4" />
                        </div>
                        <div>
                            <h2 class="font-semibold text-sm">Security</h2>
                            <p class="text-xs text-muted-foreground">Update your login and Z-Reading confirmation password.</p>
                        </div>
                    </div>
                    <div class="p-5 space-y-4">
                        <div class="space-y-2">
                            <Label for="current-password">Current Password</Label>
                            <Input id="current-password" type="password" bind:value={currentPassword} autocomplete="current-password" />
                        </div>
                        <div class="grid sm:grid-cols-2 gap-4">
                            <div class="space-y-2">
                                <Label for="new-password">New Password</Label>
                                <Input id="new-password" type="password" bind:value={newPassword} autocomplete="new-password" />
                            </div>
                            <div class="space-y-2">
                                <Label for="confirm-new-password">Confirm New Password</Label>
                                <Input id="confirm-new-password" type="password" bind:value={confirmNewPassword} autocomplete="new-password" />
                            </div>
                        </div>
                        <p class="text-xs {newPassword && !newPasswordIsStrong ? 'text-destructive' : 'text-muted-foreground'}">
                            Passwords require 8+ characters, one uppercase letter, one number, and one special character.
                        </p>
                        <Button
                            type="button"
                            variant="outline"
                            onclick={changePassword}
                            disabled={changingPassword || !currentPassword || !newPasswordIsStrong || newPassword !== confirmNewPassword}
                            aria-busy={changingPassword}
                        >
                            {#if changingPassword}<Loader2 class="size-4 animate-spin mr-2" />{:else}<KeyRound class="size-4 mr-1" />{/if}
                            Change Password
                        </Button>
                    </div>
                </section>
                    </div>
                </div>

                <div class="sticky bottom-4 z-10 rounded-2xl border bg-background/95 p-3 shadow-lg backdrop-blur flex items-center gap-3">
                    <p class="hidden sm:block flex-1 text-xs text-muted-foreground">Save business and product-type changes before leaving this page.</p>
                    <Button
                        type="submit"
                        class="w-full sm:w-auto min-w-36 h-9"
                        disabled={saving || !businessName.trim() || (!sellsMeat && !sellsFish && !sellsRetail && !sellsVeggies)}
                        aria-busy={saving}
                    >
                        {#if saving}
                            <Loader2 class="size-4 animate-spin mr-2" />
                            Saving...
                        {:else}
                            <Save class="size-4 mr-1" />
                            Save Settings
                        {/if}
                    </Button>
                </div>
            </form>
        {/if}
    </div>
</div>
