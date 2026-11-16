<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { SceneController } from '$lib/renderer/SceneController';
	import { subsolarPoint } from '$lib/solar';
	import type { SatelliteTrackResponse } from '$lib/types';
	import type { TelemetryFrame } from '$lib/schemas/generated';
	import GeometryWorker from '$lib/workers/geometry.worker?worker';

	interface Props {
		track: SatelliteTrackResponse | null;
		gsLat: number;
		gsLon: number;
		frame: TelemetryFrame | null;
	}

	let { track, gsLat, gsLon, frame }: Props = $props();

	let canvas: HTMLCanvasElement;
	let controller: SceneController | null = null;
	let worker: Worker | null = null;
	let reqId = 0;
	let ro: ResizeObserver | null = null;
	let sunTimer: ReturnType<typeof setInterval> | null = null;

	function pushFrame(f: TelemetryFrame) {
		if (!controller) return;
		const t = Date.parse(f.timestamp);
		controller.pushKeyframe(t, f.satellite.r_itrs_km, f.satellite.v_itrs_km_s);
	}

	function seedFromTrack() {
		if (!controller || !track) return;
		const live = track.future_track[0] ?? track.past_track.at(-1);
		if (!live) return;
		if (live.r_itrs_km) {
			controller.setSatelliteITRS(live.r_itrs_km);
			const t = Date.parse(live.timestamp);
			const v = live.v_itrs_km_s ?? [0, 0, 0];
			controller.pushKeyframe(t, live.r_itrs_km, v);
		}
	}

	function updateTracks() {
		if (!controller || !track || !worker) return;
		seedFromTrack();
		const id = ++reqId;
		const past = track.past_track.map((p) => ({ lat: p.latitude, lon: p.longitude }));
		const future = track.future_track.map((p) => ({ lat: p.latitude, lon: p.longitude }));
		worker.postMessage({ type: 'split_track', id, points: past });
		worker.postMessage({ type: 'split_track', id: id + 100000, points: future });
		const live = track.future_track[0];
		if (live) {
			worker.postMessage({
				type: 'footprint',
				id: id + 200000,
				lat: live.latitude,
				lon: live.longitude,
				altitude_km: live.altitude_km,
				min_elevation_deg: 0
			});
		}
	}

	onMount(() => {
		controller = new SceneController(canvas);
		controller.mount();
		controller.setGroundStation(gsLat, gsLon);
		const applySun = () => {
			const sub = subsolarPoint(new Date());
			controller?.setSunFromSubsolar(sub.lat, sub.lon);
		};
		applySun();
		sunTimer = setInterval(applySun, 60_000);

		worker = new GeometryWorker();
		let pastSeg: Float32Array[] = [];
		let futSeg: Float32Array[] = [];
		worker.onmessage = (ev) => {
			const msg = ev.data;
			if (msg.type === 'split_track') {
				if (msg.id >= 100000 && msg.id < 200000) {
					futSeg = msg.segments;
				} else {
					pastSeg = msg.segments;
				}
				controller?.setTracks(track?.past_track || [], track?.future_track || [], pastSeg, futSeg);
			} else if (msg.type === 'footprint') {
				controller?.setFootprintXYZ(msg.xyz);
			}
		};

		ro = new ResizeObserver(() => controller?.resize());
		ro.observe(canvas.parentElement || canvas);
		// Layout often settles after first paint — remeasure so the globe isn't clipped.
		requestAnimationFrame(() => {
			controller?.resize();
			updateTracks();
		});
		setTimeout(() => controller?.resize(), 100);
		updateTracks();
	});

	onDestroy(() => {
		if (sunTimer) clearInterval(sunTimer);
		ro?.disconnect();
		worker?.terminate();
		controller?.dispose();
		controller = null;
	});

	$effect(() => {
		gsLat;
		gsLon;
		controller?.setGroundStation(gsLat, gsLon);
	});

	$effect(() => {
		track;
		updateTracks();
	});

	$effect(() => {
		if (frame) pushFrame(frame);
	});
</script>

<div class="relative w-full h-[min(56vh,560px)] min-h-[360px] rounded border border-mission-border overflow-hidden bg-[#050a14]">
	<canvas bind:this={canvas} class="w-full h-full block"></canvas>
	<div class="absolute top-2 left-2 text-[10px] font-mono text-mission-muted uppercase tracking-widest">
		Blue Marble · drag to orbit · Hermite · TEME→ITRS
	</div>
</div>
