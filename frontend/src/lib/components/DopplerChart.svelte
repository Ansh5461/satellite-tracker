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

	function decimate<T>(arr: T[], max = 400): T[] {
		if (arr.length <= max) return arr;
		const step = Math.ceil(arr.length / max);
		return arr.filter((_, i) => i % step === 0);
	}

	function build() {
		if (!canvasEl) return;
		chart?.destroy();
		const pts = decimate(points);
		const elev = decimate(elevationPoints.length ? elevationPoints : points);
		if (!pts.length) return;
		const t0 = new Date(pts[0].timestamp).getTime();
		const labels = pts.map((p) => (new Date(p.timestamp).getTime() - t0) / 60000);
		const hasFspl = pts.some((p) => p.fspl_db != null);
		chart = new Chart(canvasEl, {
			type: 'line',
			data: {
				labels,
				datasets: [
					{
						label: 'Δf (kHz)',
						data: pts.map((p) => p.doppler_hz / 1000),
						borderColor: '#fbbf24',
						backgroundColor: 'rgba(251,191,36,0.1)',
						yAxisID: 'y',
						tension: 0.2,
						pointRadius: 0
					},
					{
						label: 'Elevation °',
						data: elev.map((p) => p.elevation_deg),
						borderColor: '#22d3ee',
						yAxisID: 'y1',
						tension: 0.2,
						pointRadius: 0
					},
					...(hasFspl
						? [
								{
									label: 'FSPL (dB)',
									data: pts.map((p) => p.fspl_db ?? null),
									borderColor: '#a78bfa',
									yAxisID: 'y2',
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
				plugins: { legend: { labels: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } } } },
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
						ticks: { color: '#22d3ee' },
						grid: { drawOnChartArea: false }
					},
					y2: {
						position: 'right',
						display: hasFspl,
						ticks: { color: '#a78bfa' },
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
