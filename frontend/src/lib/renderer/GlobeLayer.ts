/**
 * Realistic Earth globe — same stack used by three-globe / turban webgl-earth:
 * equirectangular Blue Marble day map + bump + specular ocean + night lights,
 * cloud shell, fresnel atmosphere. No procedural continent blobs.
 */
import * as THREE from 'three';
import { atmosphereFragment, atmosphereVertex } from './terminator.glsl';

const TEX = {
	day: '/textures/earth-day.jpg',
	night: '/textures/earth-night.jpg',
	normal: '/textures/earth-normal.jpg',
	specular: '/textures/earth-specular.jpg',
	clouds: '/textures/earth-clouds.png'
};

function configureColorMap(tex: THREE.Texture, anisotropy: number) {
	tex.colorSpace = THREE.SRGBColorSpace;
	tex.anisotropy = anisotropy;
	tex.minFilter = THREE.LinearMipmapLinearFilter;
	tex.magFilter = THREE.LinearFilter;
	tex.wrapS = THREE.ClampToEdgeWrapping;
	tex.wrapT = THREE.ClampToEdgeWrapping;
	tex.needsUpdate = true;
}

function configureDataMap(tex: THREE.Texture, anisotropy: number) {
	tex.colorSpace = THREE.NoColorSpace;
	tex.anisotropy = anisotropy;
	tex.minFilter = THREE.LinearMipmapLinearFilter;
	tex.magFilter = THREE.LinearFilter;
	tex.wrapS = THREE.ClampToEdgeWrapping;
	tex.wrapT = THREE.ClampToEdgeWrapping;
	tex.needsUpdate = true;
}

function loadTexture(loader: THREE.TextureLoader, url: string): Promise<THREE.Texture> {
	return new Promise((resolve, reject) => {
		loader.load(url, resolve, undefined, reject);
	});
}

export class GlobeLayer {
	readonly group = new THREE.Group();
	readonly mesh: THREE.Mesh;
	readonly clouds: THREE.Mesh;
	readonly atmosphere: THREE.Mesh;
	readonly material: THREE.MeshPhongMaterial;
	private sun = new THREE.Vector3(1, 0.35, 0.4).normalize();
	private textures: THREE.Texture[] = [];
	private ready = false;
	private cloudSpin = 0;

	constructor(anisotropy = 8) {
		// Placeholder ocean so the panel isn't empty while maps stream in
		this.material = new THREE.MeshPhongMaterial({
			color: 0x1a5f9e,
			specular: new THREE.Color(0x333333),
			shininess: 12
		});
		this.mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), this.material);
		this.group.add(this.mesh);

		const cloudMat = new THREE.MeshPhongMaterial({
			color: 0xffffff,
			transparent: true,
			opacity: 0,
			depthWrite: false
		});
		this.clouds = new THREE.Mesh(new THREE.SphereGeometry(1.008, 64, 48), cloudMat);
		this.group.add(this.clouds);

		const atmoMat = new THREE.ShaderMaterial({
			vertexShader: atmosphereVertex,
			fragmentShader: atmosphereFragment,
			transparent: true,
			depthWrite: false,
			side: THREE.BackSide,
			blending: THREE.AdditiveBlending
		});
		atmoMat.toneMapped = false;
		this.atmosphere = new THREE.Mesh(new THREE.SphereGeometry(1.045, 64, 48), atmoMat);
		this.group.add(this.atmosphere);

		void this.loadMaps(anisotropy);
	}

	private async loadMaps(anisotropy: number) {
		const loader = new THREE.TextureLoader();
		try {
			const [day, night, normal, specular, clouds] = await Promise.all([
				loadTexture(loader, TEX.day),
				loadTexture(loader, TEX.night),
				loadTexture(loader, TEX.normal),
				loadTexture(loader, TEX.specular),
				loadTexture(loader, TEX.clouds)
			]);

			configureColorMap(day, anisotropy);
			configureColorMap(night, anisotropy);
			configureColorMap(clouds, anisotropy);
			configureDataMap(normal, anisotropy);
			configureDataMap(specular, anisotropy);

			this.textures = [day, night, normal, specular, clouds];

			this.material.map = day;
			this.material.normalMap = normal;
			this.material.normalScale = new THREE.Vector2(0.85, 0.85);
			this.material.specularMap = specular;
			this.material.specular = new THREE.Color(0x333333);
			this.material.shininess = 22;
			// Subtle city lights — keep intensity low so day Blue Marble dominates.
			this.material.emissiveMap = night;
			this.material.emissive = new THREE.Color(0xffffff);
			this.material.emissiveIntensity = 0.2;
			this.material.color = new THREE.Color(0xffffff);
			this.material.needsUpdate = true;

			const cloudMat = this.clouds.material as THREE.MeshPhongMaterial;
			cloudMat.map = clouds;
			cloudMat.opacity = 0.35;
			cloudMat.transparent = true;
			cloudMat.depthWrite = false;
			cloudMat.blending = THREE.AdditiveBlending;
			cloudMat.needsUpdate = true;

			this.ready = true;
		} catch (err) {
			console.error('Earth texture load failed', err);
		}
	}

	addTo(parent: THREE.Object3D) {
		parent.add(this.group);
	}

	/** World-space sun direction (ITRS-ish); drives Phong shading / night lights. */
	setSunDirection(x: number, y: number, z: number) {
		this.sun.set(x, y, z).normalize();
	}

	getSunDirection(out = new THREE.Vector3()) {
		return out.copy(this.sun);
	}

	/** Subtle differential cloud drift — call once per frame. */
	tick(dtSec: number) {
		if (!this.ready) return;
		this.cloudSpin += dtSec * 0.004;
		this.clouds.rotation.y = this.cloudSpin;
	}

	get isReady() {
		return this.ready;
	}

	dispose() {
		this.mesh.geometry.dispose();
		this.clouds.geometry.dispose();
		this.atmosphere.geometry.dispose();
		this.material.dispose();
		(this.clouds.material as THREE.Material).dispose();
		(this.atmosphere.material as THREE.Material).dispose();
		for (const t of this.textures) t.dispose();
	}
}
