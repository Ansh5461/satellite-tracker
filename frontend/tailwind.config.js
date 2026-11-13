/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				mission: {
					bg: '#090D16',
					panel: '#0f1522',
					border: '#1e2a3d',
					cyan: '#22d3ee',
					amber: '#fbbf24',
					muted: '#64748b'
				}
			},
			fontFamily: {
				mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace']
			}
		}
	},
	plugins: []
};
