<script lang="ts">
    import { goto } from "$app/navigation";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Label } from "$lib/components/ui/label";
    import * as Card from "$lib/components/ui/card";
    import * as Dialog from "$lib/components/ui/dialog";
    import { Badge } from "$lib/components/ui/badge";
    import { Check, Loader2, LockKeyhole, Scale, ShoppingBasket, Zap } from "lucide-svelte";

    let email = $state("");
    let password = $state("");
    let error = $state("");
    let loading = $state(false);

    let resetOpen = $state(false);
    let resetEmail = $state("");
    let resetOtp = $state("");
    let resetPassword = $state("");
    let resetMessage = $state("");
    let resetError = $state("");
    let resetLoading = $state(false);
    let resetStep = $state<"email" | "otp">("email");

    async function handleLogin() {
        error = "";
        loading = true;
        try {
            const res = await apiJson<any>("/auth/login", {
                method: "POST",
                body: JSON.stringify({ email, password }),
            });
            auth.login(res.user, res.access_token, res.refresh_token);
            goto("/dashboard");
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function requestReset() {
        resetError = "";
        resetMessage = "";
        resetLoading = true;
        try {
            const res = await apiJson<any>("/auth/password-reset/request", {
                method: "POST",
                body: JSON.stringify({ email: resetEmail }),
            });
            resetMessage = res.message ?? "Check your email for the reset code.";
            resetStep = "otp";
        } catch (e: any) {
            resetError = e.message;
        } finally {
            resetLoading = false;
        }
    }

    async function confirmReset() {
        resetError = "";
        resetMessage = "";
        resetLoading = true;
        try {
            const res = await apiJson<any>("/auth/password-reset/confirm", {
                method: "POST",
                body: JSON.stringify({
                    email: resetEmail,
                    otp: resetOtp,
                    new_password: resetPassword,
                }),
            });
            resetMessage = res.message ?? "Password reset successful.";
            password = "";
            resetOtp = "";
            resetPassword = "";
            setTimeout(() => {
                resetOpen = false;
                resetStep = "email";
            }, 1200);
        } catch (e: any) {
            resetError = e.message;
        } finally {
            resetLoading = false;
        }
    }
</script>

<div class="min-h-screen bg-[radial-gradient(circle_at_top_left,hsl(var(--primary)/0.14),transparent_34%),hsl(var(--muted)/0.35)] p-4">
    <div class="mx-auto grid min-h-[calc(100vh-2rem)] w-full max-w-6xl items-center gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section class="hidden lg:block space-y-6">
            <Badge variant="outline" class="bg-background/80 backdrop-blur">
                Scale-integrated POS for meat, fish, produce, and retail
            </Badge>
            <div class="space-y-4">
                <div class="flex items-center gap-3">
                    <div class="rounded-2xl bg-primary p-4 text-primary-foreground shadow-lg">
                        <ShoppingBasket class="size-8" />
                    </div>
                    <div>
                        <h1 class="text-4xl font-semibold tracking-tight">UpScale POS</h1>
                        <p class="text-muted-foreground">Weigh, sell, invoice, and report from one fast cashier screen.</p>
                    </div>
                </div>
                <p class="max-w-xl text-lg text-muted-foreground">
                    Built for stores where speed matters: barcode-like product taps, live inventory protection,
                    BIR reports, and weighing scale workflows without the usual clutter.
                </p>
            </div>
            <div class="grid max-w-xl gap-3 sm:grid-cols-3">
                <div class="rounded-2xl border bg-background/80 p-4 shadow-sm">
                    <Scale class="mb-3 size-5 text-primary" />
                    <p class="font-medium">Scale ready</p>
                    <p class="mt-1 text-xs text-muted-foreground">Designed around per-kg selling.</p>
                </div>
                <div class="rounded-2xl border bg-background/80 p-4 shadow-sm">
                    <Zap class="mb-3 size-5 text-primary" />
                    <p class="font-medium">Fast checkout</p>
                    <p class="mt-1 text-xs text-muted-foreground">Cash-first flow with receipt preview.</p>
                </div>
                <div class="rounded-2xl border bg-background/80 p-4 shadow-sm">
                    <Check class="mb-3 size-5 text-primary" />
                    <p class="font-medium">BIR-Compliant</p>
                    <p class="mt-1 text-xs text-muted-foreground">Invoices, readings, and audit trail.</p>
                </div>
            </div>
        </section>

        <div class="w-full max-w-md justify-self-center space-y-5">
            <div class="text-center lg:hidden">
                <div class="mx-auto mb-3 w-fit rounded-2xl bg-primary p-3 text-primary-foreground">
                    <ShoppingBasket class="size-7" />
                </div>
                <h1 class="text-2xl font-semibold tracking-tight">UpScale POS</h1>
                <p class="text-sm text-muted-foreground">Scale-integrated selling, inventory, and BIR reports.</p>
            </div>

            <Card.Root class="border-primary/10 shadow-xl">
                <Card.Header>
                    <Card.Title>Welcome back</Card.Title>
                    <Card.Description>Sign in to continue to your cashier dashboard.</Card.Description>
                </Card.Header>
                <Card.Content class="space-y-4">
                    {#if error}
                        <div class="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
                            {error}
                        </div>
                    {/if}

                    <div class="space-y-2">
                        <Label for="email">Email</Label>
                        <Input id="email" type="email" placeholder="you@example.com" bind:value={email} autocomplete="email" />
                    </div>

                    <div class="space-y-2">
                        <div class="flex items-center justify-between gap-3">
                            <Label for="password">Password</Label>
                            <button type="button" class="text-xs text-primary underline-offset-4 hover:underline" onclick={() => { resetEmail = email; resetOpen = true; }}>
                                Forgot password?
                            </button>
                        </div>
                        <Input id="password" type="password" placeholder="Enter your password" bind:value={password} autocomplete="current-password" />
                    </div>

                    <Button class="h-11 w-full" onclick={handleLogin} disabled={loading || !email || !password} aria-busy={loading}>
                        {#if loading}<Loader2 class="mr-2 size-4 animate-spin" />Signing in...{:else}Sign in{/if}
                    </Button>
                </Card.Content>
            </Card.Root>

            <p class="text-center text-sm text-muted-foreground">
                New to UpScale?
                <a href="/register" class="text-primary underline underline-offset-4 hover:text-primary/80">Create an account</a>
            </p>
        </div>
    </div>
</div>

<Dialog.Root bind:open={resetOpen}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title class="flex items-center gap-2"><LockKeyhole class="size-5 text-primary" /> Reset password</Dialog.Title>
            <Dialog.Description>We will email a 6-digit code to verify your account.</Dialog.Description>
        </Dialog.Header>

        <div class="space-y-4">
            {#if resetError}<div class="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">{resetError}</div>{/if}
            {#if resetMessage}<div class="rounded-md bg-green-600/10 px-3 py-2 text-sm text-green-700" role="status">{resetMessage}</div>{/if}

            <div class="space-y-2">
                <Label for="reset-email">Email</Label>
                <Input id="reset-email" type="email" bind:value={resetEmail} placeholder="you@example.com" />
            </div>

            {#if resetStep === "otp"}
                <div class="space-y-2">
                    <Label for="reset-otp">One-time code</Label>
                    <Input id="reset-otp" inputmode="numeric" maxlength={6} bind:value={resetOtp} placeholder="000000" />
                </div>
                <div class="space-y-2">
                    <Label for="reset-password">New password</Label>
                    <Input id="reset-password" type="password" bind:value={resetPassword} placeholder="Create a strong password" />
                </div>
            {/if}
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => resetOpen = false}>Cancel</Button>
            {#if resetStep === "email"}
                <Button onclick={requestReset} disabled={resetLoading || !resetEmail} aria-busy={resetLoading}>
                    {#if resetLoading}<Loader2 class="mr-2 size-4 animate-spin" />{/if}
                    Send code
                </Button>
            {:else}
                <Button onclick={confirmReset} disabled={resetLoading || !resetOtp || !resetPassword} aria-busy={resetLoading}>
                    {#if resetLoading}<Loader2 class="mr-2 size-4 animate-spin" />{/if}
                    Reset password
                </Button>
            {/if}
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
