/** Sub-solar point (approximate) for day/night terminator. */
export function subsolarPoint(date: Date): { lat: number; lon: number } {
	const jd =
		date.getTime() / 86400000 +
		2440587.5 -
		(date.getTimezoneOffset() * 60000) / 86400000;
	const n = jd - 2451545.0;
	const L = (280.466 + 0.9856474 * n) % 360;
	const g = ((357.528 + 0.9856003 * n) % 360) * (Math.PI / 180);
	const lambda = (L + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * (Math.PI / 180);
	const epsilon = 23.439 * (Math.PI / 180);
	const decl = Math.asin(Math.sin(epsilon) * Math.sin(lambda));
	const gmst =
		((18.697374558 + 24.06570982441908 * n) % 24) * 15 * (Math.PI / 180);
	const lat = (decl * 180) / Math.PI;
	let lon = (gmst * 180) / Math.PI - 180;
	if (lon > 180) lon -= 360;
	if (lon < -180) lon += 360;
	return { lat, lon };
}
