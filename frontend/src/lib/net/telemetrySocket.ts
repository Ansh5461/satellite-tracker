import type { TelemetryFrame } from '$lib/schemas/generated';

export type TelemetryHandlers = {
	onFrame?: (frame: TelemetryFrame) => void;
	onRaw?: (data: unknown) => void;
	onStatus?: (connected: boolean) => void;
};

export class TelemetrySocket {
	private ws: WebSocket | null = null;
	private lastDash = 0;

	constructor(
		private handlers: TelemetryHandlers,
		private dashHz = 2
	) {}

	connect(url: string) {
		this.close();
		this.ws = new WebSocket(url);
		this.ws.binaryType = 'arraybuffer';
		this.ws.onopen = () => this.handlers.onStatus?.(true);
		this.ws.onclose = () => this.handlers.onStatus?.(false);
		this.ws.onerror = () => this.handlers.onStatus?.(false);
		this.ws.onmessage = async (ev) => {
			let obj: unknown;
			try {
				if (ev.data instanceof ArrayBuffer) {
					const text = new TextDecoder().decode(ev.data);
					obj = JSON.parse(text);
				} else {
					obj = JSON.parse(String(ev.data));
				}
			} catch {
				return;
			}
			this.handlers.onRaw?.(obj);
			const frame = obj as TelemetryFrame;
			if (!frame?.satellite) return;
			// Always deliver to scene path
			this.handlers.onFrame?.(frame);
		};
	}

	/** Throttle helper for Svelte dashboard stores. */
	shouldUpdateDashboard(now = performance.now()): boolean {
		const minDt = 1000 / this.dashHz;
		if (now - this.lastDash >= minDt) {
			this.lastDash = now;
			return true;
		}
		return false;
	}

	close() {
		this.ws?.close();
		this.ws = null;
	}
}

export function buildTelemetryUrl(
	apiBase: string | undefined,
	norad: number,
	gs: { lat: number; lon: number; alt_m: number; freq_mhz: number }
): string {
	const q = new URLSearchParams({
		norad: String(norad),
		lat: String(gs.lat),
		lon: String(gs.lon),
		alt_m: String(gs.alt_m),
		freq_hz: String(gs.freq_mhz * 1e6)
	});
	if (apiBase) {
		const wsBase = apiBase.replace(/^http/, 'ws');
		return `${wsBase}/ws/v1/telemetry?${q}`;
	}
	const proto = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
	const host = typeof window !== 'undefined' ? window.location.host : '127.0.0.1:8000';
	return `${proto}://${host}/ws/v1/telemetry?${q}`;
}
