/**
 * Cubic Hermite dead-reckoning between server keyframes (r, v) in ITRS [km].
 * Basis: h00, h10, h01, h11 with tangent scaling by Δt.
 */

export type Keyframe = {
	t: number; // unix ms
	r: Float64Array; // length 3
	v: Float64Array; // length 3 km/s
};

const RING = 16;
const STRIDE = 1 + 3 + 3; // t + r + v

export class KeyframeBuffer {
	private buf = new Float64Array(RING * STRIDE);
	private head = 0;
	private count = 0;
	/** Render delay (ms) to absorb jitter (~1.5 ticks at 1 Hz). */
	delayMs = 1500;

	push(tMs: number, r: ArrayLike<number>, v: ArrayLike<number>) {
		const i = (this.head % RING) * STRIDE;
		this.buf[i] = tMs;
		this.buf[i + 1] = r[0];
		this.buf[i + 2] = r[1];
		this.buf[i + 3] = r[2];
		this.buf[i + 4] = v[0];
		this.buf[i + 5] = v[1];
		this.buf[i + 6] = v[2];
		this.head = (this.head + 1) % RING;
		this.count = Math.min(this.count + 1, RING);
	}

	private at(logical: number): Keyframe {
		const idx = ((this.head - this.count + logical + RING * 4) % RING) * STRIDE;
		return {
			t: this.buf[idx],
			r: this.buf.subarray(idx + 1, idx + 4),
			v: this.buf.subarray(idx + 4, idx + 7)
		};
	}

	sample(nowMs: number, out: Float64Array = new Float64Array(3)): Float64Array | null {
		if (this.count < 1) return null;
		const target = nowMs - this.delayMs;
		if (this.count === 1) {
			const k = this.at(0);
			out[0] = k.r[0];
			out[1] = k.r[1];
			out[2] = k.r[2];
			return out;
		}
		// Find bracketing keyframes
		let i0 = 0;
		for (let i = 0; i < this.count - 1; i++) {
			const a = this.at(i);
			const b = this.at(i + 1);
			if (a.t <= target && target <= b.t) {
				i0 = i;
				break;
			}
			if (target > b.t) i0 = i;
		}
		const k0 = this.at(i0);
		const k1 = this.at(Math.min(i0 + 1, this.count - 1));
		const dt = (k1.t - k0.t) / 1000; // seconds
		if (dt <= 1e-6) {
			out[0] = k1.r[0];
			out[1] = k1.r[1];
			out[2] = k1.r[2];
			return out;
		}
		let u = (target - k0.t) / (k1.t - k0.t);
		// Clamp extrapolation on packet loss
		u = Math.min(1.25, Math.max(0, u));
		const u2 = u * u;
		const u3 = u2 * u;
		const h00 = 2 * u3 - 3 * u2 + 1;
		const h10 = u3 - 2 * u2 + u;
		const h01 = -2 * u3 + 3 * u2;
		const h11 = u3 - u2;
		for (let c = 0; c < 3; c++) {
			const m0 = k0.v[c] * dt;
			const m1 = k1.v[c] * dt;
			out[c] = h00 * k0.r[c] + h10 * m0 + h01 * k1.r[c] + h11 * m1;
		}
		return out;
	}
}

export function hermite(
	r0: ArrayLike<number>,
	v0: ArrayLike<number>,
	r1: ArrayLike<number>,
	v1: ArrayLike<number>,
	u: number,
	dtSec: number,
	out: Float64Array
): Float64Array {
	const u2 = u * u;
	const u3 = u2 * u;
	const h00 = 2 * u3 - 3 * u2 + 1;
	const h10 = u3 - 2 * u2 + u;
	const h01 = -2 * u3 + 3 * u2;
	const h11 = u3 - u2;
	for (let c = 0; c < 3; c++) {
		out[c] = h00 * r0[c] + h10 * v0[c] * dtSec + h01 * r1[c] + h11 * v1[c] * dtSec;
	}
	return out;
}
