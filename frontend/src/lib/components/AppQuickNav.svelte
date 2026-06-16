<script lang="ts">
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button";
    import { FileBarChart, LayoutDashboard, Package, ReceiptText, Settings, ShoppingCart, Users } from "lucide-svelte";

    let { current = "" }: { current?: string } = $props();

    const links = [
        { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
        { path: "/pos", label: "POS", icon: ShoppingCart },
        { path: "/inventory", label: "Inventory", icon: Package },
        { path: "/invoices", label: "Invoices", icon: ReceiptText },
        { path: "/reports", label: "Reports", icon: FileBarChart },
        { path: "/suppliers", label: "Suppliers", icon: Users },
        { path: "/settings", label: "Settings", icon: Settings },
    ];
</script>

<nav class="flex max-w-[68vw] items-center gap-1 overflow-x-auto py-1" aria-label="Quick access">
    {#each links as link}
        {@const Icon = link.icon}
        <Button
            variant="ghost"
            size="icon"
            class="size-10 shrink-0 hover:bg-primary! hover:text-primary-foreground! active:translate-y-0 sm:size-9
                {current === link.path ? 'bg-primary! text-primary-foreground! shadow-sm' : ''}"
            aria-label={link.label}
            aria-current={current === link.path ? "page" : undefined}
            onclick={() => goto(link.path)}
        >
            <Icon class="size-4" />
        </Button>
    {/each}
</nav>
