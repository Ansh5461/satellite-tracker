export type TrackPointMsg = { lat: number; lon: number };

export type GeometryRequest =
	| {
			type: 'split_track';
			id: number;
			points: TrackPointMsg[];
			radius?: number;
	  }
	| {
			type: 'footprint';
			id: number;
			lat: number;
			lon: number;
			altitude_km: number;
			min_elevation_deg?: number;
			n?: number;
	  }
	| {
			type: 'filter_pass_window';
			id: number;
			points: Array<TrackPointMsg & { t?: number; elevation_deg?: number }>;
			min_elevation_deg: number;
	  };

export type GeometryResponse =
	| { type: 'split_track'; id: number; segments: Float32Array[] }
	| { type: 'footprint'; id: number; xyz: Float32Array }
	| {
			type: 'filter_pass_window';
			id: number;
			indices: Uint32Array;
	  };
