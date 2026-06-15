<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import { auth } from "$lib/stores/auth";
    import { apiJson } from "$lib/api";

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
