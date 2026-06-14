import { writable, derived } from "svelte/store";

interface User {
    id: number;
    email: string;
    business_name: string;
    business_address?: string | null;
    tin?: string | null;
    vat_status: string;
    sells_meat: boolean;
    sells_retail: boolean;
    onboarding_completed: boolean;
}

function createAuthStore() {
    const { subscribe, set, update } = writable<User | null>(null);

    return {
        subscribe,
        set,
        login(user: User, token: string) {
            localStorage.setItem("access_token", token);
            set(user);
        },
        logout() {
            localStorage.removeItem("access_token");
            set(null);
        },
        update,
    };
}

export const auth = createAuthStore();
export const isAuthenticated = derived(auth, ($auth) => $auth !== null);