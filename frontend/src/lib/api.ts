import { PUBLIC_API_URL } from '$env/static/public';
import type { PassResponse, SatelliteSummary, SatelliteTrackResponse } from './types';
import type { AttitudeSample, CatalogItem, ConjunctionAlert, EclipseEvent } from './schemas/generated';
import { buildTelemetryUrl } from './net/telemetrySocket';

const API_BASE = PUBLIC_API_URL ?? '';

async function getJson<T>(path: string): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`);
	if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
	return res.json();
}

export async function fetchSatellites(): Promise<SatelliteSummary[]> {
	try {
		return await getJson('/api/v1/satellites');
	} catch {
		return getJson('/api/satellites');
	}
}

export async function fetchCatalog(): Promise<CatalogItem[]> {
	const res = await getJson<{ satellites: CatalogItem[] }>('/api/v1/catalog');
	return res.satellites;
}

export async function fetchTrack(noradId: number): Promise<SatelliteTrackResponse> {
	try {
		const t = await getJson<any>(`/api/v1/satellites/${noradId}/track`);
		// Normalize to legacy TrackPoint shape used by components
		return {
			norad_id: t.norad_id,
			name: t.name,
			elements: {
				inclination_deg: 0,
				eccentricity: 0,
				mean_motion_rev_per_day: 0,
				epoch: t.epoch_iso
			},
			footprint_radius_km: t.footprint_radius_km,
			past_track: (t.past_track || []).map((p: any) => ({
				timestamp: p.timestamp,
				latitude: p.latitude_deg ?? p.latitude,
				longitude: p.longitude_deg ?? p.longitude,
				altitude_km: p.altitude_km,
				r_itrs_km: p.r_itrs_km,
				v_itrs_km_s: p.v_itrs_km_s
			})),
			future_track: (t.future_track || []).map((p: any) => ({
				timestamp: p.timestamp,
				latitude: p.latitude_deg ?? p.latitude,
				longitude: p.longitude_deg ?? p.longitude,
				altitude_km: p.altitude_km,
				r_itrs_km: p.r_itrs_km,
				v_itrs_km_s: p.v_itrs_km_s
			})),
			epoch_age_h: t.epoch_age_h,
			stale_warning: t.stale_warning
		};
	} catch {
		return getJson(`/api/satellite/${noradId}/track`);
	}
}

export async function fetchPasses(body: {
	norad_id: number;
	lat: number;
	lon: number;
	alt_m: number;
	freq_mhz: number;
}): Promise<PassResponse> {
	const res = await fetch(`${API_BASE}/api/v1/passes`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			norad_id: body.norad_id,
			lat_deg: body.lat,
			lon_deg: body.lon,
			alt_m: body.alt_m,
			freq_hz: body.freq_mhz * 1e6
		})
	});
	if (!res.ok) {
		// legacy fallback
		const legacy = await fetch(`${API_BASE}/api/passes`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		if (!legacy.ok) throw new Error('Failed to predict passes');
		return legacy.json();
	}
	const data = await res.json();
	return {
		norad_id: data.norad_id,
		passes: data.passes,
		next_pass_curve: (data.next_pass_curve || []).map((c: any) => ({
			timestamp: c.timestamp,
			azimuth_deg: c.azimuth_deg,
			elevation_deg: c.elevation_deg,
			slant_range_km: c.slant_range_km,
			range_rate_km_s: c.range_rate_km_s,
			doppler_hz: c.doppler_hz,
			rx_freq_mhz: (c.rx_freq_hz ?? 0) / 1e6,
			fspl_db: c.fspl_db,
			doppler_drift_hz_s: c.doppler_drift_hz_s,
			elevation_apparent_deg: c.elevation_apparent_deg
		}))
	};
}

export async function fetchEclipses(noradId: number): Promise<EclipseEvent[]> {
	const res = await getJson<{ events: EclipseEvent[] }>(`/api/v1/satellites/${noradId}/eclipses`);
	return res.events;
}

export async function fetchConjunctions(): Promise<ConjunctionAlert[]> {
	const res = await getJson<{ alerts: ConjunctionAlert[] }>('/api/v1/conjunctions');
	return res.alerts;
}

export async function fetchAttitude(): Promise<AttitudeSample[]> {
	const res = await fetch(`${API_BASE}/api/v1/attitude/simulate`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({})
	});
	if (!res.ok) throw new Error('attitude sim failed');
	const data = await res.json();
	return data.samples;
}

export function telemetryWsUrl(
	noradId: number,
	gs: { lat: number; lon: number; alt_m: number; freq_mhz: number }
): string {
	return buildTelemetryUrl(PUBLIC_API_URL, noradId, gs);
}
