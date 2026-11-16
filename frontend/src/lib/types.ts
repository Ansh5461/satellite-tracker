export interface SatelliteSummary {
	norad_id: number;
	name: string;
	latitude: number;
	longitude: number;
	altitude_km: number;
	velocity_kms: number;
	period_min: number;
	epoch_age_h?: number;
	stale_warning?: boolean;
	bstar?: number;
}

export interface TrackPoint {
	timestamp: string;
	latitude: number;
	longitude: number;
	altitude_km: number;
	r_itrs_km?: [number, number, number];
	v_itrs_km_s?: [number, number, number];
}

export interface SatelliteTrackResponse {
	norad_id: number;
	name: string;
	elements: {
		inclination_deg: number;
		eccentricity: number;
		mean_motion_rev_per_day: number;
		epoch: string;
	};
	footprint_radius_km: number;
	past_track: TrackPoint[];
	future_track: TrackPoint[];
	epoch_age_h?: number;
	stale_warning?: boolean;
}

export interface PassEvent {
	aos: string;
	tca: string;
	los: string;
	max_elevation_deg: number;
	aos_azimuth_deg: number;
	los_azimuth_deg: number;
	tca_azimuth_deg: number;
	max_doppler_hz?: number | null;
	min_fspl_db?: number | null;
}

export interface PassCurvePoint {
	timestamp: string;
	azimuth_deg: number;
	elevation_deg: number;
	slant_range_km: number;
	range_rate_km_s: number;
	doppler_hz: number;
	rx_freq_mhz: number;
	fspl_db?: number;
	doppler_drift_hz_s?: number;
	elevation_apparent_deg?: number;
}

export interface PassResponse {
	norad_id: number;
	passes: PassEvent[];
	next_pass_curve: PassCurvePoint[];
}

export interface TelemetryMessage {
	timestamp: string;
	latitude: number;
	longitude: number;
	altitude_km: number;
	velocity_kms: number;
	azimuth_deg?: number;
	elevation_deg?: number;
	slant_range_km?: number;
	range_rate_km_s?: number;
	doppler_hz?: number;
	rx_freq_mhz?: number;
	eclipse_state?: string;
	fspl_db?: number;
}

export interface GroundStation {
	lat: number;
	lon: number;
	alt_m: number;
	freq_mhz: number;
}
