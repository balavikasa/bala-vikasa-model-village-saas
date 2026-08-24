import * as THREE from "https://unpkg.com/three@0.164.1/build/three.module.js";

const host = document.querySelector("#cluster-visual");
const canvas = document.querySelector("#cluster-canvas");
if (host && canvas && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 100);
  camera.position.set(0, 1.5, 12);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  const group = new THREE.Group();
  scene.add(group);

  const resize = () => {
    const { width, height } = host.getBoundingClientRect();
    renderer.setSize(Math.max(1, width), Math.max(1, height), false);
    camera.aspect = width / Math.max(1, height);
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(host);
  resize();

  const sphere = new THREE.SphereGeometry(0.12, 18, 18);
  const materials = {
    CSRB: new THREE.MeshBasicMaterial({ color: 0xE8A93A }),
    PDTC: new THREE.MeshBasicMaterial({ color: 0x8FC594 }),
  };
  const lineMaterial = new THREE.LineBasicMaterial({ color: 0xFFFFFF, transparent: true, opacity: 0.14 });
  let loaded = false;

  fetch("/api/v1/villages", { credentials: "same-origin", headers: { Accept: "application/json" } })
    .then((response) => response.ok ? response.json() : Promise.reject())
    .then((payload) => {
      const items = payload.items || [];
      const centers = { CSRB: new THREE.Vector3(-2.4, 0, 0), PDTC: new THREE.Vector3(2.4, 0, 0) };
      Object.entries(centers).forEach(([cluster, position]) => {
        const hub = new THREE.Mesh(new THREE.SphereGeometry(0.34, 24, 24), materials[cluster]);
        hub.position.copy(position);
        group.add(hub);
      });
      const counters = { CSRB: 0, PDTC: 0 };
      items.forEach((item, index) => {
        const cluster = item.cluster === "PDTC" ? "PDTC" : "CSRB";
        const localIndex = counters[cluster]++;
        const count = Math.max(1, items.filter((candidate) => candidate.cluster === cluster).length);
        const angle = localIndex / count * Math.PI * 2 + (cluster === "PDTC" ? 0.4 : 0);
        const radius = 1.25 + (localIndex % 4) * 0.33;
        const position = centers[cluster].clone().add(new THREE.Vector3(
          Math.cos(angle) * radius,
          Math.sin(angle * 1.7) * 1.45,
          Math.sin(angle) * radius * 0.62
        ));
        const node = new THREE.Mesh(sphere, materials[cluster]);
        node.position.copy(position);
        group.add(node);
        const geometry = new THREE.BufferGeometry().setFromPoints([centers[cluster], position]);
        group.add(new THREE.Line(geometry, lineMaterial));
      });
      loaded = true;
    })
    .catch(() => {
      host.classList.add("is-static");
    });

  let frame;
  const animate = () => {
    frame = requestAnimationFrame(animate);
    if (loaded) {
      group.rotation.y += 0.0018;
      group.rotation.x = Math.sin(performance.now() / 5000) * 0.08;
    }
    renderer.render(scene, camera);
  };
  animate();

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) cancelAnimationFrame(frame);
    else animate();
  });
}
