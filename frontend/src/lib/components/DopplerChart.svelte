<script lang="ts">
	import { onDestroy } from 'svelte';
	import Chart from 'chart.js/auto';
	import type { PassCurvePoint } from '$lib/types';

	interface Props {
		points: PassCurvePoint[];
		elevationPoints?: PassCurvePoint[];
	}

	let { points, elevationPoints = [] }: Props = $props();

	let canvasEl: HTMLCanvasElement;
	let chart: Chart | null = null;

	function build() {
		if (!canvasEl) return;
		chart?.destroy();
		if (!points.length) return;
		const t0 = new Date(points[0].timestamp).getTime();
		const labels = points.map((p) => (new Date(p.timestamp).getTime() - t0) / 60000);
		chart = new Chart(canvasEl, {
			type: 'line',
			data: {
				labels,
				datasets: [
					{
						label: 'Δf (kHz)',
						data: points.map((p) => p.doppler_hz / 1000),
						borderColor: '#fbbf24',
						backgroundColor: 'rgba(251,191,36,0.1)',
						yAxisID: 'y',
						tension: 0.2,
						pointRadius: 0
					},
					...(elevationPoints.length
						? [
								{
									label: 'Elevation °',
									data: elevationPoints.map((p) => p.elevation_deg),
									borderColor: '#22d3ee',
									yAxisID: 'y1',
									tension: 0.2,
									pointRadius: 0
								}
							]
						: [])
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { labels: { color: '#94a3b8', font: { family: 'JetBrains Mono' } } } },
				scales: {
					x: {
						title: { display: true, text: 'min from AOS', color: '#64748b' },
						ticks: { color: '#64748b' },
						grid: { color: 'rgba(30,42,61,0.8)' }
					},
					y: {
						position: 'left',
						ticks: { color: '#fbbf24' },
						grid: { color: 'rgba(30,42,61,0.8)' }
					},
					y1: {
						position: 'right',
						display: elevationPoints.length > 0,
						ticks: { color: '#22d3ee' },
						grid: { drawOnChartArea: false }
					}
				}
			}
		});
	}

	$effect(() => {
		points;
		elevationPoints;
		build();
	});

	onDestroy(() => chart?.destroy());
</script>

<div class="h-48 w-full relative">
	<canvas bind:this={canvasEl}></canvas>
</div>
