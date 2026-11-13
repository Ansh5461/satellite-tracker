<script lang="ts">
	import type { PassCurvePoint } from '$lib/types';

	interface Props {
		points: PassCurvePoint[];
		width?: number;
		height?: number;
	}

	let { points, width = 220, height = 220 }: Props = $props();

	function pol(rEl: number, az: number, cx: number, cy: number, R: number) {
		const elRad = (rEl * Math.PI) / 180;
		const r = R * (1 - elRad / (Math.PI / 2));
		const azRad = ((az - 90) * Math.PI) / 180;
		return { x: cx + r * Math.cos(azRad), y: cy + r * Math.sin(azRad) };
	}
</script>

<svg {width} {height} class="bg-mission-panel rounded border border-mission-border">
	{#if points.length}
		{@const cx = width / 2}
		{@const cy = height / 2}
		{@const R = Math.min(width, height) * 0.42}
		{#each [90, 60, 30, 0] as el}
			<circle
				cx={cx}
				cy={cy}
				r={R * (1 - el / 90)}
				fill="none"
				stroke="rgba(100,116,139,0.35)"
				stroke-width="1"
			/>
		{/each}
		<text x={cx} y={12} fill="#64748b" font-size="9" text-anchor="middle">N</text>
		<polyline
			fill="none"
			stroke="#22d3ee"
			stroke-width="1.5"
			points={points
				.map((p) => {
					const pt = pol(p.elevation_deg, p.azimuth_deg, cx, cy, R);
					return `${pt.x},${pt.y}`;
				})
				.join(' ')}
		/>
	{:else}
		<text x="50%" y="50%" fill="#64748b" font-size="11" text-anchor="middle" dy=".3em">
			No pass curve
		</text>
	{/if}
</svg>
