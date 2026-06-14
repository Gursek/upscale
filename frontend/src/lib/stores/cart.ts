import { writable, derived } from "svelte/store";

export interface CartItem {
    product_id: number;
    name: string;
    category: string;
    pricing_type: string;  // 'per_kg' or 'fixed'
    unit: string;
    unit_cost: number;
    quantity: number;
    line_total: number;
}

function createCartStore() {
    const { subscribe, update, set } = writable<CartItem[]>([]);

    return {
        subscribe,
        addItem(product: any, quantity: number) {
            update((items) => {
                const existing = items.find((i) => i.product_id === product.id);
                if (existing) {
                    existing.quantity = quantity;
                    existing.line_total = Number((existing.unit_cost * quantity).toFixed(2));
                    return [...items];
                }
                return [
                    ...items,
                    {
                        product_id: product.id,
                        name: product.name + (product.cut_type ? ` (${product.cut_type})` : ""),
                        category: product.category,
                        pricing_type: product.pricing_type,
                        unit: product.unit,
                        unit_cost: product.price,
                        quantity,
                        line_total: Number((product.price * quantity).toFixed(2)),
                    },
                ];
            });
        },
        removeItem(product_id: number) {
            update((items) => items.filter((i) => i.product_id !== product_id));
        },
        clear() {
            set([]);
        },
    };
}

export const cart = createCartStore();

export const cartTotal = derived(cart, ($cart) =>
    Number($cart.reduce((sum, item) => sum + item.line_total, 0).toFixed(2))
);

export const cartCount = derived(cart, ($cart) => $cart.length);