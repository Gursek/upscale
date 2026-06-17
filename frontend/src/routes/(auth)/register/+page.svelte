<script lang="ts">
    import { goto } from "$app/navigation";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import * as Card from "$lib/components/ui/card";
    import { Badge } from "$lib/components/ui/badge";
    import { Check, Loader2, Scale, ShieldCheck, ShoppingBasket, X, Zap } from "lucide-svelte";

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
            auth.login(res.user, res.access_token, res.refresh_token);
            goto("/dashboard");
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    }
</script>

<div class="min-h-screen bg-[radial-gradient(circle_at_top_right,hsl(var(--primary)/0.14),transparent_34%),hsl(var(--muted)/0.35)] p-4">
    <div class="mx-auto grid min-h-[calc(100vh-2rem)] w-full max-w-6xl items-center gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <section class="hidden lg:block space-y-6">
            <Badge variant="outline" class="bg-background/80 backdrop-blur">Launch your scale-ready POS</Badge>
            <div class="space-y-4">
                <div class="rounded-2xl bg-primary p-4 text-primary-foreground shadow-lg w-fit">
                    <ShoppingBasket class="size-8" />
                </div>
                <h1 class="text-4xl font-semibold tracking-tight">Start with the workflows that matter at the counter.</h1>
                <p class="max-w-xl text-lg text-muted-foreground">
                    UpScale combines product cards, live stock protection, weighing-scale workflows, invoices, and BIR reports
                    so your store can move faster without losing control.
                </p>
            </div>
            <div class="space-y-3">
                <div class="flex items-center gap-3 rounded-2xl border bg-background/80 p-4 shadow-sm">
                    <Scale class="size-5 text-primary" />
                    <span class="font-medium">Built around per-kg selling</span>
                </div>
                <div class="flex items-center gap-3 rounded-2xl border bg-background/80 p-4 shadow-sm">
                    <Zap class="size-5 text-primary" />
                    <span class="font-medium">Fast cash checkout with receipt preview</span>
                </div>
                <div class="flex items-center gap-3 rounded-2xl border bg-background/80 p-4 shadow-sm">
                    <ShieldCheck class="size-5 text-primary" />
                    <span class="font-medium">BIR-aware reports and audit records</span>
                </div>
            </div>
        </section>

        <div class="w-full max-w-lg justify-self-center space-y-5">
            <div class="text-center lg:hidden">
                <div class="mx-auto mb-3 w-fit rounded-2xl bg-primary p-3 text-primary-foreground">
                    <ShoppingBasket class="size-7" />
                </div>
                <h1 class="text-2xl font-semibold tracking-tight">Create your UpScale account</h1>
                <p class="text-sm text-muted-foreground">Scale-integrated POS for faster checkout.</p>
            </div>

            <Card.Root class="border-primary/10 shadow-xl">
                <Card.Header>
                    <Card.Title>Create your store</Card.Title>
                    <Card.Description>Set the basics now. You can complete BIR registration details later in Settings.</Card.Description>
                </Card.Header>
                <Card.Content class="space-y-4">
                    {#if error}
                        <div class="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
                            {error}
                        </div>
                    {/if}

                    <div class="grid gap-4 sm:grid-cols-2">
                        <div class="space-y-2 sm:col-span-2">
                            <Label for="businessName">Business Name</Label>
                            <Input id="businessName" placeholder="VDA Meat Shop" bind:value={businessName} />
                        </div>
                        <div class="space-y-2 sm:col-span-2">
                            <Label for="email">Email</Label>
                            <Input id="email" type="email" placeholder="you@example.com" bind:value={email} autocomplete="email" />
                        </div>
                        <div class="space-y-2">
                            <Label for="tin">TIN <span class="text-muted-foreground">(optional)</span></Label>
                            <Input id="tin" placeholder="123-456-789" bind:value={tin} />
                        </div>
                        <div class="space-y-2">
                            <Label>VAT Status</Label>
                            <div class="grid grid-cols-2 gap-2">
                                <Button type="button" variant={vatStatus === "non_vat" ? "default" : "outline"} onclick={() => vatStatus = "non_vat"}>Non-VAT</Button>
                                <Button type="button" variant={vatStatus === "vat" ? "default" : "outline"} onclick={() => vatStatus = "vat"}>VAT</Button>
                            </div>
                        </div>
                        <div class="space-y-2 sm:col-span-2">
                            <Label for="businessAddress">Business Address <span class="text-muted-foreground">(optional)</span></Label>
                            <Input id="businessAddress" placeholder="123 Main St, City" bind:value={businessAddress} />
                        </div>
                    </div>

                    <div class="space-y-2">
                        <Label for="password">Password</Label>
                        <Input id="password" type="password" placeholder="Create a strong password" bind:value={password} autocomplete="new-password" aria-describedby="password-strength password-requirements" />
                        {#if password}
                            <div id="password-strength" class="space-y-1" aria-live="polite">
                                <div class="flex justify-between text-xs">
                                    <span class="text-muted-foreground">Password strength</span>
                                    <span class={passwordStrength === "Strong" ? "text-green-700" : passwordStrength === "Fair" ? "text-amber-700" : "text-destructive"}>{passwordStrength}</span>
                                </div>
                                <div class="grid grid-cols-4 gap-1" aria-hidden="true">
                                    {#each [1, 2, 3, 4] as segment}
                                        <div class="h-1.5 rounded-full {segment <= metRequirementCount ? (passwordStrength === 'Strong' ? 'bg-green-600' : passwordStrength === 'Fair' ? 'bg-amber-500' : 'bg-destructive') : 'bg-muted'}"></div>
                                    {/each}
                                </div>
                            </div>
                        {/if}
                        <ul id="password-requirements" class="grid gap-1 text-xs sm:grid-cols-2">
                            {#each passwordRequirements as requirement}
                                <li class="flex items-center gap-1 {requirement.met ? 'text-green-700' : 'text-muted-foreground'}">
                                    {#if requirement.met}<Check class="size-3" />{:else}<X class="size-3" />{/if}
                                    {requirement.label}
                                </li>
                            {/each}
                        </ul>
                    </div>

                    <div class="space-y-2">
                        <Label for="confirmPassword">Confirm Password</Label>
                        <Input id="confirmPassword" type="password" placeholder="Confirm your password" bind:value={confirmPassword} autocomplete="new-password" />
                    </div>

                    <Button class="h-11 w-full" onclick={handleRegister} disabled={loading || !email || !passwordIsStrong || password !== confirmPassword || !businessName} aria-busy={loading}>
                        {#if loading}<Loader2 class="mr-2 size-4 animate-spin" />Creating account...{:else}Create account{/if}
                    </Button>
                </Card.Content>
            </Card.Root>

            <p class="text-center text-sm text-muted-foreground">
                Already have an account?
                <a href="/login" class="text-primary underline underline-offset-4 hover:text-primary/80">Sign in</a>
            </p>
        </div>
    </div>
</div>
