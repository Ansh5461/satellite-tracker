import { describe, expect, it } from 'vitest';
import { filterPassWindow, horizonFootprint, splitAntiMeridian } from './geometryMath';

describe('splitAntiMeridian', () => {
	it('splits when longitude jumps across ±180', () => {
		const pts = [
			{ lat: 10, lon: 170 },
			{ lat: 10, lon: 179 },
			{ lat: 10, lon: -179 },
			{ lat: 10, lon: -170 }
		];
		const segs = splitAntiMeridian(pts);
		expect(segs.length).toBeGreaterThanOrEqual(2);
	});

	it('keeps a single segment without wrap', () => {
		const pts = [
			{ lat: 0, lon: 0 },
			{ lat: 1, lon: 10 },
			{ lat: 2, lon: 20 }
		];
		const segs = splitAntiMeridian(pts);
		expect(segs.length).toBe(1);
		expect(segs[0].length).toBe(9);
	});
});

describe('horizonFootprint', () => {
	it('returns closed ring', () => {
		const xyz = horizonFootprint(0, 0, 500, 0, 32);
		expect(xyz.length).toBe(33 * 3);
		expect(xyz[0]).toBeCloseTo(xyz[xyz.length - 3], 5);
	});
});

describe('filterPassWindow', () => {
	it('filters by elevation', () => {
		const idx = filterPassWindow(
			[
				{ lat: 0, lon: 0, elevation_deg: 5 },
				{ lat: 0, lon: 1, elevation_deg: 15 },
				{ lat: 0, lon: 2, elevation_deg: 20 }
			],
			10
		);
		expect(Array.from(idx)).toEqual([1, 2]);
	});
});
