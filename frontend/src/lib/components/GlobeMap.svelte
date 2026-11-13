<script lang="ts">
	import { onMount } from 'svelte';
	import type { SatelliteTrackResponse, TrackPoint } from '$lib/types';
	import { subsolarPoint } from '$lib/solar';

	interface Props {
		track: SatelliteTrackResponse | null;
		gsLat: number;
		gsLon: number;
		liveLat?: number;
		liveLon?: number;
		footprintKm?: number;
	}

	let { track, gsLat, gsLon, liveLat = 0, liveLon = 0, footprintKm = 0 }: Props = $props();

	let canvas: HTMLCanvasElement;
	let width = $state(800);
	let height = $state(420);

	function project(lat: number, lon: number, w: number, h: number) {
		const x = ((lon + 180) / 360) * w;
		const y = ((90 - lat) / 180) * h;
		return { x, y };
}

	function drawTerminator(ctx: CanvasRenderingContext2D, w: number, h: number, now: Date) {
		const sub = subsolarPoint(now);
		ctx.save();
		ctx.strokeStyle = 'rgba(251, 191, 36, 0.35)';
		ctx.lineWidth = 1;
		ctx.beginPath();
		for (let lon = -180; lon <= 180; lon += 2) {
			// Great circle ~90° from subsolar
			const lat =
				(Math.asin(
					Math.sin((sub.lat * Math.PI) / 180) * Math.cos(((lon - sub.lon) * Math.PI) / 180)
				) *
					180) /
				Math.PI;
			const p = project(lat, lon, w, h);
			if (lon === -180) ctx.moveTo(p.x, p.y);
			else ctx.lineTo(p.x, p.y);
		}
		ctx.stroke();
		ctx.restore();
	}

	function drawTrack(
		ctx: CanvasRenderingContext2D,
		pts: TrackPoint[],
		w: number,
		h: number,
		style: { dash: number[]; color: string; width: number }
	) {
		if (!pts.length) return;
		ctx.save();
		ctx.setLineDash(style.dash);
		ctx.strokeStyle = style.color;
		ctx.lineWidth = style.width;
		ctx.beginPath();
		pts.forEach((pt, i) => {
			const p = project(pt.latitude, pt.longitude, w, h);
			if (i === 0) ctx.moveTo(p.x, p.y);
			else ctx.lineTo(p.x, p.y);
		});
		ctx.stroke();
		ctx.restore();
	}

	function drawFootprint(
		ctx: CanvasRenderingContext2D,
		lat: number,
		lon: number,
		radiusKm: number,
		w: number,
		h: number
	) {
		const p = project(lat, lon, w, h);
		const kmPerDegLat = 111.32;
		const rPx = (radiusKm / kmPerDegLat / 180) * h * 2;
		ctx.save();
		ctx.strokeStyle = 'rgba(34, 211, 238, 0.35)';
		ctx.fillStyle = 'rgba(34, 211, 238, 0.08)';
		ctx.beginPath();
		ctx.arc(p.x, p.y, Math.max(rPx, 4), 0, Math.PI * 2);
		ctx.fill();
		ctx.stroke();
		ctx.restore();
	}

	function drawMarker(
		ctx: CanvasRenderingContext2D,
		lat: number,
		lon: number,
		w: number,
		h: number,
		color: string,
		size: number
	) {
		const p = project(lat, lon, w, h);
		ctx.save();
		ctx.fillStyle = color;
		ctx.beginPath();
		ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
		ctx.fill();
		ctx.strokeStyle = '#0f1522';
		ctx.lineWidth = 1;
		ctx.stroke();
		ctx.restore();
	}

	function render() {
		if (!canvas) return;
		const dpr = window.devicePixelRatio || 1;
		const rect = canvas.getBoundingClientRect();
		width = rect.width;
		height = rect.height;
		canvas.width = width * dpr;
		canvas.height = height * dpr;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.fillStyle = '#0a1020';
		ctx.fillRect(0, 0, width, height);

		// graticule
		ctx.strokeStyle = 'rgba(30, 42, 61, 0.9)';
		ctx.lineWidth = 1;
		for (let lon = -180; lon <= 180; lon += 30) {
			const x = ((lon + 180) / 360) * width;
			ctx.beginPath();
			ctx.moveTo(x, 0);
			ctx.lineTo(x, height);
			ctx.stroke();
		}
		for (let lat = -60; lat <= 60; lat += 30) {
			const y = ((90 - lat) / 180) * height;
			ctx.beginPath();
			ctx.moveTo(0, y);
			ctx.lineTo(width, y);
			ctx.stroke();
		}

		drawTerminator(ctx, width, height, new Date());

		if (track) {
			drawTrack(ctx, track.past_track, width, height, {
				dash: [4, 6],
				color: 'rgba(148, 163, 184, 0.7)',
				width: 1.5
			});
			drawTrack(ctx, track.future_track, width, height, {
				dash: [],
				color: '#22d3ee',
				width: 2
			});
		}

		const satLat = liveLat || track?.future_track[0]?.latitude || 0;
		const satLon = liveLon || track?.future_track[0]?.longitude || 0;
		const fp = footprintKm || track?.footprint_radius_km || 0;
		if (fp > 0) drawFootprint(ctx, satLat, satLon, fp, width, height);
		drawMarker(ctx, satLat, satLon, width, height, '#22d3ee', 5);
		drawMarker(ctx, gsLat, gsLon, width, height, '#fbbf24', 4);
	}

	onMount(() => {
		const ro = new ResizeObserver(() => render());
		ro.observe(canvas);
		const id = setInterval(render, 1000);
		return () => {
			ro.disconnect();
			clearInterval(id);
		};
	});

	$effect(() => {
		track;
		gsLat;
		gsLon;
		liveLat;
		liveLon;
		render();
	});
</script>

<div class="relative w-full h-full min-h-[320px] rounded border border-mission-border overflow-hidden">
	<canvas bind:this={canvas} class="w-full h-full block"></canvas>
	<div class="absolute top-2 left-2 text-[10px] font-mono text-mission-muted uppercase tracking-widest">
		Equirectangular · TEME→ECEF track
	</div>
</div>
