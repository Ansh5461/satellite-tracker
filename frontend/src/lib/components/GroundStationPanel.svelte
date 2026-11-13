<script lang="ts">
	import type { GroundStation } from '$lib/types';

	interface Props {
		gs: GroundStation;
		onChange: (gs: GroundStation) => void;
	}

	let { gs, onChange }: Props = $props();

	function geoLocate() {
		if (!navigator.geolocation) return;
		navigator.geolocation.getCurrentPosition((pos) => {
			onChange({
				...gs,
				lat: pos.coords.latitude,
				lon: pos.coords.longitude,
				alt_m: pos.coords.altitude ?? 0
			});
		});
	}
</script>

<div class="space-y-3 text-sm font-mono">
	<div class="flex items-center justify-between">
		<h3 class="text-mission-cyan text-xs uppercase tracking-widest">Ground Station</h3>
		<button
			type="button"
			class="text-xs text-mission-amber hover:underline"
			onclick={geoLocate}
		>
			Auto GPS
		</button>
	</div>
	<label class="block">
		<span class="text-mission-muted text-xs">Latitude °</span>
		<input
			type="number"
			step="0.0001"
			class="w-full mt-0.5 bg-mission-bg border border-mission-border rounded px-2 py-1 tabular-nums"
			value={gs.lat}
			oninput={(e) => onChange({ ...gs, lat: parseFloat(e.currentTarget.value) || 0 })}
		/>
	</label>
	<label class="block">
		<span class="text-mission-muted text-xs">Longitude °</span>
		<input
			type="number"
			step="0.0001"
			class="w-full mt-0.5 bg-mission-bg border border-mission-border rounded px-2 py-1 tabular-nums"
			value={gs.lon}
			oninput={(e) => onChange({ ...gs, lon: parseFloat(e.currentTarget.value) || 0 })}
		/>
	</label>
	<label class="block">
		<span class="text-mission-muted text-xs">Altitude m</span>
		<input
			type="number"
			class="w-full mt-0.5 bg-mission-bg border border-mission-border rounded px-2 py-1 tabular-nums"
			value={gs.alt_m}
			oninput={(e) => onChange({ ...gs, alt_m: parseFloat(e.currentTarget.value) || 0 })}
		/>
	</label>
	<label class="block">
		<span class="text-mission-muted text-xs">Downlink MHz</span>
		<input
			type="number"
			step="0.0001"
			class="w-full mt-0.5 bg-mission-bg border border-mission-border rounded px-2 py-1 tabular-nums"
			value={gs.freq_mhz}
			oninput={(e) => onChange({ ...gs, freq_mhz: parseFloat(e.currentTarget.value) || 137.1 })}
		/>
	</label>
</div>
