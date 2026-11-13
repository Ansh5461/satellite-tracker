import { PUBLIC_API_URL } from '$env/static/public';
import type { PassResponse, SatelliteSummary, SatelliteTrackResponse } from './types';

const API_BASE = PUBLIC_API_URL ?? '';

export async function fetchSatellites(): Promise<SatelliteSummary[]> {
	const res = await fetch(`${API_BASE}/api/satellites`);
	if (!res.ok) throw new Error('Failed to load satellites');
	return res.json();
}

export async function fetchTrack(noradId: number): Promise<SatelliteTrackResponse> {
	const res = await fetch(`${API_BASE}/api/satellite/${noradId}/track`);
	if (!res.ok) throw new Error('Failed to load track');
	return res.json();
}

export async function fetchPasses(body: {
	norad_id: number;
	lat: number;
	lon: number;
	alt_m: number;
	freq_mhz: number;
}): Promise<PassResponse> {
	const res = await fetch(`${API_BASE}/api/passes`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!res.ok) throw new Error('Failed to predict passes');
	return res.json();
}

export function telemetryWsUrl(
	noradId: number,
	gs: { lat: number; lon: number; alt_m: number; freq_mhz: number }
): string {
	const proto = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
	const host = typeof window !== 'undefined' ? window.location.host : '127.0.0.1:8000';
	const q = new URLSearchParams({
		lat: String(gs.lat),
		lon: String(gs.lon),
		alt_m: String(gs.alt_m),
		freq_mhz: String(gs.freq_mhz)
	});
	const base = PUBLIC_API_URL;
	if (base) {
		const wsBase = base.replace(/^http/, 'ws');
		return `${wsBase}/ws/telemetry/${noradId}?${q}`;
	}
	if (typeof window !== 'undefined') {
		return `${proto}://${host}/ws/telemetry/${noradId}?${q}`;
	}
	return `ws://127.0.0.1:8000/ws/telemetry/${noradId}?${q}`;
}
