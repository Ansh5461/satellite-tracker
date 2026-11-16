/** Contract stubs aligned with backend Pydantic schemas. */
export interface SatelliteState {
	norad_id: number;
	name: string;
	timestamp: string;
	r_teme_km: [number, number, number];
	v_teme_km_s: [number, number, number];
	r_itrs_km: [number, number, number];
	v_itrs_km_s: [number, number, number];
	latitude_deg: number;
	longitude_deg: number;
	altitude_km: number;
	velocity_km_s: number;
	eclipse_state: string;
	shadow_function: number;
}

export interface ObserverGeometry {
	azimuth_deg: number;
	elevation_deg: number;
	elevation_apparent_deg: number;
	slant_range_km: number;
	range_rate_km_s: number;
	doppler_hz: number;
	doppler_drift_hz_s: number;
	fspl_db: number;
	rx_freq_hz: number;
}

export interface TelemetryFrame {
	timestamp: string;
	tick_id: number;
	satellite: SatelliteState;
	observer: ObserverGeometry | null;
	degraded_iers: boolean;
}

export interface CatalogItem {
	norad_id: number;
	name: string;
	epoch_iso: string;
	epoch_age_h: number;
	stale_warning: boolean;
	bstar: number;
	bstar_trend: number | null;
	inclination_deg: number;
	eccentricity: number;
	mean_motion_rev_per_day: number;
}

export interface ConjunctionAlert {
	primary_norad: number;
	secondary_norad: number;
	tca: string;
	miss_distance_km: number;
	relative_speed_km_s: number;
	screening_radius_km: number;
}

export interface EclipseEvent {
	entry: string;
	exit: string;
	kind: string;
	duration_s: number;
}

export interface AttitudeSample {
	t_s: number;
	q_body_inertial: [number, number, number, number];
	omega_body_rad_s: [number, number, number];
	solar_power_w: number;
	polarization_loss_db: number;
}
