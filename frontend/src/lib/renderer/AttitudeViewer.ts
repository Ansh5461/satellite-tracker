import * as THREE from 'three';

/** Small imperative quaternion attitude visualizer (separate from main globe). */
export class AttitudeViewer {
	private renderer: THREE.WebGLRenderer;
	private scene = new THREE.Scene();
	private camera: THREE.PerspectiveCamera;
	private body: THREE.Group;
	private raf = 0;
	private running = false;

	constructor(private canvas: HTMLCanvasElement) {
		this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
		this.renderer.setClearColor(0x000000, 0);
		this.camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100);
		this.camera.position.set(2.2, 1.6, 2.2);
		this.camera.lookAt(0, 0, 0);
		this.scene.add(new THREE.AmbientLight(0xffffff, 0.6));
		const L = new THREE.DirectionalLight(0xffffff, 0.8);
		L.position.set(3, 4, 2);
		this.scene.add(L);

		this.body = new THREE.Group();
		const cube = new THREE.Mesh(
			new THREE.BoxGeometry(0.6, 0.6, 0.6),
			new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.3, roughness: 0.5 })
		);
		this.body.add(cube);
		// Solar panels
		const panelMat = new THREE.MeshStandardMaterial({ color: 0x1e3a8a, metalness: 0.2, roughness: 0.4 });
		const p1 = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.02, 0.4), panelMat);
		p1.position.set(0.9, 0, 0);
		const p2 = p1.clone();
		p2.position.set(-0.9, 0, 0);
		this.body.add(p1, p2);
		// Axes
		this.body.add(new THREE.AxesHelper(1.0));
		this.scene.add(this.body);
		this.resize();
	}

	mount() {
		if (this.running) return;
		this.running = true;
		const loop = () => {
			this.raf = requestAnimationFrame(loop);
			this.renderer.render(this.scene, this.camera);
		};
		this.raf = requestAnimationFrame(loop);
	}

	dispose() {
		this.running = false;
		cancelAnimationFrame(this.raf);
		this.renderer.dispose();
	}

	resize() {
		const w = this.canvas.clientWidth || 240;
		const h = this.canvas.clientHeight || 180;
		this.renderer.setSize(w, h, false);
		this.camera.aspect = w / Math.max(h, 1);
		this.camera.updateProjectionMatrix();
	}

	/** q = (w,x,y,z) body←inertial */
	setQuaternion(w: number, x: number, y: number, z: number) {
		this.body.quaternion.set(x, y, z, w).normalize();
	}
}
