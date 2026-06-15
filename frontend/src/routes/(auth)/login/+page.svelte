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
    let error = $state("");
    let loading = $state(false);

    async function handleLogin() {
        error = "";
        loading = true;
        try {
            const res = await apiJson<any>("/auth/login", {
                method: "POST",
                body: JSON.stringify({ email, password }),
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

        <!-- Logo / Brand -->
        <div class="flex flex-col items-center gap-2 text-center">
            <div class="bg-primary rounded-xl p-3">
                <ShoppingBasket class="text-primary-foreground size-7" />
            </div>
            <h1 class="text-2xl font-semibold tracking-tight">UpScale POS</h1>
            <p class="text-muted-foreground text-sm">Sign in to your account</p>
        </div>

        <Card.Root>
            <Card.Content class="pt-6 space-y-4">

                {#if error}
                    <div class="bg-destructive/10 text-destructive text-sm rounded-md px-3 py-2">
                        {error}
                    </div>
                {/if}

                <div class="space-y-2">
                    <Label for="email">Email</Label>
                    <Input
                        id="email"
                        type="email"
                        placeholder="you@example.com"
                        bind:value={email}
                        autocomplete="email"
                        aria-label="Email address"
                    />
                </div>

                <div class="space-y-2">
                    <Label for="password">Password</Label>
                    <Input
                        id="password"
                        type="password"
                        placeholder="••••••••"
                        bind:value={password}
                        autocomplete="current-password"
                        aria-label="Password"
                    />
                </div>

                <Button
                    class="w-full"
                    onclick={handleLogin}
                    disabled={loading || !email || !password}
                    aria-busy={loading}
                >
                    {#if loading}
                        <Loader2 class="size-4 animate-spin mr-2" />
                        Signing in...
                    {:else}
                        Sign in
                    {/if}
                </Button>

            </Card.Content>
        </Card.Root>

        <p class="text-center text-sm text-muted-foreground">
            Don't have an account?
            <a href="/register" class="text-primary underline underline-offset-4 hover:text-primary/80">
                Create one
            </a>
        </p>

    </div>
</div>
