import type { GroundStation } from '$lib/types';

/** Session-level UI state (Svelte 5 runes module). */
class SessionStore {
	selectedId = $state<number | null>(null);
	gs = $state<GroundStation>({ lat: 28.6139, lon: 77.209, alt_m: 216, freq_mhz: 137.1 });
	wsConnected = $state(false);
	degradedIers = $state(false);
}

export const session = new SessionStore();
