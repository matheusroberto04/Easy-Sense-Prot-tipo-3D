/** Operação por botões. A tela de câmeras fica em simulacao.js. */
import { getState, sendAction } from "./api.js";

const element = (id) => document.getElementById(id);
const actions = ["start", "axle", "undo", "finish", "cancel"];
const successMessages = {
  start: "Passagem iniciada. Registre cada eixo.",
  axle: "Eixo registrado.",
  undo: "Último eixo removido.",
  finish: "Passagem finalizada e salva no histórico.",
  cancel: "Passagem cancelada. Nenhum resultado foi incluído no histórico.",
};
let currentState = null;
let busy = true;

function showMessage(text, error = false) {
  element("message").textContent = text;
  element("message").className = error ? "error" : "";
}

function updateControls() {
  const activePassage = currentState?.active;
  for (const action of actions) {
    const requiresActive = action !== "start";
    const requiresAxles = ["undo", "finish"].includes(action);
    element(action).disabled =
      busy ||
      !currentState ||
      (requiresActive ? !activePassage : Boolean(activePassage)) ||
      (requiresAxles && !activePassage?.axes);
  }
}

function renderWheels(count) {
  element("wheels").replaceChildren();
  for (let axle = 0; axle < Math.min(count, 10); axle++) {
    const wheel = document.createElement("span");
    wheel.className = "wheel";
    element("wheels").append(wheel);
  }
}

function renderHistory() {
  element("history").replaceChildren();
  for (const passage of currentState.history) {
    const row = document.createElement("tr");
    const values = [
      `#${passage.id}`,
      new Date(passage.ended).toLocaleString("pt-BR"),
      passage.axes,
      `${passage.axes} ${passage.axes === 1 ? "eixo" : "eixos"}`,
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    element("history").append(row);
  }
  element("empty").hidden = currentState.history.length > 0;
}

function renderState(data) {
  currentState = data;
  const activePassage = data.active;
  const count = activePassage?.axes || 0;
  element("count").textContent = count;
  element("status").textContent = activePassage ? "Em andamento" : "Aguardando";
  element("status").className = `status${activePassage ? " active" : ""}`;
  element("passage").textContent = activePassage
    ? `Passagem #${activePassage.id} · iniciada em ${new Date(activePassage.started).toLocaleString("pt-BR")}`
    : "Nenhuma passagem em andamento.";
  element("total").textContent = data.total_passages;
  element("axes").textContent = data.total_axes;
  renderWheels(count);
  renderHistory();
  updateControls();
}

async function refreshState() {
  renderState(await getState());
}

async function performAction(action) {
  if (busy) return;
  if (
    action === "cancel" &&
    !confirm("Cancelar esta passagem? Ela não entrará no histórico.")
  )
    return;
  busy = true;
  updateControls();
  try {
    renderState(await sendAction(action));
    showMessage(successMessages[action]);
  } catch (error) {
    const message =
      error instanceof TypeError
        ? "Sem conexão com o programa. Verifique se o terminal está aberto e atualize a página."
        : error.message;
    showMessage(message, true);
    // Se a resposta se perdeu, recarrega o estado antes de permitir outra ação.
    try {
      await refreshState();
    } catch {
      /* Mantém a mensagem de conexão. */
    }
  } finally {
    busy = false;
    updateControls();
  }
}

async function loadInitialState() {
  try {
    await refreshState();
    showMessage(
      currentState.active
        ? "Passagem em andamento recuperada. Você pode continuar."
        : "Tudo pronto para a demonstração.",
    );
  } catch {
    showMessage(
      "Abra esta tela pelo endereço exibido no terminal, com o programa em execução.",
      true,
    );
  } finally {
    busy = false;
    updateControls();
  }
}

for (const action of actions) {
  element(action).addEventListener("click", () => performAction(action));
}
window.addEventListener("focus", async () => {
  if (busy) return;
  busy = true;
  updateControls();
  try {
    await refreshState();
  } catch {
    showMessage("Verifique se o programa continua aberto no terminal.", true);
  } finally {
    busy = false;
    updateControls();
  }
});
loadInitialState();
