<script lang="ts">
	import type { EclipseEvent } from '$lib/schemas/generated';

	interface Props {
		events: EclipseEvent[];
	}
	let { events }: Props = $props();
</script>

<div class="space-y-1 max-h-40 overflow-auto text-xs font-mono">
	{#if !events.length}
		<p class="text-mission-muted">No eclipse events in window.</p>
	{:else}
		{#each events as e}
			<div class="flex items-center gap-2 border-b border-mission-border/50 py-1">
				<span
					class="w-2 h-2 rounded-full {e.kind === 'umbra' ? 'bg-indigo-400' : 'bg-amber-300'}"
				></span>
				<span class="uppercase text-mission-muted w-16">{e.kind}</span>
				<span class="truncate">{new Date(e.entry).toISOString().slice(11, 19)} → {new Date(e.exit).toISOString().slice(11, 19)}</span>
				<span class="text-mission-muted ml-auto">{e.duration_s.toFixed(0)}s</span>
			</div>
		{/each}
	{/if}
</div>
