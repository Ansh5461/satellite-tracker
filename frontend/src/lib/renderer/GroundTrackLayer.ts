import * as THREE from 'three';
import { ensureFloat32, latLonToXYZ } from './buffers';

const EARTH_R = 1;

export class GroundTrackLayer {
	readonly group = new THREE.Group();
	private pastLine: THREE.Line;
	private futureLine: THREE.Line;
	private pastPos: Float32Array | null = null;
	private futurePos: Float32Array | null = null;
	private pastGeo: THREE.BufferGeometry;
	private futureGeo: THREE.BufferGeometry;

	constructor() {
		this.pastGeo = new THREE.BufferGeometry();
		this.futureGeo = new THREE.BufferGeometry();
		this.pastLine = new THREE.Line(
			this.pastGeo,
			new THREE.LineBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.7 })
		);
		this.futureLine = new THREE.Line(
			this.futureGeo,
			new THREE.LineBasicMaterial({ color: 0x22d3ee })
		);
		this.group.add(this.pastLine, this.futureLine);
	}

	setTracks(
		past: Array<{ latitude_deg?: number; longitude_deg?: number; latitude?: number; longitude?: number }>,
		future: Array<{ latitude_deg?: number; longitude_deg?: number; latitude?: number; longitude?: number }>,
		segmentsPast: Float32Array[],
		segmentsFuture: Float32Array[]
	) {
		this.applySegments(this.pastGeo, segmentsPast.length ? segmentsPast : this.project(past), true);
		this.applySegments(
			this.futureGeo,
			segmentsFuture.length ? segmentsFuture : this.project(future),
			false
		);
	}

	private project(
		pts: Array<{ latitude_deg?: number; longitude_deg?: number; latitude?: number; longitude?: number }>
	): Float32Array[] {
		if (!pts.length) return [];
		const arr = ensureFloat32(null, pts.length * 3);
		for (let i = 0; i < pts.length; i++) {
			const lat = pts[i].latitude_deg ?? pts[i].latitude ?? 0;
			const lon = pts[i].longitude_deg ?? pts[i].longitude ?? 0;
			latLonToXYZ(lat, lon, EARTH_R * 1.001, arr, i * 3);
		}
		return [arr.subarray(0, pts.length * 3)];
	}

	private applySegments(geo: THREE.BufferGeometry, segments: Float32Array[], past: boolean) {
		// Merge segments with NaN breaks for Line
		let total = 0;
		for (const s of segments) total += s.length + 3; // +NaN sentinel
		const buf = ensureFloat32(past ? this.pastPos : this.futurePos, total);
		if (past) this.pastPos = buf;
		else this.futurePos = buf;
		let o = 0;
		for (const s of segments) {
			buf.set(s, o);
			o += s.length;
			if (o + 3 <= buf.length) {
				buf[o] = buf[o + 1] = buf[o + 2] = NaN;
				o += 3;
			}
		}
		const attr = new THREE.BufferAttribute(buf.subarray(0, o), 3);
		attr.setUsage(THREE.DynamicDrawUsage);
		geo.setAttribute('position', attr);
		geo.setDrawRange(0, o / 3);
		geo.computeBoundingSphere();
	}

	dispose() {
		this.pastGeo.dispose();
		this.futureGeo.dispose();
		(this.pastLine.material as THREE.Material).dispose();
		(this.futureLine.material as THREE.Material).dispose();
	}
}
