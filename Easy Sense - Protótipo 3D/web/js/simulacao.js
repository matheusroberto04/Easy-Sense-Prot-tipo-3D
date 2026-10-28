/** Controla a demonstração: escolhe veículo, anima, envia eventos e mostra o resultado. */
import { getState, sendAction } from "./api.js";
import { detectionProgress } from "./desenho.js";
import {
  drawScene3D,
  holdCameraFrames,
  releaseCameraFrames,
} from "./cena3d.js";
import { classifyCameraImage, TYPE_LABELS } from "./reconhecimento.js";

const element = (id) => document.getElementById(id);
const CAMERA_B_DELAY = 0.012; // Pequena diferença visual entre as duas observações.

// Estado da tela. Os dados permanentes ficam no banco Python, não nestas variáveis.
let currentState = null;
let running = false;
let busy = true;
let progress = 0;
let cameraEvents = [];
let processedEvents = new Set();
let lastResult = null;
let graphicsAvailable = false;
let recognitionCaptured = false;
let recognitionObservations = [];

function selectedVehicle() {
  return currentState?.vehicles[element("vehicle").value];
}

function showMessage(text, error = false) {
  element("message").textContent = text;
  element("message").className = error ? "error" : "";
}

function updateControls() {
  const activePassage = currentState?.active;
  const manualPassage = activePassage && activePassage.mode !== "simulation";
  element("vehicle").disabled = busy || running || Boolean(activePassage);
  element("run").disabled =
    busy || running || !currentState || manualPassage || !graphicsAvailable;
  element("cancel").disabled = busy || running || !activePassage;

  if (running) {
    element("run").textContent = "Simulando passagem…";
    element("status").textContent = "Passagem em andamento";
  } else {
    element("run").textContent =
      activePassage?.mode === "simulation"
        ? "Continuar passagem"
        : "Simular passagem";
    element("status").textContent = activePassage
      ? "Passagem pendente"
      : "Pronto para simular";
  }
}

function populateVehicleOptions() {
  // As opções vêm de config.py; não precisam ser repetidas no HTML.
  element("vehicle").replaceChildren();
  for (const [key, vehicle] of Object.entries(currentState.vehicles)) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = `${vehicle.label} · ${vehicle.axes.length} eixos`;
    element("vehicle").append(option);
  }
}

function renderCameraCounts() {
  for (const camera of ["A", "B"]) {
    const count = cameraEvents.filter(
      (event) => event.camera === camera,
    ).length;
    element(`count${camera}`).textContent =
      `${count} ${count === 1 ? "evento" : "eventos"}`;
  }
}

function renderConfirmedAxles() {
  element("evidence").replaceChildren();
  const vehicle = selectedVehicle();
  if (!vehicle) return;

  for (let axle = 1; axle <= vehicle.axes.length; axle++) {
    const observations = cameraEvents.filter((event) => event.axle === axle);
    const confirmed = observations.length === 2;
    const badge = document.createElement("span");
    badge.className = confirmed ? "ok" : "";
    badge.textContent = `E${axle}${confirmed ? " ✓" : " ·"}`;
    element("evidence").append(badge);
  }
}

function renderHistory() {
  element("history").replaceChildren();
  for (const passage of currentState.history) {
    const row = document.createElement("tr");
    const vehicleName =
      passage.mode === "manual"
        ? "Registro manual"
        : passage.recognition_status === "agreed"
          ? TYPE_LABELS[passage.identified_type]
          : passage.recognition_status === "inconclusive"
            ? "Inconclusivo"
            : "Sem análise visual";
    const values = [
      `#${passage.id}`,
      vehicleName,
      passage.axes,
      new Date(passage.ended).toLocaleTimeString("pt-BR"),
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    element("history").append(row);
  }
  element("empty").hidden = currentState.history.length > 0;
  element("total").textContent =
    `${currentState.total_passages} passagens · histórico compartilhado com o modo manual`;
}

function renderRecognition() {
  const passage = currentState.active || lastResult;
  const status = passage?.recognition_status;
  element("identifiedType").textContent =
    status === "agreed"
      ? TYPE_LABELS[passage.identified_type]
      : status === "inconclusive"
        ? "Inconclusivo"
        : "Aguardando imagem";
  element("recognitionStatus").textContent =
    status === "agreed"
      ? "As duas câmeras concordaram · regras visuais"
      : status === "inconclusive"
        ? "Sem acordo entre as vistas. Revisar a passagem."
        : "Análise automática quando o veículo estiver inteiro no quadro.";
  for (const camera of ["A", "B"]) {
    const observation = recognitionObservations.find(
      (item) => item.camera === camera,
    );
    element(`recognition${camera}`).textContent = observation
      ? `${TYPE_LABELS[observation.detected_type]} · ${observation.wheel_count} rodas · ${observation.window_count} ${observation.window_count === 1 ? "janela" : "janelas"}`
      : "Análise visual pendente";
  }
}

function renderState(data) {
  const firstLoad = currentState === null;
  currentState = data;
  if (firstLoad) populateVehicleOptions();

  const activePassage = data.active;
  if (activePassage?.mode === "simulation") {
    element("vehicle").value = activePassage.vehicle;
    cameraEvents = data.camera_events;
    recognitionObservations = data.recognition_observations;
  }
  const confirmed =
    activePassage?.mode === "simulation"
      ? activePassage.axes
      : lastResult?.axes || 0;
  element("confirmed").textContent = confirmed;
  renderCameraCounts();
  renderConfirmedAxles();
  renderHistory();
  renderRecognition();
  updateControls();
}

async function performAction(action, payload = {}) {
  const data = await sendAction(action, payload);
  renderState(data);
  return data;
}

function redraw() {
  drawScene3D(selectedVehicle(), element("vehicle").value, progress, running);
  graphicsAvailable = true;
}

function resetSimulationView() {
  releaseCameraFrames();
  element("frameStatus").textContent = "Câmeras virtuais · quadros ao vivo";
  progress = 0;
  cameraEvents = [];
  processedEvents = new Set();
  lastResult = null;
  recognitionCaptured = false;
  recognitionObservations = [];
  element("log").textContent = "Aguardando veículo.";
  renderState(currentState);
  redraw();
}

async function recognizeVehicle(passageId) {
  if (progress < 0.5) return;
  if (recognitionCaptured) {
    holdCameraFrames();
    element("frameStatus").textContent =
      "Quadros analisados preservados para conferência";
    return;
  }
  // Neste ponto o veículo inteiro cabe nas duas vistas. A função recebe só os pixels.
  for (const camera of ["A", "B"]) {
    const observation = classifyCameraImage(element(`cam${camera}`));
    await performAction("recognition", {
      passage_id: passageId,
      camera,
      ...observation,
    });
  }
  recognitionCaptured = true;
  holdCameraFrames();
  element("frameStatus").textContent =
    "Quadros analisados preservados para conferência";
}

function createDetectionSchedule(vehicle) {
  const schedule = [];
  vehicle.axes.forEach((position, index) => {
    // O veículo anda para a direita; o eixo da frente recebe o número 1.
    const axle = vehicle.axes.length - index;
    const at = detectionProgress(vehicle, position);
    schedule.push({ at, camera: "A", axle });
    schedule.push({ at: at + CAMERA_B_DELAY, camera: "B", axle });
  });
  return schedule.sort((first, second) => first.at - second.at);
}

async function sendCrossedAxles(schedule, passageId) {
  for (const event of schedule) {
    const eventKey = `${event.camera}:${event.axle}`;
    if (progress < event.at || processedEvents.has(eventKey)) continue;

    await performAction("camera", {
      passage_id: passageId,
      camera: event.camera,
      axle: event.axle,
    });
    processedEvents.add(eventKey);
    element("log").textContent =
      `Câmera ${event.camera} · eixo ${event.axle} observado`;
  }
}

function animateVehicle(vehicle, passageId) {
  const schedule = createDetectionSchedule(vehicle);
  const duration = currentState.simulation_settings.duration_ms;
  let previousFrame = performance.now();

  return new Promise((resolve, reject) => {
    async function frame(timestamp) {
      try {
        // Limita saltos da animação se a aba ficar temporariamente em segundo plano.
        const elapsed = Math.min(timestamp - previousFrame, 80);
        previousFrame = timestamp;
        progress = Math.min(1, progress + elapsed / duration);
        redraw();
        await recognizeVehicle(passageId);
        await sendCrossedAxles(schedule, passageId);

        if (progress < 1) requestAnimationFrame(frame);
        else resolve();
      } catch (error) {
        reject(error);
      }
    }
    requestAnimationFrame(frame);
  });
}

async function runSimulation() {
  if (busy || running) return;
  busy = true;
  updateControls();
  showMessage("Iniciando a passagem simulada…");

  try {
    if (!currentState.active) {
      cameraEvents = [];
      lastResult = null;
      recognitionObservations = [];
      await performAction("simulation", { vehicle: element("vehicle").value });
    }
    const passageId = currentState.active.id;
    const vehicle = selectedVehicle();
    progress = 0;
    releaseCameraFrames();
    element("frameStatus").textContent = "Câmeras virtuais · quadros ao vivo";
    recognitionCaptured = currentState.recognition_observations.length === 2;
    processedEvents = new Set(
      cameraEvents.map((event) => `${event.camera}:${event.axle}`),
    );
    running = true;
    busy = false;
    updateControls();
    showMessage("As duas câmeras virtuais estão acompanhando o veículo.");

    await animateVehicle(vehicle, passageId);
    lastResult = { ...currentState.active };
    await performAction("finish");
    element("log").textContent = "Duas vistas confirmadas. Registro salvo.";
    showMessage(
      `Passagem #${passageId} salva: ${TYPE_LABELS[lastResult.identified_type] || "sem identificação visual"}, ${lastResult.axes} eixos.`,
    );
  } catch (error) {
    const message =
      error instanceof TypeError
        ? "Conexão interrompida. Verifique o terminal e atualize a página para recuperar a passagem."
        : error.message;
    showMessage(message, true);
  } finally {
    running = false;
    busy = false;
    updateControls();
    redraw();
  }
}

async function cancelPassage() {
  if (busy || running || !confirm("Cancelar a passagem pendente?")) return;
  busy = true;
  updateControls();
  try {
    await performAction("cancel");
    resetSimulationView();
    showMessage("Passagem cancelada. Você pode iniciar outra.");
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    busy = false;
    updateControls();
  }
}

async function loadInitialState() {
  try {
    renderState(await getState());
    if (currentState.active?.mode === "simulation") {
      showMessage(
        "Passagem pendente recuperada. Clique em Continuar passagem. Os eventos já salvos não serão contados novamente.",
      );
    } else if (currentState.active) {
      showMessage(
        "Há uma passagem manual pendente. Conclua no modo manual ou cancele aqui.",
      );
    } else {
      showMessage("Escolha um veículo e clique em Simular passagem.");
    }
    redraw();
  } catch {
    showMessage(
      currentState
        ? "Não foi possível iniciar o 3D. Use um navegador com WebGL 2 ou abra o modo manual."
        : "Não foi possível conectar. Execute app.py e abra o endereço mostrado no terminal.",
      true,
    );
  } finally {
    busy = false;
    updateControls();
  }
}

element("run").addEventListener("click", runSimulation);
element("vehicle").addEventListener("change", resetSimulationView);
element("cancel").addEventListener("click", cancelPassage);
loadInitialState();
