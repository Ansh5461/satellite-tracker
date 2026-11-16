<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import {
		fetchAttitude,
		fetchConjunctions,
		fetchEclipses,
		fetchPasses,
		fetchSatellites,
		fetchTrack,
		telemetryWsUrl
	} from '$lib/api';
	import type {
		GroundStation,
		PassCurvePoint,
		PassEvent,
		SatelliteSummary,
		SatelliteTrackResponse,
		TelemetryMessage
	} from '$lib/types';
	import type { TelemetryFrame } from '$lib/schemas/generated';
	import { TelemetrySocket } from '$lib/net/telemetrySocket';
	import { dashboard } from '$lib/stores/dashboard.svelte';
	import Globe3D from '$lib/components/Globe3D.svelte';
	import SatelliteList from '$lib/components/SatelliteList.svelte';
	import GroundStationPanel from '$lib/components/GroundStationPanel.svelte';
	import TelemetryPanel from '$lib/components/TelemetryPanel.svelte';
	import PassTable from '$lib/components/PassTable.svelte';
	import Skyplot from '$lib/components/Skyplot.svelte';
	import DopplerChart from '$lib/components/DopplerChart.svelte';
	import EclipseTimeline from '$lib/components/EclipseTimeline.svelte';
	import ConjunctionAlerts from '$lib/components/ConjunctionAlerts.svelte';
	import AttitudePanel from '$lib/components/AttitudePanel.svelte';
	import EpochBadge from '$lib/components/EpochBadge.svelte';

	let satellites = $state<SatelliteSummary[]>([]);
	let selectedId = $state<number | null>(null);
	let track = $state<SatelliteTrackResponse | null>(null);
	let passes = $state<PassEvent[]>([]);
	let curve = $state<PassCurvePoint[]>([]);
	let selectedPass = $state(0);
	let gs = $state<GroundStation>({ lat: 28.6139, lon: 77.209, alt_m: 216, freq_mhz: 137.1 });
	let telemetry = $state<TelemetryMessage | null>(null);
	let liveFrame = $state<TelemetryFrame | null>(null);
	let wsConnected = $state(false);
	let sock: TelemetrySocket | null = null;
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
		connectWs();
		try {
			track = await fetchTrack(id);
		} catch (err) {
			console.error('track fetch failed', err);
		}
		refreshPasses().catch((err) => console.error('passes failed', err));
		fetchEclipses(id)
			.then((e) => (dashboard.eclipses = e))
			.catch(() => {});
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
		sock?.close();
		if (!selectedId) return;
		sock = new TelemetrySocket({
			onStatus: (c) => (wsConnected = c),
			onFrame: (frame) => {
				liveFrame = frame;
				if (sock?.shouldUpdateDashboard()) {
					dashboard.satellite = frame.satellite;
					dashboard.observer = frame.observer;
					dashboard.liveDopplerHz = frame.observer?.doppler_hz ?? null;
					dashboard.liveFsplDb = frame.observer?.fspl_db ?? null;
					telemetry = {
						timestamp: frame.timestamp,
						latitude: frame.satellite.latitude_deg,
						longitude: frame.satellite.longitude_deg,
						altitude_km: frame.satellite.altitude_km,
						velocity_kms: frame.satellite.velocity_km_s,
						azimuth_deg: frame.observer?.azimuth_deg,
						elevation_deg: frame.observer?.elevation_deg,
						slant_range_km: frame.observer?.slant_range_km,
						range_rate_km_s: frame.observer?.range_rate_km_s,
						doppler_hz: frame.observer?.doppler_hz,
						rx_freq_mhz: frame.observer ? frame.observer.rx_freq_hz / 1e6 : undefined,
						eclipse_state: frame.satellite.eclipse_state,
						fspl_db: frame.observer?.fspl_db
					};
				}
			},
			onRaw: (obj: any) => {
				// Legacy TelemetryMessage shape fallback
				if (obj && typeof obj.latitude === 'number' && !obj.satellite) {
					telemetry = obj as TelemetryMessage;
				}
			}
		});
		sock.connect(telemetryWsUrl(selectedId, gs));
	}

	onMount(() => {
		loadSatellites().catch(console.error);
		fetchConjunctions()
			.then((a) => (dashboard.conjunctions = a))
			.catch(() => {});
		fetchAttitude()
			.then((s) => (dashboard.attitude = s))
			.catch(() => {});
		trackTimer = setInterval(() => {
			if (selectedId) fetchTrack(selectedId).then((t) => (track = t)).catch(() => {});
		}, 30000);
	});

	onDestroy(() => {
		sock?.close();
		if (trackTimer) clearInterval(trackTimer);
	});

	const selectedSat = $derived(satellites.find((s) => s.norad_id === selectedId) ?? null);
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
			<div class="mt-2">
				<EpochBadge
					epochAgeH={track?.epoch_age_h ?? selectedSat?.epoch_age_h}
					staleWarning={track?.stale_warning ?? selectedSat?.stale_warning}
					bstar={selectedSat?.bstar}
				/>
			</div>
		</section>
	</aside>

	<section class="xl:col-span-6 flex flex-col gap-3 min-h-[420px]">
		<div class="flex-1 bg-mission-panel border border-mission-border rounded p-2 min-h-[360px]">
			<Globe3D {track} gsLat={gs.lat} gsLon={gs.lon} frame={liveFrame} />
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
			<section class="bg-mission-panel border border-mission-border rounded p-3">
				<h2 class="text-xs uppercase tracking-widest text-mission-muted mb-2">Eclipse timeline</h2>
				<EclipseTimeline events={dashboard.eclipses} />
			</section>
			<section class="bg-mission-panel border border-mission-border rounded p-3">
				<h2 class="text-xs uppercase tracking-widest text-mission-muted mb-2">Conjunction alerts</h2>
				<ConjunctionAlerts alerts={dashboard.conjunctions} />
			</section>
		</div>
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
			<h2 class="text-xs uppercase tracking-widest text-mission-muted mb-2">Doppler · El · FSPL</h2>
			<DopplerChart points={curve} elevationPoints={curve} />
		</section>
		<section class="bg-mission-panel border border-mission-border rounded p-3">
			<h2 class="text-xs uppercase tracking-widest text-mission-muted mb-2">CubeSat attitude</h2>
			<AttitudePanel samples={dashboard.attitude} />
		</section>
	</aside>
</div>
