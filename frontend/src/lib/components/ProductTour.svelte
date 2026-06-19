<script lang="ts">
    import { onMount, tick } from "svelte";
    import { Button } from "$lib/components/ui/button";
    import { X } from "lucide-svelte";

    interface TourStep {
        title: string;
        body: string;
        target: string;
    }

    interface TargetRect {
        top: number;
        left: number;
        width: number;
        height: number;
    }

    let {
        open,
        step,
        steps,
        onNext,
        onBack,
        onClose,
    }: {
        open: boolean;
        step: number;
        steps: TourStep[];
        onNext: () => void;
        onBack: () => void;
        onClose: () => void;
    } = $props();

    let targetRect = $state<TargetRect | null>(null);
    let tooltipElement = $state<HTMLElement | null>(null);
    let tooltipWidth = $state(340);
    let positionTimer: ReturnType<typeof setTimeout> | null = null;

    let currentStep = $derived(steps[step]);
    let tooltipPosition = $derived.by(() => {
        if (!targetRect) {
            return { top: 24, left: 16, placement: "below" as const };
        }

        const margin = 16;
        const gap = 18;
        const estimatedHeight = tooltipElement?.offsetHeight ?? 230;
        const viewportWidth = typeof window === "undefined" ? 1024 : window.innerWidth;
        const viewportHeight = typeof window === "undefined" ? 768 : window.innerHeight;
        const width = Math.min(tooltipWidth, viewportWidth - margin * 2);
        const centeredLeft = targetRect.left + targetRect.width / 2 - width / 2;
        const left = Math.max(margin, Math.min(centeredLeft, viewportWidth - width - margin));
        const fitsBelow = targetRect.top + targetRect.height + gap + estimatedHeight <= viewportHeight - margin;
        const top = fitsBelow
            ? targetRect.top + targetRect.height + gap
            : Math.max(margin, targetRect.top - estimatedHeight - gap);

        return { top, left, placement: fitsBelow ? "below" as const : "above" as const };
    });

    function updateTargetPosition() {
        if (!open || !currentStep) return;
        const target = document.querySelector<HTMLElement>(currentStep.target);
        if (!target) {
            targetRect = null;
            return;
        }

        const rect = target.getBoundingClientRect();
        const left = Math.max(8, rect.left - 6);
        targetRect = {
            top: Math.max(8, rect.top - 6),
            left,
            width: Math.min(window.innerWidth - left - 8, rect.width + 12),
            height: rect.height + 12,
        };
    }

    async function focusCurrentTarget() {
        if (!open || !currentStep) return;
        await tick();
        const target = document.querySelector<HTMLElement>(currentStep.target);
        if (!target) {
            targetRect = null;
            return;
        }

        target.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
        updateTargetPosition();
        if (positionTimer) clearTimeout(positionTimer);
        positionTimer = setTimeout(updateTargetPosition, 350);
    }

    $effect(() => {
        open;
        step;
        if (open) focusCurrentTarget();
    });

    $effect(() => {
        if (tooltipElement) {
            tooltipWidth = Math.min(340, window.innerWidth - 32);
            updateTargetPosition();
        }
    });

    onMount(() => {
        const handleViewportChange = () => updateTargetPosition();
        window.addEventListener("resize", handleViewportChange);
        window.addEventListener("scroll", handleViewportChange, true);

        return () => {
            window.removeEventListener("resize", handleViewportChange);
            window.removeEventListener("scroll", handleViewportChange, true);
            if (positionTimer) clearTimeout(positionTimer);
        };
    });

    function handleKeydown(event: KeyboardEvent) {
        if (open && event.key === "Escape") onClose();
    }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open && currentStep}
    <div class="fixed inset-0 z-[100]" role="dialog" aria-modal="true" aria-label="UpScale quick tour">
        <div class="absolute inset-0 {targetRect ? 'bg-transparent' : 'bg-black/45'}"></div>

        {#if targetRect}
            <div
                class="pointer-events-none fixed rounded-xl border-2 border-primary bg-transparent shadow-[0_0_0_5px_hsl(var(--primary)/0.22),0_0_0_9999px_rgb(0_0_0/0.45),0_0_28px_hsl(var(--primary)/0.45)] transition-all duration-300"
                style:top="{targetRect.top}px"
                style:left="{targetRect.left}px"
                style:width="{targetRect.width}px"
                style:height="{targetRect.height}px"
                aria-hidden="true"
            >
                <span class="absolute -inset-1 animate-pulse rounded-xl border border-primary/70"></span>
            </div>
        {/if}

        <section
            bind:this={tooltipElement}
            class="fixed w-[min(340px,calc(100vw-2rem))] rounded-2xl border bg-background p-4 text-foreground shadow-2xl transition-[top,left] duration-300"
            style:top="{tooltipPosition.top}px"
            style:left="{tooltipPosition.left}px"
        >
            {#if targetRect}
                <span
                    class="absolute left-1/2 size-4 -translate-x-1/2 rotate-45 border bg-background
                        {tooltipPosition.placement === 'below'
                            ? '-top-2 border-b-0 border-r-0'
                            : '-bottom-2 border-l-0 border-t-0'}"
                    aria-hidden="true"
                ></span>
            {/if}

            <div class="relative">
                <div class="mb-3 flex items-start justify-between gap-3">
                    <div>
                        <p class="text-xs font-medium uppercase tracking-wide text-primary">
                            Step {step + 1} of {steps.length}
                        </p>
                        <h2 class="mt-1 text-base font-semibold">{currentStep.title}</h2>
                    </div>
                    <Button variant="ghost" size="icon" class="size-11 shrink-0" onclick={onClose} aria-label="Close tutorial">
                        <X class="size-4" />
                    </Button>
                </div>

                <p class="text-sm leading-6 text-muted-foreground">{currentStep.body}</p>

                <div class="my-4 grid grid-cols-5 gap-1" aria-label="Tutorial progress">
                    {#each steps as _, index}
                        <span class="h-1.5 rounded-full {index <= step ? 'bg-primary' : 'bg-muted'}"></span>
                    {/each}
                </div>

                <div class="flex items-center justify-between gap-2">
                    <Button variant="ghost" onclick={onClose}>Skip</Button>
                    <div class="flex gap-2">
                        {#if step > 0}
                            <Button variant="outline" onclick={onBack}>Back</Button>
                        {/if}
                        <Button onclick={step < steps.length - 1 ? onNext : onClose}>
                            {step < steps.length - 1 ? "Next" : "Finish"}
                        </Button>
                    </div>
                </div>
            </div>
        </section>
    </div>
{/if}
