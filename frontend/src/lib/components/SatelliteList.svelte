<script lang="ts">
	import type { SatelliteSummary } from '$lib/types';

	interface Props {
		satellites: SatelliteSummary[];
		selectedId: number | null;
		onSelect: (id: number) => void;
	}

	let { satellites, selectedId, onSelect }: Props = $props();
	let query = $state('');

	const filtered = $derived(
		satellites.filter(
			(s) =>
				s.name.toLowerCase().includes(query.toLowerCase()) ||
				String(s.norad_id).includes(query)
		)
	);
</script>

<div class="flex flex-col gap-2 h-full">
	<input
		class="w-full bg-mission-bg border border-mission-border rounded px-2 py-1.5 text-sm font-mono focus:outline-none focus:border-mission-cyan"
		placeholder="Search NORAD / name…"
		bind:value={query}
	/>
	<ul class="flex-1 overflow-y-auto space-y-1 text-sm">
		{#each filtered as sat (sat.norad_id)}
			<li>
				<button
					type="button"
					class="w-full text-left px-2 py-1.5 rounded border tabular-nums transition-colors
						{selectedId === sat.norad_id
						? 'border-mission-cyan bg-mission-cyan/10'
						: 'border-transparent hover:border-mission-border hover:bg-mission-panel'}"
					onclick={() => onSelect(sat.norad_id)}
				>
					<div class="font-medium truncate">{sat.name}</div>
					<div class="text-xs text-mission-muted font-mono">
						{sat.norad_id} · {sat.altitude_km.toFixed(1)} km · {sat.velocity_kms.toFixed(2)} km/s
					</div>
				</button>
			</li>
		{/each}
	</ul>
</div>
