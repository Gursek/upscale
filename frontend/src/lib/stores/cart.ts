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
    stock_quantity: number;
}

function createCartStore() {
    const { subscribe, update, set } = writable<CartItem[]>([]);

    return {
        subscribe,
        addItem(product: any, quantity: number): { added: boolean; quantity: number; available: number } {
            let result = { added: false, quantity: 0, available: Number(product.stock_quantity) };
            update((items) => {
                const existing = items.find((i) => i.product_id === product.id);
                const available = Number(product.stock_quantity);
                const requested = product.pricing_type === "fixed" && existing
                    ? existing.quantity + quantity
                    : quantity;
                if (requested > available) {
                    result = { added: false, quantity: existing?.quantity ?? 0, available };
                    return items;
                }
                if (existing) {
                    const line_total = Number((existing.unit_cost * requested).toFixed(2));
                    result = { added: true, quantity: requested, available };
                    return items.map((item) => item.product_id === product.id
                        ? {
                            ...item,
                            quantity: requested,
                            stock_quantity: available,
                            line_total,
                        }
                        : item
                    );
                }
                result = { added: true, quantity, available };
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
                        stock_quantity: available,
                    },
                ];
            });
            return result;
        },
        setQuantity(product_id: number, quantity: number): boolean {
            let changed = false;
            update((items) => items.map((item) => {
                if (item.product_id !== product_id) return item;
                if (quantity <= 0) {
                    changed = true;
                    return { ...item, quantity: 0 };
                }
                if (quantity > item.stock_quantity) return item;
                changed = true;
                return {
                    ...item,
                    quantity,
                    line_total: Number((item.unit_cost * quantity).toFixed(2)),
                };
            }).filter((item) => item.quantity > 0));
            return changed;
        },
        syncStock(products: any[]) {
            update((items) => items.map((item) => {
                const product = products.find((candidate) => candidate.id === item.product_id);
                if (!product) return item;
                const stock = Number(product.stock_quantity);
                const quantity = Math.min(item.quantity, stock);
                return {
                    ...item,
                    stock_quantity: stock,
                    quantity,
                    line_total: Number((item.unit_cost * quantity).toFixed(2)),
                };
            }).filter((item) => item.quantity > 0));
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

export const cartCount = derived(cart, ($cart) =>
    $cart.reduce((sum, item) => sum + item.quantity, 0)
);
