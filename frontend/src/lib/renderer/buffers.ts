/** Pre-allocated typed-array helpers for ground tracks / footprints. */

export function ensureFloat32(buf: Float32Array | null, n: number): Float32Array {
	if (buf && buf.length >= n) return buf;
	return new Float32Array(Math.max(n, 64));
}

export function latLonToXYZ(latDeg: number, lonDeg: number, radius: number, out: Float32Array, offset = 0) {
	const lat = (latDeg * Math.PI) / 180;
	const lon = (lonDeg * Math.PI) / 180;
	const cl = Math.cos(lat);
	out[offset] = radius * cl * Math.cos(lon);
	out[offset + 1] = radius * Math.sin(lat);
	out[offset + 2] = radius * cl * Math.sin(lon);
}

export function itrsKmToScene(r_itrs_km: ArrayLike<number>, scale: number, out: Float32Array, offset = 0) {
	// Three.js Y-up: map ITRS Z→Y, Y→Z
	out[offset] = r_itrs_km[0] * scale;
	out[offset + 1] = r_itrs_km[2] * scale;
	out[offset + 2] = r_itrs_km[1] * scale;
}
