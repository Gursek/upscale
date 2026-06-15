<script lang="ts">
    import { goto } from "$app/navigation";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import * as Card from "$lib/components/ui/card";
    import { ShoppingBasket, Loader2, Check, X } from "lucide-svelte";

    let email = $state("");
    let password = $state("");
    let confirmPassword = $state("");
    let businessName = $state("");
    let businessAddress = $state("");
    let tin = $state("");
    let vatStatus = $state("non_vat");
    let error = $state("");
    let loading = $state(false);
    let passwordRequirements = $derived([
        { label: "At least 8 characters", met: password.length >= 8 },
        { label: "One uppercase letter", met: /[A-Z]/.test(password) },
        { label: "One number", met: /\d/.test(password) },
        { label: "One special character", met: /[^A-Za-z0-9]/.test(password) },
    ]);
    let metRequirementCount = $derived(passwordRequirements.filter((requirement) => requirement.met).length);
    let passwordStrength = $derived(
        metRequirementCount <= 2 ? "Weak" : metRequirementCount === 3 ? "Fair" : "Strong"
    );
    let passwordIsStrong = $derived(metRequirementCount === 4);

    async function handleRegister() {
        error = "";
        if (password !== confirmPassword) {
            error = "Passwords do not match";
            return;
        }
        if (!passwordIsStrong) {
            error = "Password does not meet all security requirements";
            return;
        }
        loading = true;
        try {
            const res = await apiJson<any>("/auth/register", {
                method: "POST",
                body: JSON.stringify({
                    email,
                    password,
                    business_name: businessName,
                    business_address: businessAddress,
                    tin,
                    vat_status: vatStatus,
                }),
            });
            auth.login(res.user, res.access_token);
            goto("/dashboard");
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    }
</script>

<div class="min-h-screen flex items-center justify-center bg-muted/40 p-4">
    <div class="w-full max-w-sm space-y-6">

        <div class="flex flex-col items-center gap-2 text-center">
            <div class="bg-primary rounded-xl p-3">
                <ShoppingBasket class="text-primary-foreground size-7" />
            </div>
            <h1 class="text-2xl font-semibold tracking-tight">Create an account</h1>
            <p class="text-muted-foreground text-sm">Set up your UpScale POS</p>
        </div>

        <Card.Root>
            <Card.Content class="pt-6 space-y-4">

                {#if error}
                    <div class="bg-destructive/10 text-destructive text-sm rounded-md px-3 py-2">
                        {error}
                    </div>
                {/if}

                <div class="space-y-2">
                    <Label for="businessName">Business Name</Label>
                    <Input id="businessName" placeholder="VDA Meat Shop" bind:value={businessName} />
                </div>

                <div class="space-y-2">
                    <Label for="email">Email</Label>
                    <Input id="email" type="email" placeholder="you@example.com" bind:value={email} />
                </div>

                <div class="space-y-2">
                    <Label for="tin">TIN <span class="text-muted-foreground">(optional)</span></Label>
                    <Input id="tin" placeholder="123-456-789" bind:value={tin} />
                </div>

                <div class="space-y-2">
                    <Label for="businessAddress">Business Address <span class="text-muted-foreground">(optional)</span></Label>
                    <Input id="businessAddress" placeholder="123 Main St, City" bind:value={businessAddress} />
                </div>

                <div class="space-y-2">
                    <Label for="vatStatus">VAT Status</Label>
                    <select
                        id="vatStatus"
                        bind:value={vatStatus}
                        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
                        aria-label="VAT registration status"
                    >
                        <option value="non_vat">Non-VAT Registered</option>
                        <option value="vat">VAT Registered</option>
                    </select>
                </div>

                <div class="space-y-2">
                    <Label for="password">Password</Label>
                    <Input
                        id="password"
                        type="password"
                        placeholder="Create a strong password"
                        bind:value={password}
                        autocomplete="new-password"
                        aria-describedby="password-strength password-requirements"
                    />
                    {#if password}
                        <div id="password-strength" class="space-y-1" aria-live="polite">
                            <div class="flex justify-between text-xs">
                                <span class="text-muted-foreground">Password strength</span>
                                <span class={passwordStrength === "Strong" ? "text-green-700" : passwordStrength === "Fair" ? "text-amber-700" : "text-destructive"}>
                                    {passwordStrength}
                                </span>
                            </div>
                            <div class="grid grid-cols-4 gap-1" aria-hidden="true">
                                {#each [1, 2, 3, 4] as segment}
                                    <div class="h-1.5 rounded-full {segment <= metRequirementCount ? (passwordStrength === 'Strong' ? 'bg-green-600' : passwordStrength === 'Fair' ? 'bg-amber-500' : 'bg-destructive') : 'bg-muted'}"></div>
                                {/each}
                            </div>
                        </div>
                    {/if}
                    <ul id="password-requirements" class="grid grid-cols-2 gap-1 text-xs">
                        {#each passwordRequirements as requirement}
                            <li class="flex items-center gap-1 {requirement.met ? 'text-green-700' : 'text-muted-foreground'}">
                                {#if requirement.met}
                                    <Check class="size-3" />
                                {:else}
                                    <X class="size-3" />
                                {/if}
                                {requirement.label}
                            </li>
                        {/each}
                    </ul>
                </div>

                <div class="space-y-2">
                    <Label for="confirmPassword">Confirm Password</Label>
                    <Input id="confirmPassword" type="password" placeholder="••••••••" bind:value={confirmPassword} />
                </div>

                <Button
                    class="w-full"
                    onclick={handleRegister}
                    disabled={loading || !email || !passwordIsStrong || password !== confirmPassword || !businessName}
                    aria-busy={loading}
                >
                    {#if loading}
                        <Loader2 class="size-4 animate-spin mr-2" />
                        Creating account...
                    {:else}
                        Create account
                    {/if}
                </Button>

            </Card.Content>
        </Card.Root>

        <p class="text-center text-sm text-muted-foreground">
            Already have an account?
            <a href="/login" class="text-primary underline underline-offset-4 hover:text-primary/80">
                Sign in
            </a>
        </p>

    </div>
</div>
