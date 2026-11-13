<script lang="ts">
	import type { PassEvent } from '$lib/types';

	interface Props {
		passes: PassEvent[];
		onSelectPass: (index: number) => void;
		selected: number;
	}

	let { passes, onSelectPass, selected }: Props = $props();

	function fmt(iso: string) {
		return new Date(iso).toLocaleString(undefined, {
			month: 'short',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
</script>

<div class="overflow-x-auto text-xs font-mono">
	<table class="w-full border-collapse">
		<thead>
			<tr class="text-mission-muted text-left border-b border-mission-border">
				<th class="py-1 pr-2">AOS</th>
				<th class="py-1 pr-2">TCA</th>
				<th class="py-1 pr-2">LOS</th>
				<th class="py-1">Max El</th>
			</tr>
		</thead>
		<tbody>
			{#each passes as pass, i}
				<tr
					class="cursor-pointer border-b border-mission-border/50 hover:bg-mission-panel
						{selected === i ? 'bg-mission-cyan/10' : ''}"
					onclick={() => onSelectPass(i)}
				>
					<td class="py-1 pr-2 tabular-nums">{fmt(pass.aos)}</td>
					<td class="py-1 pr-2 tabular-nums">{fmt(pass.tca)}</td>
					<td class="py-1 pr-2 tabular-nums">{fmt(pass.los)}</td>
					<td class="py-1 text-mission-amber tabular-nums">{pass.max_elevation_deg.toFixed(1)}°</td>
				</tr>
			{/each}
		</tbody>
	</table>
	{#if !passes.length}
		<p class="text-mission-muted py-2">No passes ≥10° in the next 24 h.</p>
	{/if}
</div>
