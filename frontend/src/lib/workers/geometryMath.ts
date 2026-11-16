import type { TrackPointMsg } from './protocol';

const R_EARTH_KM = 6378.137;

function latLonToXYZ(latDeg: number, lonDeg: number, radius: number, out: Float32Array, o: number) {
	const lat = (latDeg * Math.PI) / 180;
	const lon = (lonDeg * Math.PI) / 180;
	const cl = Math.cos(lat);
	out[o] = radius * cl * Math.cos(lon);
	out[o + 1] = radius * Math.sin(lat);
	out[o + 2] = radius * cl * Math.sin(lon);
}

/** Split ground track when |Δλ| > 180°, interpolating crossing latitude to ±180. */
export function splitAntiMeridian(points: TrackPointMsg[], radius = 1.001): Float32Array[] {
	if (!points.length) return [];
	const segments: Float32Array[] = [];
	let cur: number[] = [];

	const pushPt = (lat: number, lon: number) => {
		const o = cur.length;
		cur.length += 3;
		const tmp = new Float32Array(3);
		latLonToXYZ(lat, lon, radius, tmp, 0);
		cur[o] = tmp[0];
		cur[o + 1] = tmp[1];
		cur[o + 2] = tmp[2];
	};

	pushPt(points[0].lat, points[0].lon);
	for (let i = 1; i < points.length; i++) {
		const a = points[i - 1];
		const b = points[i];
		const dLon = b.lon - a.lon;
		if (Math.abs(dLon) > 180) {
			const dir = dLon > 0 ? -1 : 1;
			const lonEdgeA = dir > 0 ? 180 : -180;
			const lonEdgeB = -lonEdgeA;
			const t = (lonEdgeA - a.lon) / (b.lon - a.lon - Math.sign(dLon) * 360);
			const latCross = a.lat + t * (b.lat - a.lat);
			pushPt(latCross, lonEdgeA);
			segments.push(new Float32Array(cur));
			cur = [];
			pushPt(latCross, lonEdgeB);
			pushPt(b.lat, b.lon);
		} else {
			pushPt(b.lat, b.lon);
		}
	}
	if (cur.length) segments.push(new Float32Array(cur));
	return segments;
}

export function horizonFootprint(
	lat: number,
	lon: number,
	altitude_km: number,
	min_elevation_deg = 0,
	n = 128
): Float32Array {
	const eps = (min_elevation_deg * Math.PI) / 180;
	const ratio = R_EARTH_KM / (R_EARTH_KM + Math.max(altitude_km, 1));
	const arg = Math.min(1, Math.max(-1, ratio * Math.cos(eps)));
	const lambda0 = Math.acos(arg) - eps;
	const out = new Float32Array((n + 1) * 3);
	const lat0 = (lat * Math.PI) / 180;
	const lon0 = (lon * Math.PI) / 180;
	for (let i = 0; i <= n; i++) {
		const az = (2 * Math.PI * i) / n;
		const lat2 = Math.asin(
			Math.sin(lat0) * Math.cos(lambda0) + Math.cos(lat0) * Math.sin(lambda0) * Math.cos(az)
		);
		const lon2 =
			lon0 +
			Math.atan2(
				Math.sin(az) * Math.sin(lambda0) * Math.cos(lat0),
				Math.cos(lambda0) - Math.sin(lat0) * Math.sin(lat2)
			);
		latLonToXYZ((lat2 * 180) / Math.PI, (lon2 * 180) / Math.PI, 1.002, out, i * 3);
	}
	return out;
}

export function filterPassWindow(
	points: Array<TrackPointMsg & { elevation_deg?: number }>,
	min_elevation_deg: number
): Uint32Array {
	const idx: number[] = [];
	for (let i = 0; i < points.length; i++) {
		const el = points[i].elevation_deg;
		if (el === undefined || el >= min_elevation_deg) idx.push(i);
	}
	return Uint32Array.from(idx);
}
