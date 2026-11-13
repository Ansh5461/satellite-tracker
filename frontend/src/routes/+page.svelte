<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { fetchPasses, fetchSatellites, fetchTrack, telemetryWsUrl } from '$lib/api';
	import type {
		GroundStation,
		PassCurvePoint,
		PassEvent,
		SatelliteSummary,
		SatelliteTrackResponse,
		TelemetryMessage
	} from '$lib/types';
	import GlobeMap from '$lib/components/GlobeMap.svelte';
	import SatelliteList from '$lib/components/SatelliteList.svelte';
	import GroundStationPanel from '$lib/components/GroundStationPanel.svelte';
	import TelemetryPanel from '$lib/components/TelemetryPanel.svelte';
	import PassTable from '$lib/components/PassTable.svelte';
	import Skyplot from '$lib/components/Skyplot.svelte';
	import DopplerChart from '$lib/components/DopplerChart.svelte';

	let satellites = $state<SatelliteSummary[]>([]);
	let selectedId = $state<number | null>(null);
	let track = $state<SatelliteTrackResponse | null>(null);
	let passes = $state<PassEvent[]>([]);
	let curve = $state<PassCurvePoint[]>([]);
	let selectedPass = $state(0);
	let gs = $state<GroundStation>({ lat: 28.6139, lon: 77.209, alt_m: 216, freq_mhz: 137.1 });
	let telemetry = $state<TelemetryMessage | null>(null);
	let wsConnected = $state(false);
	let ws: WebSocket | null = null;
	let trackTimer: ReturnType<typeof setInterval> | null = null;

	async function loadSatellites() {
		satellites = await fetchSatellites();
		if (!selectedId && satellites.length) {
			const iss = satellites.find((s) => s.norad_id === 25544) ?? satellites[0];
			await selectSatellite(iss.norad_id);
		}
	}

	async function selectSatellite(id: number) {
		selectedId = id;
		track = await fetchTrack(id);
		await refreshPasses();
		connectWs();
	}

	async function refreshPasses() {
		if (!selectedId) return;
		const res = await fetchPasses({
			norad_id: selectedId,
			lat: gs.lat,
			lon: gs.lon,
			alt_m: gs.alt_m,
			freq_mhz: gs.freq_mhz
		});
		passes = res.passes;
		curve = res.next_pass_curve;
		selectedPass = 0;
	}

	function onGsChange(next: GroundStation) {
		gs = next;
		refreshPasses();
		connectWs();
	}

	function connectWs() {
		ws?.close();
		if (!selectedId) return;
		const url = telemetryWsUrl(selectedId, gs);
		ws = new WebSocket(url);
		ws.onopen = () => (wsConnected = true);
		ws.onclose = () => (wsConnected = false);
		ws.onmessage = (ev) => {
			telemetry = JSON.parse(ev.data) as TelemetryMessage;
		};
	}

	onMount(() => {
		loadSatellites().catch(console.error);
		trackTimer = setInterval(() => {
			if (selectedId) fetchTrack(selectedId).then((t) => (track = t)).catch(() => {});
		}, 30000);
	});

	onDestroy(() => {
		ws?.close();
		if (trackTimer) clearInterval(trackTimer);
	});
</script>

<div class="grid grid-cols-1 xl:grid-cols-12 gap-3 max-w-[1600px] mx-auto">
	<aside class="xl:col-span-3 space-y-3">
		<section class="bg-mission-panel border border-mission-border rounded p-3 h-64">
			<h2 class="text-xs uppercase tracking-widest text-mission-muted mb-2">Assets</h2>
			<SatelliteList {satellites} {selectedId} onSelect={selectSatellite} />
		</section>
		<section class="bg-mission-panel border border-mission-border rounded p-3">
			<GroundStationPanel {gs} onChange={onGsChange} />
		</section>
		<section class="bg-mission-panel border border-mission-border rounded p-3">
			<TelemetryPanel {telemetry} connected={wsConnected} />
		</section>
	</aside>

	<section class="xl:col-span-6 flex flex-col gap-3 min-h-[420px]">
		<div class="flex-1 bg-mission-panel border border-mission-border rounded p-2 min-h-[360px]">
			<GlobeMap
				{track}
				gsLat={gs.lat}
				gsLon={gs.lon}
				liveLat={telemetry?.latitude}
				liveLon={telemetry?.longitude}
				footprintKm={track?.footprint_radius_km}
			/>
		</div>
		{#if track}
			<div class="text-xs font-mono text-mission-muted grid grid-cols-3 gap-2 px-1">
				<span>Incl {track.elements.inclination_deg.toFixed(2)}°</span>
				<span>e {track.elements.eccentricity.toFixed(6)}</span>
				<span>MM {track.elements.mean_motion_rev_per_day.toFixed(4)} rev/d</span>
			</div>
		{/if}
	</section>

	<aside class="xl:col-span-3 space-y-3">
		<section class="bg-mission-panel border border-mission-border rounded p-3">
			<h2 class="text-xs uppercase tracking-widest text-mission-muted mb-2">24h passes ≥10°</h2>
			<PassTable {passes} selected={selectedPass} onSelectPass={(i) => (selectedPass = i)} />
		</section>
		<section class="bg-mission-panel border border-mission-border rounded p-3 flex flex-col items-center gap-2">
			<h2 class="text-xs uppercase tracking-widest text-mission-muted w-full">Polar skyplot</h2>
			<Skyplot points={curve} />
		</section>
		<section class="bg-mission-panel border border-mission-border rounded p-3">
			<h2 class="text-xs uppercase tracking-widest text-mission-muted mb-2">Doppler & elevation</h2>
			<DopplerChart points={curve} elevationPoints={curve} />
		</section>
	</aside>
</div>
