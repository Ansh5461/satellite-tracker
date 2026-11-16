/// <reference lib="webworker" />
import type { GeometryRequest, GeometryResponse } from './protocol';
import { filterPassWindow, horizonFootprint, splitAntiMeridian } from './geometryMath';

self.onmessage = (ev: MessageEvent<GeometryRequest>) => {
	const msg = ev.data;
	if (msg.type === 'split_track') {
		const segments = splitAntiMeridian(msg.points, msg.radius ?? 1.001);
		const transfer = segments.map((s) => s.buffer);
		const res: GeometryResponse = { type: 'split_track', id: msg.id, segments };
		(self as DedicatedWorkerGlobalScope).postMessage(res, transfer);
	} else if (msg.type === 'footprint') {
		const xyz = horizonFootprint(
			msg.lat,
			msg.lon,
			msg.altitude_km,
			msg.min_elevation_deg ?? 0,
			msg.n ?? 128
		);
		const res: GeometryResponse = { type: 'footprint', id: msg.id, xyz };
		(self as DedicatedWorkerGlobalScope).postMessage(res, [xyz.buffer]);
	} else if (msg.type === 'filter_pass_window') {
		const indices = filterPassWindow(msg.points, msg.min_elevation_deg);
		const res: GeometryResponse = { type: 'filter_pass_window', id: msg.id, indices };
		(self as DedicatedWorkerGlobalScope).postMessage(res, [indices.buffer]);
	}
};
