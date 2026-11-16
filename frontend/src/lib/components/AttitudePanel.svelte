<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { AttitudeViewer } from '$lib/renderer/AttitudeViewer';
	import type { AttitudeSample } from '$lib/schemas/generated';

	interface Props {
		samples: AttitudeSample[];
	}
	let { samples }: Props = $props();

	let canvas: HTMLCanvasElement;
	let viewer: AttitudeViewer | null = null;
	let idx = $state(0);
	let timer: ReturnType<typeof setInterval> | null = null;

	onMount(() => {
		viewer = new AttitudeViewer(canvas);
		viewer.resize();
		viewer.mount();
		timer = setInterval(() => {
			if (!samples.length || !viewer) return;
			idx = (idx + 1) % samples.length;
			const q = samples[idx].q_body_inertial;
			viewer.setQuaternion(q[0], q[1], q[2], q[3]);
		}, 100);
		const ro = new ResizeObserver(() => viewer?.resize());
		ro.observe(canvas);
		return () => ro.disconnect();
	});

	onDestroy(() => {
		if (timer) clearInterval(timer);
		viewer?.dispose();
	});

	$effect(() => {
		samples;
		idx = 0;
	});
</script>

<div class="space-y-2">
	<canvas bind:this={canvas} class="w-full h-40 rounded border border-mission-border bg-black/40"></canvas>
	{#if samples.length}
		{@const s = samples[Math.min(idx, samples.length - 1)]}
		<div class="text-[10px] font-mono text-mission-muted grid grid-cols-2 gap-1">
			<span>P {s.solar_power_w.toFixed(2)} W</span>
			<span>Pol {s.polarization_loss_db.toFixed(1)} dB</span>
			<span>ω {s.omega_body_rad_s.map((x: number) => x.toFixed(2)).join(',')}</span>
			<span>t {s.t_s.toFixed(1)} s</span>
		</div>
	{/if}
</div>
