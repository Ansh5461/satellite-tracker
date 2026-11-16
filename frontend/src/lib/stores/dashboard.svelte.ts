import type {
	AttitudeSample,
	CatalogItem,
	ConjunctionAlert,
	EclipseEvent,
	ObserverGeometry,
	SatelliteState
} from '$lib/schemas/generated';

/** Throttled (~2 Hz) dashboard snapshots — never drive the render loop. */
class DashboardStore {
	satellite = $state<SatelliteState | null>(null);
	observer = $state<ObserverGeometry | null>(null);
	catalog = $state<CatalogItem[]>([]);
	eclipses = $state<EclipseEvent[]>([]);
	conjunctions = $state<ConjunctionAlert[]>([]);
	attitude = $state<AttitudeSample[]>([]);
	liveDopplerHz = $state<number | null>(null);
	liveFsplDb = $state<number | null>(null);
}

export const dashboard = new DashboardStore();
