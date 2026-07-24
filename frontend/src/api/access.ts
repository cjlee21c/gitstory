// The shared class access code lives in localStorage and rides on every request
// as the X-Access-Code header (see client.ts). It's a gate credential the
// student possesses, not a secret — the backend is what enforces it.

const STORAGE_KEY = "accessCode";

// Dispatched by client.ts when a request comes back 401 so the AccessProvider
// can drop back to the code-entry screen.
export const UNAUTHORIZED_EVENT = "gitstory:unauthorized";

export function getAccessCode(): string {
  return localStorage.getItem(STORAGE_KEY) ?? "";
}

export function setAccessCode(code: string): void {
  localStorage.setItem(STORAGE_KEY, code);
}

export function clearAccessCode(): void {
  localStorage.removeItem(STORAGE_KEY);
}
