/** Comunicação com o Python. As duas telas usam as mesmas funções. */

async function readResponse(response) {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Não foi possível concluir a operação.");
  }
  return data;
}

export async function getState() {
  const response = await fetch("/api/state");
  return readResponse(response);
}

export async function sendAction(action, payload = {}) {
  const response = await fetch(`/api/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readResponse(response);
}
