/** Sub-solar point (approximate) for day/night terminator. */
export function subsolarPoint(date: Date): { lat: number; lon: number } {
	// getTime() is already UTC ms — do not apply local timezone offset again.
	const jd = date.getTime() / 86400000 + 2440587.5;
	const n = jd - 2451545.0;
	const L = (((280.466 + 0.9856474 * n) % 360) + 360) % 360;
	const g = ((((357.528 + 0.9856003 * n) % 360) + 360) % 360) * (Math.PI / 180);
	const lambda =
		(L + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * (Math.PI / 180);
	const epsilon = 23.439 * (Math.PI / 180);
	const decl = Math.asin(Math.sin(epsilon) * Math.sin(lambda));
	const ra = Math.atan2(Math.cos(epsilon) * Math.sin(lambda), Math.cos(lambda));
	// GMST in degrees
	let gmst = ((18.697374558 + 24.06570982441908 * n) % 24) * 15;
	gmst = ((gmst % 360) + 360) % 360;
	const lat = (decl * 180) / Math.PI;
	let lon = (ra * 180) / Math.PI - gmst;
	lon = ((((lon + 180) % 360) + 360) % 360) - 180;
	return { lat, lon };
}
