<script lang="ts">
	interface Props {
		epochAgeH?: number | null;
		staleWarning?: boolean;
		bstar?: number | null;
	}
	let { epochAgeH = null, staleWarning = false, bstar = null }: Props = $props();
</script>

<div class="flex flex-wrap gap-2 text-[10px] font-mono">
	{#if epochAgeH != null}
		<span
			class="px-2 py-0.5 rounded border {staleWarning
				? 'border-amber-500 text-amber-300'
				: 'border-mission-border text-mission-muted'}"
		>
			Epoch age {epochAgeH.toFixed(1)} h
			{#if staleWarning}⚠{/if}
		</span>
	{/if}
	{#if bstar != null}
		<span class="px-2 py-0.5 rounded border border-mission-border text-mission-muted">
			B* {bstar.toExponential(2)}
		</span>
	{/if}
</div>
