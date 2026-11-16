<script lang="ts">
	import type { TelemetryMessage } from '$lib/types';

	interface Props {
		telemetry: TelemetryMessage | null;
		connected: boolean;
	}

	let { telemetry, connected }: Props = $props();

	const rows = $derived(
		telemetry
			? [
					['Lat', telemetry.latitude.toFixed(4) + '°'],
					['Lon', telemetry.longitude.toFixed(4) + '°'],
					['Alt', telemetry.altitude_km.toFixed(2) + ' km'],
					['Vel', telemetry.velocity_kms.toFixed(3) + ' km/s'],
					['Az', telemetry.azimuth_deg?.toFixed(1) ?? '—', '°'],
					['El', telemetry.elevation_deg?.toFixed(1) ?? '—', '°'],
					['Range', telemetry.slant_range_km?.toFixed(0) ?? '—', ' km'],
					['Δf', telemetry.doppler_hz ? (telemetry.doppler_hz / 1000).toFixed(2) + ' kHz' : '—'],
					['Rx', telemetry.rx_freq_mhz?.toFixed(5) ?? '—', ' MHz']
				]
			: []
	);
</script>

<div class="font-mono text-sm">
	<div class="flex items-center gap-2 mb-2">
		<span
			class="inline-block w-2 h-2 rounded-full {connected ? 'bg-emerald-400' : 'bg-red-500'}"
		></span>
		<span class="text-xs uppercase tracking-widest text-mission-muted">Live telemetry</span>
	</div>
	{#if !telemetry}
		<p class="text-mission-muted text-xs">
			{connected ? 'Connected — waiting for ticker frames…' : 'Awaiting WebSocket…'}
		</p>
	{:else}
		<dl class="grid grid-cols-2 gap-x-3 gap-y-1 tabular-nums">
			{#each rows as row}
				<dt class="text-mission-muted text-xs">{row[0]}</dt>
				<dd class="text-mission-cyan text-right">{row[1]}</dd>
			{/each}
		</dl>
	{/if}
</div>
