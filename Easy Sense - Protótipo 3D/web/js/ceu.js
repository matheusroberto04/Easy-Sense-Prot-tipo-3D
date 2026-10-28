/** Céu e nuvens gerados localmente, sem baixar imagens ou texturas. */
import * as THREE from "../vendor/three.module.js";

function createCloud(x, y, z, scale) {
  const cloud = new THREE.Group();
  const material = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.9,
    depthWrite: false,
  });
  const shapes = [
    [-43, 0, 0, 37, 15, 23],
    [-13, 10, 0, 35, 25, 27],
    [20, 7, 0, 39, 21, 26],
    [54, 0, 2, 32, 14, 22],
  ];
  for (const [offsetX, offsetY, offsetZ, width, height, depth] of shapes) {
    const part = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 10), material);
    part.position.set(offsetX, offsetY, offsetZ);
    part.scale.set(width, height, depth);
    cloud.add(part);
  }
  cloud.position.set(x, y, z);
  cloud.scale.setScalar(scale);
  return cloud;
}

export function addSky(scene) {
  const skyMaterial = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      zenithColor: { value: new THREE.Color("#78b7e8") },
      horizonColor: { value: new THREE.Color("#eaf4fc") },
      sunColor: { value: new THREE.Color("#fff1d3") },
    },
    vertexShader: `
      varying vec3 skyPosition;
      void main() {
        vec4 worldPosition = modelMatrix * vec4(position, 1.0);
        skyPosition = worldPosition.xyz;
        gl_Position = projectionMatrix * viewMatrix * worldPosition;
      }
    `,
    fragmentShader: `
      uniform vec3 zenithColor;
      uniform vec3 horizonColor;
      uniform vec3 sunColor;
      varying vec3 skyPosition;
      void main() {
        vec3 direction = normalize(skyPosition - vec3(550.0, 0.0, 0.0));
        float heightBlend = smoothstep(-0.10, 0.65, direction.y);
        vec3 color = mix(horizonColor, zenithColor, heightBlend);
        float sunlight = pow(max(dot(direction, normalize(vec3(-0.3, 0.45, -0.8))), 0.0), 70.0);
        color = mix(color, sunColor, sunlight * 0.65);
        gl_FragColor = vec4(color, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(2400, 32, 16),
    skyMaterial,
  );
  sky.position.x = 550;
  sky.renderOrder = -20;
  scene.add(sky);

  scene.add(
    createCloud(-220, 220, -800, 1.5),
    createCloud(280, 260, -1000, 1.9),
    createCloud(940, 230, -820, 1.6),
    createCloud(1430, 280, -1100, 1.8),
  );
  // Tudo fica na camada 0: o céu não entra no recorte usado pelo classificador.
}
