export type QueuedRequest = {
	id?: number;
	url: string;
	method: string;
	body: string | null;
	timestamp: number;
	retries: number;
};

const DB_NAME = "upscale-offline";
const DB_VERSION = 1;
const STORE_NAME = "requests";
const listeners = new Set<(count: number) => void>();

let dbPromise: Promise<IDBDatabase> | null = null;
let draining = false;

function isBrowser() {
	return typeof indexedDB !== "undefined";
}

function openDb(): Promise<IDBDatabase> {
	if (!isBrowser()) return Promise.reject(new Error("IndexedDB is unavailable"));
	if (dbPromise) return dbPromise;

	dbPromise = new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);
		request.onupgradeneeded = () => {
			const db = request.result;
			if (!db.objectStoreNames.contains(STORE_NAME)) {
				db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
			}
		};
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});

	return dbPromise;
}

async function withStore<T>(
	mode: IDBTransactionMode,
	callback: (store: IDBObjectStore) => IDBRequest<T> | void
): Promise<T | undefined> {
	const db = await openDb();
	return new Promise((resolve, reject) => {
		const tx = db.transaction(STORE_NAME, mode);
		const store = tx.objectStore(STORE_NAME);
		const request = callback(store);
		let result: T | undefined;

		if (request) {
			request.onsuccess = () => {
				result = request.result;
			};
			request.onerror = () => reject(request.error);
		}
		tx.oncomplete = () => resolve(result);
		tx.onerror = () => reject(tx.error);
	});
}

async function notifyQueueCount() {
	const count = await getQueuedRequestCount();
	for (const listener of listeners) listener(count);
}

export async function enqueueInvoiceRequest(request: QueuedRequest) {
	await withStore("readwrite", (store) => store.add(request));
	await notifyQueueCount();
}

export async function getQueuedRequests(): Promise<QueuedRequest[]> {
	const requests = await withStore<QueuedRequest[]>("readonly", (store) => store.getAll());
	return (requests ?? []).sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
}

export async function getQueuedRequestCount(): Promise<number> {
	const count = await withStore<number>("readonly", (store) => store.count());
	return count ?? 0;
}

async function updateQueuedRequest(request: QueuedRequest) {
	await withStore("readwrite", (store) => store.put(request));
	await notifyQueueCount();
}

async function removeQueuedRequest(id: number) {
	await withStore("readwrite", (store) => store.delete(id));
	await notifyQueueCount();
}

export function subscribeQueueCount(listener: (count: number) => void) {
	listeners.add(listener);
	getQueuedRequestCount().then(listener).catch(() => listener(0));
	return () => listeners.delete(listener);
}

export async function drainOfflineQueue(apiBase: string, token: string | null) {
	if (!isBrowser() || draining || !navigator.onLine) return;
	draining = true;
	try {
		const requests = await getQueuedRequests();
		for (const queued of requests) {
			if (!queued.id) continue;
			try {
				const response = await fetch(`${apiBase}${queued.url}`, {
					method: queued.method,
					headers: {
						"Content-Type": "application/json",
						...(token ? { Authorization: `Bearer ${token}` } : {}),
					},
					body: queued.body,
				});

				if (response.ok) {
					await removeQueuedRequest(queued.id);
					continue;
				}

				if (response.status >= 400 && response.status < 500) {
					await removeQueuedRequest(queued.id);
					continue;
				}

				await updateQueuedRequest({ ...queued, retries: queued.retries + 1 });
				break;
			} catch {
				await updateQueuedRequest({ ...queued, retries: queued.retries + 1 });
				break;
			}
		}
	} finally {
		draining = false;
		await notifyQueueCount();
	}
}
