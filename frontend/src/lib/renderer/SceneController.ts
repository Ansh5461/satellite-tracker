/**
 * Imperative 60 FPS scene controller — NOT stored in Svelte runes/stores.
 *
 * Earth: Blue Marble Phong globe (GlobeLayer) + directional sun + ambient.
 * Satellites: Hermite dead-reckon between 1 Hz ITRS keyframes.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { KeyframeBuffer } from './hermite';
import { GlobeLayer } from './GlobeLayer';
import { GroundTrackLayer } from './GroundTrackLayer';
import { itrsKmToScene } from './buffers';

const SCALE = 1 / 6378.137; // km → Earth radii

export class SceneController {
	private renderer: THREE.WebGLRenderer;
	private scene = new THREE.Scene();
	private camera: THREE.PerspectiveCamera;
	private controls: OrbitControls;
	private globe: GlobeLayer;
	private tracks = new GroundTrackLayer();
	private satMesh: THREE.Mesh;
	private gsMesh: THREE.Mesh;
	private footprint: THREE.Line;
	private sunLight: THREE.DirectionalLight;
	private ambient: THREE.AmbientLight;
	private raf = 0;
	private running = false;
	private keyframes = new KeyframeBuffer();
	private tmp = new Float64Array(3);
	private tmp3 = new Float32Array(3);
	private sunDir = new THREE.Vector3(1, 0.35, 0.4);
	private lastT = 0;
	private userSteering = false;
	private onFrame: ((t: number) => void) | null = null;

	constructor(private canvas: HTMLCanvasElement) {
		this.renderer = new THREE.WebGLRenderer({
			canvas,
			antialias: true,
			alpha: false,
			preserveDrawingBuffer: true
		});
		this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
		this.renderer.outputColorSpace = THREE.SRGBColorSpace;
		this.renderer.toneMapping = THREE.NoToneMapping;
		this.renderer.setClearColor(0x030712, 1);

		this.camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100);
		this.camera.position.set(0, 0.12, 3.05);
		this.camera.lookAt(0, 0, 0);

		this.controls = new OrbitControls(this.camera, this.canvas);
		this.controls.enableDamping = true;
		this.controls.dampingFactor = 0.06;
		this.controls.minDistance = 1.45;
		this.controls.maxDistance = 6;
		this.controls.enablePan = false;
		this.controls.rotateSpeed = 0.55;
		this.controls.addEventListener('start', () => {
			this.userSteering = true;
		});

		const maxAniso = this.renderer.capabilities.getMaxAnisotropy();
		this.globe = new GlobeLayer(Math.min(maxAniso, 8));
		this.globe.addTo(this.scene);
		this.scene.add(this.tracks.group);

		// Strong fill so Blue Marble day map always reads; sun adds terminator.
		this.ambient = new THREE.AmbientLight(0xffffff, 1.15);
		this.sunLight = new THREE.DirectionalLight(0xfff5e6, 2.8);
		this.sunLight.position.copy(this.sunDir).multiplyScalar(5);
		this.scene.add(this.ambient, this.sunLight);

		// Sparse star field (points) — keeps space from reading as empty void
		this.scene.add(this.makeStars());

		this.satMesh = new THREE.Mesh(
			new THREE.SphereGeometry(0.018, 16, 12),
			new THREE.MeshBasicMaterial({ color: 0x22d3ee })
		);
		this.gsMesh = new THREE.Mesh(
			new THREE.SphereGeometry(0.014, 12, 10),
			new THREE.MeshBasicMaterial({ color: 0xfbbf24 })
		);
		this.footprint = new THREE.Line(
			new THREE.BufferGeometry(),
			new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.45 })
		);
		this.scene.add(this.satMesh, this.gsMesh, this.footprint);
		this.resize();
	}

	private makeStars() {
		const n = 1200;
		const pos = new Float32Array(n * 3);
		for (let i = 0; i < n; i++) {
			const r = 8 + Math.random() * 20;
			const u = Math.random();
			const v = Math.random();
			const theta = 2 * Math.PI * u;
			const phi = Math.acos(2 * v - 1);
			pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
			pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
			pos[i * 3 + 2] = r * Math.cos(phi);
		}
		const geo = new THREE.BufferGeometry();
		geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
		return new THREE.Points(
			geo,
			new THREE.PointsMaterial({ color: 0xb8c4d8, size: 0.015, sizeAttenuation: true })
		);
	}

	mount() {
		if (this.running) return;
		this.running = true;
		this.lastT = performance.now();
		const loop = (t: number) => {
			this.raf = requestAnimationFrame(loop);
			this.render(t);
			this.onFrame?.(t);
		};
		this.raf = requestAnimationFrame(loop);
	}

	dispose() {
		this.running = false;
		cancelAnimationFrame(this.raf);
		this.globe.dispose();
		this.tracks.dispose();
		this.satMesh.geometry.dispose();
		(this.satMesh.material as THREE.Material).dispose();
		this.gsMesh.geometry.dispose();
		(this.gsMesh.material as THREE.Material).dispose();
		this.footprint.geometry.dispose();
		(this.footprint.material as THREE.Material).dispose();
		this.renderer.dispose();
	}

	resize() {
		const parent = this.canvas.parentElement;
		const w = Math.max(parent?.clientWidth || this.canvas.clientWidth || 800, 1);
		const h = Math.max(parent?.clientHeight || this.canvas.clientHeight || 420, 1);
		this.canvas.style.width = `${w}px`;
		this.canvas.style.height = `${h}px`;
		this.renderer.setSize(w, h, false);
		this.camera.aspect = w / h;
		this.camera.updateProjectionMatrix();
	}

	pushKeyframe(tMs: number, r_itrs_km: ArrayLike<number>, v_itrs_km_s: ArrayLike<number>) {
		this.keyframes.push(tMs, r_itrs_km, v_itrs_km_s);
	}

	setSatelliteITRS(r_itrs_km: ArrayLike<number>) {
		itrsKmToScene(r_itrs_km, SCALE, this.tmp3);
		this.satMesh.position.set(this.tmp3[0], this.tmp3[1], this.tmp3[2]);
	}

	setGroundStation(lat: number, lon: number) {
		const latR = (lat * Math.PI) / 180;
		const lonR = (lon * Math.PI) / 180;
		const cl = Math.cos(latR);
		this.gsMesh.position.set(1.002 * cl * Math.cos(lonR), 1.002 * Math.sin(latR), 1.002 * cl * Math.sin(lonR));
	}

	setTracks(past: any[], future: any[], segPast: Float32Array[] = [], segFuture: Float32Array[] = []) {
		this.tracks.setTracks(past, future, segPast, segFuture);
	}

	setFootprintXYZ(xyz: Float32Array) {
		const geo = this.footprint.geometry as THREE.BufferGeometry;
		const attr = new THREE.BufferAttribute(xyz, 3);
		attr.setUsage(THREE.DynamicDrawUsage);
		geo.setAttribute('position', attr);
		geo.setDrawRange(0, xyz.length / 3);
		geo.computeBoundingSphere();
	}

	setSunFromSubsolar(lat: number, lon: number) {
		const latR = (lat * Math.PI) / 180;
		const lonR = (lon * Math.PI) / 180;
		const cl = Math.cos(latR);
		this.sunDir.set(cl * Math.cos(lonR), Math.sin(latR), cl * Math.sin(lonR)).normalize();
		this.globe.setSunDirection(this.sunDir.x, this.sunDir.y, this.sunDir.z);
		this.sunLight.position.copy(this.sunDir).multiplyScalar(8);
		// Initial framing toward sunlit hemisphere — stop once the user grabs the globe.
		if (!this.userSteering) {
			const dist = 3.05;
			this.camera.position.set(
				this.sunDir.x * dist,
				this.sunDir.y * dist * 0.35 + 0.15,
				this.sunDir.z * dist
			);
			if (this.camera.position.lengthSq() < 0.5) this.camera.position.set(0, 0.15, dist);
			this.camera.lookAt(0, 0, 0);
			this.controls.target.set(0, 0, 0);
			this.controls.update();
		}
	}

	setOnFrame(cb: ((t: number) => void) | null) {
		this.onFrame = cb;
	}

	private render(now: number) {
		const dt = Math.min(0.05, (now - this.lastT) / 1000);
		this.lastT = now;
		this.globe.tick(dt);
		this.controls.update();

		const s = this.keyframes.sample(Date.now(), this.tmp);
		if (s) {
			itrsKmToScene(s, SCALE, this.tmp3);
			this.satMesh.position.set(this.tmp3[0], this.tmp3[1], this.tmp3[2]);
		}
		this.renderer.render(this.scene, this.camera);
	}
}
