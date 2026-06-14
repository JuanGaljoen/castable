// RNG-4 — Three.js STL viewer (vanilla ES module; vendored three r0.169.0).
// Listens for the `ring:generated` event app.js fires on a successful
// generation, loads the STL blob, and shows an interactive, orbitable preview.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const canvas = document.getElementById("viewer-canvas");
const messageEl = document.getElementById("viewer-message");
const toggleBtn = document.getElementById("wireframe-toggle");

const loader = new STLLoader();

let renderer = null;
let scene = null;
let camera = null;
let controls = null;
let mesh = null;
let initialized = false;
let wireframe = false;

function showViewerMessage(text) {
  if (messageEl) {
    messageEl.textContent = text;
    messageEl.hidden = false;
  }
  if (canvas) canvas.hidden = true;
  if (toggleBtn) toggleBtn.disabled = true;
}

function revealCanvas() {
  if (messageEl) messageEl.hidden = true;
  if (canvas) canvas.hidden = false;
}

function canvasSize() {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width));
  const height = Math.max(1, Math.round(rect.height));
  return { width, height };
}

function init() {
  if (initialized) return true;
  try {
    const { width, height } = canvasSize();
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(width, height, false);

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1d21);

    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(20, 16, 30);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const key = new THREE.DirectionalLight(0xffffff, 0.8);
    key.position.set(1, 1, 1);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.4);
    fill.position.set(-1, -0.5, -1);
    scene.add(fill);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    window.addEventListener("resize", handleResize);
    renderer.setAnimationLoop(animate);

    initialized = true;
    return true;
  } catch (err) {
    console.error("WebGL viewer init failed", err);
    showViewerMessage(
      "Interactive 3D preview is unavailable in this browser. Your STL download still works."
    );
    return false;
  }
}

function animate() {
  if (controls) controls.update();
  if (renderer && scene && camera) renderer.render(scene, camera);
}

function handleResize() {
  if (!initialized || canvas.hidden) return;
  const { width, height } = canvasSize();
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function disposeCurrent() {
  if (!mesh) return;
  scene.remove(mesh);
  if (mesh.geometry) mesh.geometry.dispose();
  if (mesh.material) mesh.material.dispose();
  mesh = null;
}

// RNG-1 builds the ring with the setting axis along +X. Three.js treats +Y as
// up, so rotate +90deg about Z to stand the setting up (+X -> +Y). (-90deg put
// the setting at -Y, i.e. hanging below the band.)
function orientUpright(target) {
  target.rotation.z = Math.PI / 2;
}

function frameModel(geometry) {
  geometry.center();
  geometry.computeBoundingSphere();
  const sphere = geometry.boundingSphere;
  const r = sphere ? sphere.radius : 10;
  const fov = (camera.fov * Math.PI) / 180;
  const dist = (r / Math.sin(fov / 2)) * 1.25;

  camera.near = Math.max(0.01, dist / 100);
  camera.far = dist * 10;
  camera.position.set(dist * 0.6, dist * 0.5, dist);
  camera.updateProjectionMatrix();

  if (controls) {
    controls.target.set(0, 0, 0);
    controls.update();
  }
}

async function render(blob) {
  if (!blob) return;
  if (!init()) return;
  try {
    const buffer = await blob.arrayBuffer();
    const geometry = loader.parse(buffer);
    disposeCurrent();
    if (!geometry.getAttribute("normal")) geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({
      color: 0xcfcfd6,
      metalness: 0.55,
      roughness: 0.35,
      wireframe,
    });
    mesh = new THREE.Mesh(geometry, material);
    orientUpright(mesh);
    scene.add(mesh);
    frameModel(geometry);

    revealCanvas();
    if (toggleBtn) toggleBtn.disabled = false;
    handleResize();
  } catch (err) {
    console.error("Could not display STL", err);
    showViewerMessage("Could not display this model. Your STL download still works.");
  }
}

function toggleWireframe() {
  if (!mesh) return;
  wireframe = !wireframe;
  mesh.material.wireframe = wireframe;
  toggleBtn.setAttribute("aria-pressed", String(wireframe));
}

document.addEventListener("ring:generated", (event) => {
  render(event.detail && event.detail.blob);
});

if (toggleBtn) toggleBtn.addEventListener("click", toggleWireframe);
