/** Cena WebGL e câmeras virtuais. O classificador de imagens fica em reconhecimento.js. */
import * as THREE from "../vendor/three.module.js";
import { vehiclePosition } from "./desenho.js";
import { addSky } from "./ceu.js";

const TIRE_COLOR = 0x17212b;
const WINDOW_COLOR = 0xa8dcff;
let sceneView = null;

function cameraLabel(scene, letter, x, y, z) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const context = canvas.getContext("2d");
  context.fillStyle = "#c2410c";
  context.beginPath();
  context.arc(32, 32, 29, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = "white";
  context.font = "bold 38px system-ui";
  context.textAlign = "center";
  context.fillText(letter, 32, 46);
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(canvas),
      depthTest: false,
    }),
  );
  sprite.position.set(x, y, z);
  sprite.scale.set(32, 32, 1);
  scene.add(sprite);
}

function box(parent, width, height, depth, x, y, z, color, unlit = false) {
  const Material = unlit ? THREE.MeshBasicMaterial : THREE.MeshStandardMaterial;
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(width, height, depth),
    new Material({ color }),
  );
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function cylinder(parent, radius, height, x, y, z, color) {
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, height, 20),
    new THREE.MeshBasicMaterial({ color }),
  );
  mesh.position.set(x, y, z);
  parent.add(mesh);
  return mesh;
}

function sideWindows(parent, positions, y, width, height, halfWidth) {
  for (const z of [-halfWidth - 0.4, halfWidth + 0.4]) {
    for (const x of positions) {
      box(parent, width, height, 0.6, x, y, z, WINDOW_COLOR, true);
    }
  }
}

function createVehicle(vehicle, key) {
  const group = new THREE.Group();
  const length = vehicle.length;
  const wheels = [];
  box(group, length, 10, 52, length / 2, 20, 0, 0x445360);

  if (key === "car") {
    box(group, length, 22, 60, length / 2, 32, 0, vehicle.color);
    box(group, length * 0.55, 24, 52, length * 0.53, 54, 0, vehicle.color);
    sideWindows(group, [length * 0.39, length * 0.66], 55, 31, 16, 26);
  } else if (key === "bus") {
    box(group, length, 54, 64, length / 2, 51, 0, vehicle.color);
    const windows = [];
    for (let x = 22; x < length - 15; x += 32) windows.push(x);
    sideWindows(group, windows, 62, 23, 22, 32);
  } else {
    const trailer = key === "trailer";
    const cargoLength = length * (trailer ? 0.56 : 0.66);
    box(group, cargoLength, 62, 64, cargoLength / 2, 56, 0, vehicle.color);
    box(group, 62, 44, 60, length - 31, 44, 0, vehicle.color);
    sideWindows(group, [length - 31], 54, 29, 20, 30);
  }

  // Um par de rodas por eixo. As câmeras laterais veem um lado por vez.
  for (const axle of vehicle.axes) {
    for (const side of [-1, 1]) {
      const wheelGroup = new THREE.Group();
      wheelGroup.position.set(axle * length, 13, side * 32);
      const tire = cylinder(wheelGroup, 12, 6, 0, 0, 0, TIRE_COLOR);
      tire.rotation.x = Math.PI / 2;
      const hub = cylinder(wheelGroup, 5, 6.8, 0, 0, 0, 0xa4b2bf);
      hub.rotation.x = Math.PI / 2;
      group.add(wheelGroup);
      wheels.push(wheelGroup);
    }
  }
  // A camada 1 contém só o veículo: um recorte controlado das câmeras virtuais.
  group.traverse((object) => object.layers.enable(1));
  return { group, wheels };
}

class TollScene {
  constructor() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xdce9ef);
    addSky(this.scene);
    const ambient = new THREE.HemisphereLight(0xffffff, 0x829b7c, 2.4);
    ambient.layers.enable(1);
    this.scene.add(ambient);
    const sun = new THREE.DirectionalLight(0xffffff, 2.6);
    sun.layers.enable(1);
    sun.position.set(300, 700, 300);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    Object.assign(sun.shadow.camera, {
      left: -900,
      right: 900,
      top: 700,
      bottom: -700,
      far: 1600,
    });
    sun.target.position.set(550, 0, 0);
    this.scene.add(sun, sun.target);

    this.renderer = this.makeRenderer("world", 1100, 410);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.camera = new THREE.PerspectiveCamera(43, 1100 / 410, 1, 4000);
    this.yaw = 0.42;
    this.elevation = 0.58;
    this.distance = 1050;
    this.lastFrame = null;
    this.holdFrames = false;
    this.model = null;
    this.modelSignature = null;

    this.sideViews = {};
    for (const [name, direction] of [
      ["A", -1],
      ["B", 1],
    ]) {
      const camera = new THREE.OrthographicCamera(-300, 300, 115, -92, 1, 1000);
      camera.position.set(550, 70, direction * 400);
      camera.lookAt(550, 70, 0);
      camera.layers.set(1);
      this.sideViews[name] = {
        camera,
        renderer: this.makeRenderer(`cam${name}`, 550, 190),
      };
    }
    this.buildPlaza();
    this.bindControls();
  }

  makeRenderer(id, width, height) {
    const renderer = new THREE.WebGLRenderer({
      canvas: document.getElementById(id),
      antialias: true,
      preserveDrawingBuffer: true,
    });
    renderer.setPixelRatio(1);
    renderer.setSize(width, height, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    return renderer;
  }

  buildPlaza() {
    box(this.scene, 2300, 8, 900, 550, -7, 0, 0xa7bd99);
    box(this.scene, 1750, 3, 148, 550, -1, 0, 0x42474b);
    for (const z of [-65, 65]) {
      box(this.scene, 1720, 0.6, 2, 550, 1, z, 0xe6e8d5);
      for (let x = -200; x < 1450; x += 85) {
        box(this.scene, 38, 0.7, 2, x, 1.1, z * 0.8, 0xf0dfaf);
      }
    }
    for (const z of [-112, 112]) {
      box(this.scene, 1700, 4, 4, 550, 28, z, 0xa4b6b8);
      for (let x = -170; x < 1400; x += 100)
        box(this.scene, 4, 30, 4, x, 14, z, 0xa4b6b8);
    }
    // Cabine, ilha de proteção e cobertura.
    box(this.scene, 120, 10, 78, 630, 4, -145, 0xe8dbad);
    box(this.scene, 76, 80, 60, 630, 46, -145, 0xe8e7dd);
    box(this.scene, 85, 8, 70, 630, 90, -145, 0xd75416);
    box(this.scene, 51, 29, 1, 630, 60, -114, 0x7fc9d5);
    box(this.scene, 1, 29, 35, 669, 60, -143, 0x7fc9d5);
    for (const x of [470, 730])
      box(this.scene, 8, 150, 8, x, 75, -180, 0x7b9489);
    box(this.scene, 360, 8, 160, 600, 154, -130, 0xd75416);
    box(this.scene, 360, 11, 12, 600, 149, -44, 0x262626);

    // Câmeras A e B em lados opostos da pista.
    for (const z of [-92, 92]) {
      box(this.scene, 5, 78, 5, 520, 39, z, 0x414141);
      box(this.scene, 24, 13, 15, 520, 82, z, 0x202020);
      const lens = cylinder(
        this.scene,
        4,
        4,
        520,
        82,
        z - Math.sign(z) * 9,
        0xffa65e,
      );
      lens.rotation.x = Math.PI / 2;
      cameraLabel(this.scene, z < 0 ? "A" : "B", 520, 114, z);
    }
    box(this.scene, 2.5, 0.8, 130, 520, 1.2, 0, 0xff9d4a);

    box(this.scene, 10, 55, 10, 685, 27, -76, 0xe4e4db);
    this.barrier = new THREE.Group();
    this.barrier.position.set(685, 52, -76);
    box(this.barrier, 5, 5, 148, 0, 0, 74, 0xe6b653);
    this.scene.add(this.barrier);
  }

  bindControls() {
    const canvas = this.renderer.domElement;
    let drag = null;
    canvas.addEventListener("pointerdown", (event) => {
      drag = { x: event.clientX, y: event.clientY };
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!drag) return;
      this.yaw -= (event.clientX - drag.x) * 0.005;
      this.elevation = THREE.MathUtils.clamp(
        this.elevation + (event.clientY - drag.y) * 0.004,
        0.22,
        1.25,
      );
      drag = { x: event.clientX, y: event.clientY };
      if (this.lastFrame) this.draw(...this.lastFrame);
    });
    canvas.addEventListener("pointerup", () => {
      drag = null;
    });
    canvas.addEventListener("pointercancel", () => {
      drag = null;
    });
    document.getElementById("resetView").addEventListener("click", () => {
      this.yaw = 0.42;
      this.elevation = 0.58;
      if (this.lastFrame) this.draw(...this.lastFrame);
    });
  }

  updateModel(vehicle, key) {
    const signature = key + JSON.stringify(vehicle);
    if (signature === this.modelSignature) return;
    if (this.model) {
      this.scene.remove(this.model.group);
      this.model.group.traverse((object) => {
        object.geometry?.dispose();
        object.material?.dispose();
      });
    }
    this.model = createVehicle(vehicle, key);
    this.modelSignature = signature;
    this.scene.add(this.model.group);
  }

  draw(vehicle, key, progress, running) {
    if (!vehicle) return;
    this.lastFrame = [vehicle, key, progress, running];
    this.updateModel(vehicle, key);
    const x = vehiclePosition(vehicle, progress);
    this.model.group.position.x = x;
    for (const wheel of this.model.wheels) wheel.rotation.z = -x / 12;
    this.barrier.rotation.x = progress > 0.33 && progress < 0.95 ? -1.48 : 0;
    this.camera.position.set(
      550 + Math.sin(this.yaw) * this.distance * Math.cos(this.elevation),
      this.distance * Math.sin(this.elevation),
      Math.cos(this.yaw) * this.distance * Math.cos(this.elevation),
    );
    this.camera.lookAt(550, 60, 0);
    this.renderer.render(this.scene, this.camera);
    if (!this.holdFrames) {
      for (const view of Object.values(this.sideViews))
        view.renderer.render(this.scene, view.camera);
    }
  }
}

export function drawScene3D(vehicle, key, progress, running) {
  if (!sceneView) sceneView = new TollScene();
  sceneView.draw(vehicle, key, progress, running);
}

export function holdCameraFrames() {
  if (sceneView) sceneView.holdFrames = true;
}

export function releaseCameraFrames() {
  if (sceneView) sceneView.holdFrames = false;
}
