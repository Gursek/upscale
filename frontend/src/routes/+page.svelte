<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";
    import { ShoppingBasket } from "lucide-svelte";

    onMount(async () => {
        const token = localStorage.getItem("access_token");
        if (!token) {
            goto("/login");
            return;
        }
        try {
            const user = await apiJson<any>("/auth/me");
            auth.login(user, token);
            goto("/dashboard");
        } catch {
            goto("/login");
        }
    });
</script>

<div class="min-h-screen bg-muted/30 flex items-center justify-center px-4">
    <div class="rounded-2xl border bg-background p-6 text-center shadow-sm">
        <ShoppingBasket class="mx-auto mb-3 size-8 text-primary" />
        <p class="text-sm font-medium">Opening UpScale POS</p>
        <p class="mt-1 text-xs text-muted-foreground">Taking you to the right page...</p>
    </div>
</div>
