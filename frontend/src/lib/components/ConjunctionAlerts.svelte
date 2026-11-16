<script lang="ts">
	import type { ConjunctionAlert } from '$lib/schemas/generated';

	interface Props {
		alerts: ConjunctionAlert[];
	}
	let { alerts }: Props = $props();
</script>

<div class="space-y-1 max-h-40 overflow-auto text-xs font-mono">
	{#if !alerts.length}
		<p class="text-mission-muted">No conjunctions within screening radius.</p>
	{:else}
		{#each alerts as a}
			<div class="border border-rose-500/40 bg-rose-950/30 rounded px-2 py-1">
				<div class="text-rose-300">{a.primary_norad} ↔ {a.secondary_norad}</div>
				<div class="text-mission-muted">
					TCA {new Date(a.tca).toISOString().slice(0, 19)}Z · miss {a.miss_distance_km.toFixed(2)} km ·
					{a.relative_speed_km_s.toFixed(2)} km/s
				</div>
			</div>
		{/each}
	{/if}
</div>
