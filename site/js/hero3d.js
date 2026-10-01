// The hero: Riser's real island (exported from the app's Blender pipeline), floating live in
// Three.js under a sky that follows the visitor's local time of day, just like the app.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const SKIES = {
  dawn:  { css: "linear-gradient(180deg, #3d4f9e 0%, #9a7fc0 38%, #f59f8b 70%, #ffd9a0 100%)", sun: 0xffb37a, sunI: 2.4, hemiSky: 0xb9b3ff, hemiGround: 0xe0a080, hemiI: 1.1, dir: [-6, 5, 8], night: 0, exposure: 1.0 },
  day:   { css: "linear-gradient(180deg, #3a78dd 0%, #6fa9ee 40%, #a9d3f7 72%, #e9f4ff 100%)", sun: 0xfff1dc, sunI: 2.6, hemiSky: 0xcfe8ff, hemiGround: 0x9ccf7a, hemiI: 1.0, dir: [6, 12, 7], night: 0, exposure: 0.95 },
  dusk:  { css: "linear-gradient(180deg, #232766 0%, #6b3f86 36%, #d8687e 68%, #ffb46b 100%)", sun: 0xff9a5a, sunI: 2.1, hemiSky: 0x9a8cd8, hemiGround: 0xc07a5a, hemiI: 0.95, dir: [8, 4, 6], night: 0.35, exposure: 1.0 },
  night: { css: "linear-gradient(180deg, #03061a 0%, #0a1440 45%, #16235e 80%, #25306b 100%)", sun: 0x9fb7ff, sunI: 0.9, hemiSky: 0x4a5aa0, hemiGround: 0x141a38, hemiI: 0.7, dir: [-5, 9, 6], night: 1, exposure: 1.1 },
};

export function skyForHour(h) {
  if (h >= 5 && h < 8) return "dawn";
  if (h >= 8 && h < 17) return "day";
  if (h >= 17 && h < 20) return "dusk";
  return "night";
}

export async function createHero(canvas, { reduce = false, onReady } = {}) {
  const hero = canvas.parentElement;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.35;

  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 400);

  // Lights
  const hemi = new THREE.HemisphereLight(0xffffff, 0x88aa66, 1.2);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffffff, 3);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -11; sun.shadow.camera.right = 11;
  sun.shadow.camera.top = 11; sun.shadow.camera.bottom = -11;
  sun.shadow.camera.near = 1; sun.shadow.camera.far = 60;
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.03;
  sun.shadow.radius = 4;
  scene.add(sun, sun.target);

  // Stars (fade in at night)
  const starGeo = new THREE.BufferGeometry();
  const N = 900, pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const u = Math.random() * Math.PI * 2, v = Math.acos(1 - Math.random() * 1.1);
    const r = 150;
    pos[i * 3] = r * Math.sin(v) * Math.cos(u);
    pos[i * 3 + 1] = r * Math.cos(v) - 20;
    pos[i * 3 + 2] = r * Math.sin(v) * Math.sin(u) - 60;
  }
  starGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const starMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.55, transparent: true, opacity: 0, depthWrite: false });
  scene.add(new THREE.Points(starGeo, starMat));

  // World
  const world = new THREE.Group();
  scene.add(world);
  const draco = new DRACOLoader().setDecoderPath("https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/");
  const loader = new GLTFLoader().setDRACOLoader(draco);
  const load = (url) => new Promise((res, rej) => loader.load(url, res, undefined, rej));
  const [islandG, sproutG, cloudG] = await Promise.all([
    load("assets/3d/island.glb"), load("assets/3d/sprout.glb"), load("assets/3d/cloud.glb"),
  ]);

  const island = islandG.scene;
  const glowMats = new Set();
  const canopies = [];
  let blades = null, doorPoint = null, lamps = [];
  island.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) if (m && /^Glow/.test(m.name)) { glowMats.add(m); m.userData.base = m.emissive.clone(); }
    }
    if (o.name === "Blades") blades = o;
    if (o.name.startsWith("Canopy")) canopies.push({ node: o, phase: Math.random() * 6, base: o.rotation.clone() });
    if (o.name === "DoorPoint") doorPoint = o;
    if (o.name === "LightPoint") lamps.push(o);
  });
  world.add(island);
  const floatRocks = ["FloatRock1", "FloatRock2", "FloatRock3"].map((n) => island.getObjectByName(n)).filter(Boolean)
    .map((node, i) => ({ node, base: node.position.clone(), phase: i * 2.1 }));

  // Warm little lights for the night.
  const nightLights = lamps.map((p) => {
    const l = new THREE.PointLight(0xffb866, 0, 5, 1.6);
    p.add(l);
    return l;
  });

  // The sprout, hopping in front of his door.
  const sprout = sproutG.scene;
  sprout.traverse((o) => { if (o.isMesh) { o.castShadow = true; } });
  sprout.scale.setScalar(2.1);
  island.updateMatrixWorld(true);
  const door = new THREE.Vector3(0.3, 0, 1.6);
  if (doorPoint) { doorPoint.getWorldPosition(door); door.y = 0; }
  const sproutHome = door.clone().add(new THREE.Vector3(1.35, 0, 2.2));
  sprout.position.copy(sproutHome);
  world.add(sprout);
  const armL = sprout.getObjectByName("ArmL"), armR = sprout.getObjectByName("ArmR");
  const armBase = { l: armL?.rotation.z ?? 0, r: armR?.rotation.z ?? 0 };

  // Clouds drifting around the island.
  const clouds = [];
  const cloudSrc = cloudG.scene;
  cloudSrc.traverse((o) => { if (o.isMesh) { o.material = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, emissive: 0xffffff, emissiveIntensity: 0.12 }); } });
  // Kept to the sides and low, so they frame the island without crossing the headline.
  const cloudSpecs = [[-17, 1.5, -6, 1.2], [17, 3, -9, 1.0], [-12, -4.5, 5, 0.8], [13, -3.5, 4, 0.9], [-24, 7, -24, 1.6], [25, 8.5, -26, 1.5]];
  for (const [x, y, z, s] of cloudSpecs) {
    const c = cloudSrc.clone();
    c.scale.setScalar(s);
    c.position.set(x, y, z);
    c.userData = { x, y, z, speed: 0.08 + Math.random() * 0.1, phase: Math.random() * 10 };
    scene.add(c);
    clouds.push(c);
  }

  // Sky state (tweened)
  const state = { night: 0, sunI: 3, hemiI: 1.2, exposure: 1, sun: new THREE.Color(), hemiSky: new THREE.Color(), hemiGround: new THREE.Color(), dir: new THREE.Vector3(6, 12, 7) };
  let target = SKIES.day;
  function setSky(name, instant = false) {
    target = SKIES[name] ?? SKIES.day;
    hero.style.setProperty("--sky", target.css);
    if (instant) {
      state.night = target.night; state.sunI = target.sunI; state.hemiI = target.hemiI; state.exposure = target.exposure;
      state.sun.set(target.sun); state.hemiSky.set(target.hemiSky); state.hemiGround.set(target.hemiGround); state.dir.set(...target.dir);
    }
  }
  setSky(new URLSearchParams(location.search).get("sky") || skyForHour(new Date().getHours()), true);

  // Layout: frame the island below the headline, whatever the aspect ratio.
  let scroll = 0;
  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  function resize() {
    const w = hero.clientWidth, h = hero.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  function placeCamera() {
    const aspect = camera.aspect;
    const vFov = THREE.MathUtils.degToRad(camera.fov);
    const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
    const needW = aspect < 0.8 ? 19 : 22.5; // island + air (wider on desktop so it sits under the copy)
    const dist = Math.max(33, needW / 2 / Math.tan(hFov / 2));
    const lift = aspect < 0.8 ? 6.6 : 6.7; // higher look-at = island sits lower in the frame
    camera.position.set(pointer.x * 1.2, 7.2 + pointer.y * 0.8 + scroll * 5, dist * (1 - scroll * 0.18));
    camera.lookAt(0, lift + scroll * 5.5, 0);
  }
  resize();
  new ResizeObserver(resize).observe(hero);
  if (!reduce) {
    window.addEventListener("pointermove", (e) => {
      pointer.tx = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.ty = (e.clientY / window.innerHeight) * 2 - 1;
    }, { passive: true });
  }

  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(canvas);

  const clock = new THREE.Clock();
  const t0 = performance.now();
  const k = (dt, rate) => 1 - Math.exp(-dt * rate);
  function frame() {
    requestAnimationFrame(frame);
    if (!visible || document.hidden) { clock.getDelta(); return; }
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;
    const motion = reduce ? 0 : 1;

    // Ease the sky/lighting toward the target.
    const e = k(dt, 2.2);
    state.night += (target.night - state.night) * e;
    state.sunI += (target.sunI - state.sunI) * e;
    state.hemiI += (target.hemiI - state.hemiI) * e;
    state.exposure += (target.exposure - state.exposure) * e;
    state.sun.lerp(new THREE.Color(target.sun), e);
    state.hemiSky.lerp(new THREE.Color(target.hemiSky), e);
    state.hemiGround.lerp(new THREE.Color(target.hemiGround), e);
    state.dir.lerp(new THREE.Vector3(...target.dir), e);
    sun.color.copy(state.sun); sun.intensity = state.sunI;
    sun.position.copy(state.dir).multiplyScalar(2.2);
    hemi.color.copy(state.hemiSky); hemi.groundColor.copy(state.hemiGround); hemi.intensity = state.hemiI;
    renderer.toneMappingExposure = state.exposure;
    starMat.opacity = state.night * 0.9;
    for (const m of glowMats) { m.emissive.copy(m.userData.base); m.emissiveIntensity = 0.25 + state.night * 3.2; }
    nightLights.forEach((l, i) => { l.intensity = state.night * (6 + Math.sin(t * 7 + i) * 0.6); });

    // Intro: the island rises into place.
    const intro = reduce ? 1 : Math.min(1, (performance.now() - t0) / 2200);
    const ease = 1 - Math.pow(1 - intro, 4);

    pointer.x += (pointer.tx - pointer.x) * k(dt, 3);
    pointer.y += (pointer.ty - pointer.y) * k(dt, 3);
    world.rotation.y = -0.35 + (1 - ease) * -0.9 + t * 0.06 * motion + pointer.x * 0.18;
    world.position.y = (1 - ease) * -7 + Math.sin(t * 0.7) * 0.18 * motion;

    if (blades) blades.rotation.z -= dt * 0.9 * motion;
    for (const c of canopies) c.node.rotation.z = c.base.z + Math.sin(t * 1.3 + c.phase) * 0.025 * motion;
    for (const r of floatRocks) r.node.position.y = r.base.y + Math.sin(t * 0.8 + r.phase) * 0.18 * motion;

    // Sprout: little hops, a wave now and then, always looking at you.
    const hop = Math.max(0, Math.sin(t * 3.1)) * motion;
    sprout.position.y = hop * 0.22;
    sprout.scale.set(2.1 * (1 + (1 - hop) * 0.04), 2.1 * (1 - (1 - hop) * 0.05 + hop * 0.04), 2.1);
    const camLocal = world.worldToLocal(camera.position.clone());
    sprout.rotation.y = Math.atan2(camLocal.x - sprout.position.x, camLocal.z - sprout.position.z);
    const wave = (Math.sin(t * 0.5) > 0.6 ? Math.sin(t * 12) * 0.5 : 0) * motion;
    if (armR) armR.rotation.z = armBase.r + wave;
    if (armL) armL.rotation.z = armBase.l;

    for (const c of clouds) {
      const u = c.userData;
      c.position.x = u.x + Math.sin(t * u.speed + u.phase) * 2.2 * motion;
      c.position.y = u.y + Math.sin(t * u.speed * 1.7 + u.phase) * 0.3 * motion;
    }

    placeCamera();
    renderer.render(scene, camera);
  }
  frame();
  canvas.classList.add("ready");
  onReady?.();

  return {
    setSky,
    setScroll(p) { scroll = p; },
  };
}
