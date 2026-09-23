import * as THREE from '../t800/vendor/three/three.module.js';
import { GLTFLoader } from '../t800/vendor/three/GLTFLoader.js';
import { DRACOLoader } from '../t800/vendor/three/DRACOLoader.js';

const CONFIG = {
  eyeSmoothing: 0.2,
  headSmoothing: 0.075,
  eyeLimit: 0.5,
  headSensitivity: { x: 0.30, y: 0.18 },
  mouthIntensity: 0.58,
  mouthAttack: 20,
  mouthRelease: 11,
  headHeightFraction: 0.58,
  cameraFov: 27
};

const viewport = document.querySelector('#viewport');
const loading = document.querySelector('#loading');
const errorBox = document.querySelector('#error');
const input = document.querySelector('#speech-input');
const form = document.querySelector('#speech-form');
const pointer = new THREE.Vector2();
const targetLook = new THREE.Vector2();
const currentLook = new THREE.Vector2();
const currentHeadLook = new THREE.Vector2();
const worldTarget = new THREE.Vector3();
const cameraRight = new THREE.Vector3();
const cameraUp = new THREE.Vector3();
const quaternionA = new THREE.Quaternion();
const quaternionB = new THREE.Quaternion();
const eyeBaseQuaternions = new Map();
const eyeLocalForwards = new Map();
let scene, camera, renderer, character, clock;
let head, leftEye, rightEye, jaw;
let headBaseQuaternion, jawBaseQuaternion;
let mouthOpenAmount = 0;
let speech = { active: false, energy: 0, lastBoundary: 0 };

const dracoLoader = new DRACOLoader().setDecoderPath('../t800/vendor/three/draco/');
const gltfLoader = new GLTFLoader().setDRACOLoader(dracoLoader);

function renderSize() {
  const height = viewport.clientHeight;
  return { width: Math.min(viewport.clientWidth, Math.round(height * .58)), height };
}

function setupScene() {
  scene = new THREE.Scene();
  scene.fog = new THREE.Fog('#090807', 1.8, 4.6);
  const size = renderSize();
  camera = new THREE.PerspectiveCamera(CONFIG.cameraFov, size.width / size.height, 0.01, 100);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(size.width, size.height);
  renderer.domElement.style.margin = '0 auto';
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.18;
  viewport.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight('#ffe6c3', '#120c07', 2.3));
  const key = new THREE.DirectionalLight('#fff0d5', 3.4); key.position.set(2, 3, 4); scene.add(key);
  const rim = new THREE.PointLight('#e79245', 4.5, 5); rim.position.set(-2, 1, -2); scene.add(rim);
  clock = new THREE.Clock();
}

function discoverControls() {
  head = character.getObjectByName('cm_J_FaceRoot');
  leftEye = character.getObjectByName('cm_J_Eye_s_L');
  rightEye = character.getObjectByName('cm_J_Eye_s_R');
  jaw = character.getObjectByName('cm_J_MouthLow');
  if (!head || !leftEye || !rightEye || !jaw) throw new Error('O modelo Smoke não contém os pivôs faciais necessários.');
  headBaseQuaternion = head.quaternion.clone();
  jawBaseQuaternion = jaw.quaternion.clone();
  [leftEye, rightEye].forEach((eye) => eyeBaseQuaternions.set(eye, eye.quaternion.clone()));
  window.__smokeControls = { head, leftEye, rightEye, jaw };
  console.info('Smoke controls', Object.fromEntries(Object.entries(window.__smokeControls).map(([key, value]) => [key, value.name])));
}

function frameCharacter() {
  // The GLB keeps the full original skin (including legs) but the page uses
  // the same chest-up camera treatment as T-800.
  const upperParts = ['Smoke_head', 'Smoke_hat', 'Smoke_hat_bandana', 'Smoke_hair'];
  const bounds = new THREE.Box3();
  upperParts.forEach((name) => {
    const object = character.getObjectByName(name);
    if (object) bounds.expandByObject(object);
  });
  if (bounds.isEmpty()) bounds.setFromObject(character);
  const size = bounds.getSize(new THREE.Vector3());
  const target = bounds.getCenter(new THREE.Vector3());
  // Keep the complete character in the GLB, but compose this page as a
  // portrait: hat, face, collar and the top of the jacket, never its T-pose.
  target.y -= size.y * 0.18;
  const distance = size.y / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * CONFIG.headHeightFraction);
  camera.position.set(target.x, target.y, target.z + distance);
  camera.zoom = 1;
  camera.updateProjectionMatrix();
  camera.lookAt(target);
}

function cacheEyeAim() {
  [leftEye, rightEye].forEach((eye) => {
    eye.parent.updateWorldMatrix(true, false);
    eye.updateWorldMatrix(false, false);
    const neutralWorld = eye.getWorldQuaternion(new THREE.Quaternion());
    const eyePosition = eye.getWorldPosition(new THREE.Vector3());
    const cameraDirection = camera.position.clone().sub(eyePosition).normalize();
    eyeLocalForwards.set(eye, cameraDirection.applyQuaternion(neutralWorld.invert()).normalize());
  });
}

function updatePointer(event) {
  const rect = viewport.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
  const eyeAnchor = leftEye.getWorldPosition(new THREE.Vector3()).add(rightEye.getWorldPosition(new THREE.Vector3())).multiplyScalar(0.5).project(camera);
  targetLook.set(THREE.MathUtils.clamp(pointer.x - eyeAnchor.x, -1, 1), THREE.MathUtils.clamp(pointer.y - eyeAnchor.y, -1, 1));
}

function applyEyeTracking() {
  cameraRight.setFromMatrixColumn(camera.matrixWorld, 0);
  cameraUp.setFromMatrixColumn(camera.matrixWorld, 1);
  worldTarget.copy(camera.position).addScaledVector(cameraRight, currentLook.x * 2.8).addScaledVector(cameraUp, currentLook.y * 1.8);
  [leftEye, rightEye].forEach((eye) => {
    const base = eyeBaseQuaternions.get(eye);
    eye.quaternion.copy(base);
    eye.parent.updateWorldMatrix(true, false);
    eye.updateWorldMatrix(false, false);
    const eyePosition = eye.getWorldPosition(new THREE.Vector3());
    const neutralWorld = eye.getWorldQuaternion(quaternionA);
    const localForward = eyeLocalForwards.get(eye);
    const neutralForward = localForward.clone().applyQuaternion(neutralWorld).normalize();
    const desiredForward = worldTarget.clone().sub(eyePosition).normalize();
    const turn = quaternionB.setFromUnitVectors(neutralForward, desiredForward);
    const angle = 2 * Math.acos(THREE.MathUtils.clamp(turn.w, -1, 1));
    if (angle > CONFIG.eyeLimit) turn.slerp(new THREE.Quaternion(), 1 - CONFIG.eyeLimit / angle);
    const desiredWorld = turn.multiply(neutralWorld);
    eye.quaternion.copy(eye.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(desiredWorld));
  });
}

function animateMouth(delta) {
  speech.energy = Math.max(0, speech.energy - delta * 5.2);
  const target = speech.active ? Math.max(0.055, speech.energy * CONFIG.mouthIntensity) : 0;
  mouthOpenAmount = THREE.MathUtils.damp(mouthOpenAmount, target, target > mouthOpenAmount ? CONFIG.mouthAttack : CONFIG.mouthRelease, delta);
  jaw.quaternion.copy(jawBaseQuaternion).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), mouthOpenAmount));
}

function stopSpeech() { speech = { active: false, energy: 0, lastBoundary: 0 }; }
function onSpeechBoundary(event) {
  const now = performance.now();
  const gap = Math.min((now - speech.lastBoundary) / 1000, 0.3);
  speech.lastBoundary = now;
  const char = event.charIndex === undefined ? '' : event.utterance.text[event.charIndex] || '';
  speech.energy = THREE.MathUtils.clamp((/[aeiouáàâãéêíóôõúü]/i.test(char) ? 1 : 0.55) * (0.72 + gap * 0.9), 0.25, 1);
}
function speak(text) {
  const cleanText = text.trim();
  if (!cleanText) return;
  window.speechSynthesis.cancel();
  stopSpeech();
  const utterance = new SpeechSynthesisUtterance(cleanText);
  speech = { active: true, energy: 0.3, lastBoundary: performance.now() };
  utterance.onboundary = onSpeechBoundary;
  utterance.onend = utterance.onerror = stopSpeech;
  window.speechSynthesis.speak(utterance);
}

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.05);
  if (character) {
    currentLook.lerp(targetLook, CONFIG.eyeSmoothing);
    currentHeadLook.lerp(targetLook, CONFIG.headSmoothing);
    head.quaternion.copy(headBaseQuaternion)
      .multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), currentHeadLook.x * CONFIG.headSensitivity.x))
      .multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -currentHeadLook.y * CONFIG.headSensitivity.y));
    character.updateMatrixWorld(true);
    applyEyeTracking();
    animateMouth(delta);
  }
  renderer.render(scene, camera);
}

async function init() {
  setupScene();
  try {
    const gltf = await gltfLoader.loadAsync('./Smoke-bust.glb');
    character = gltf.scene;
    window.__smokeCharacter = character;
    scene.add(character);
    discoverControls();
    frameCharacter();
    cacheEyeAim();
    loading.hidden = true;
    animate();
  } catch (error) {
    console.error(error);
    loading.hidden = true;
    errorBox.hidden = false;
    errorBox.textContent = `Não foi possível carregar Smoke-bust.glb. Sirva esta pasta por HTTP. Detalhes: ${error.message}`;
  }
}

form.addEventListener('submit', (event) => { event.preventDefault(); speak(input.value); input.focus(); });
viewport.addEventListener('pointermove', updatePointer);
window.addEventListener('resize', () => {
  if (!renderer || !camera) return;
  const size = renderSize();
  camera.aspect = size.width / size.height;
  camera.updateProjectionMatrix();
  renderer.setSize(size.width, size.height);
  frameCharacter();
  cacheEyeAim();
});
init();
