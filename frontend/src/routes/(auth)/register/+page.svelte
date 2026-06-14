<script lang="ts">
    import { goto } from "$app/navigation";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import * as Card from "$lib/components/ui/card";
    import { ShoppingBasket, Loader2 } from "lucide-svelte";

    let email = $state("");
    let password = $state("");
    let confirmPassword = $state("");
    let businessName = $state("");
    let businessAddress = $state("");
    let tin = $state("");
    let vatStatus = $state("non_vat");
    let error = $state("");
    let loading = $state(false);

    async function handleRegister() {
        error = "";
        if (password !== confirmPassword) {
            error = "Passwords do not match";
            return;
        }
        if (password.length < 8) {
            error = "Password must be at least 8 characters";
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
            goto("/onboarding");
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
                    <Input id="password" type="password" placeholder="Min. 8 characters" bind:value={password} />
                </div>

                <div class="space-y-2">
                    <Label for="confirmPassword">Confirm Password</Label>
                    <Input id="confirmPassword" type="password" placeholder="••••••••" bind:value={confirmPassword} />
                </div>

                <Button
                    class="w-full"
                    onclick={handleRegister}
                    disabled={loading || !email || !password || !businessName}
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