<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<div class="min-h-screen flex flex-col">
	<header
		class="border-b border-mission-border bg-mission-panel/80 backdrop-blur px-4 py-3 flex items-center justify-between"
	>
		<div>
			<h1 class="text-lg font-semibold tracking-tight text-slate-100">GP Visualiser</h1>
			<p class="text-xs text-mission-muted font-mono">LEO telemetry · SGP4 · pass predictor</p>
		</div>
		<span class="text-[10px] uppercase tracking-[0.2em] text-mission-cyan font-mono">Mission Control</span>
	</header>
	<main class="flex-1 p-3 md:p-4">{@render children()}</main>
</div>
