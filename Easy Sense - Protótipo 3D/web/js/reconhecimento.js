/** Classificação por regras nos pixels das câmeras virtuais.
 * Recebe SOMENTE um canvas: não lê o seletor, o modelo ou a configuração do veículo.
 * Regras para este ambiente sintético, com cores e iluminação controladas.
 * Não é um modelo treinado para imagens de rodovias reais.
 */

function connectedComponents(image, matches) {
  const { width, height, data } = image;
  const visited = new Uint8Array(width * height);
  const components = [];
  const queue = new Int32Array(width * height);

  for (let start = 0; start < visited.length; start++) {
    if (visited[start]) continue;
    visited[start] = 1;
    const offset = start * 4;
    if (!matches(data[offset], data[offset + 1], data[offset + 2])) continue;
    let head = 0,
      tail = 1;
    queue[0] = start;
    let minX = width,
      maxX = 0,
      minY = height,
      maxY = 0,
      area = 0;

    while (head < tail) {
      const index = queue[head++];
      const x = index % width;
      const y = Math.floor(index / width);
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
      area++;
      for (const neighbor of [
        x > 0 ? index - 1 : -1,
        x + 1 < width ? index + 1 : -1,
        y > 0 ? index - width : -1,
        y + 1 < height ? index + width : -1,
      ]) {
        if (neighbor < 0 || visited[neighbor]) continue;
        visited[neighbor] = 1;
        const pixel = neighbor * 4;
        if (matches(data[pixel], data[pixel + 1], data[pixel + 2]))
          queue[tail++] = neighbor;
      }
    }
    components.push({
      minX,
      minY,
      maxX,
      maxY,
      width: maxX - minX + 1,
      height: maxY - minY + 1,
      area,
    });
  }
  return components;
}

export function classifyCameraImage(sourceCanvas) {
  // Copia o quadro WebGL para um canvas 2D que permite ler os pixels.
  const frame = document.createElement("canvas");
  frame.width = sourceCanvas.width;
  frame.height = sourceCanvas.height;
  const context = frame.getContext("2d", { willReadFrequently: true });
  context.drawImage(sourceCanvas, 0, 0);
  const image = context.getImageData(0, 0, frame.width, frame.height);

  const tires = connectedComponents(
    image,
    (r, g, b) => r < 35 && g < 45 && b < 60,
  ).filter(
    (part) =>
      part.width >= 12 &&
      part.width <= 32 &&
      part.height >= 12 &&
      part.height <= 32 &&
      part.area >= 70 &&
      part.minY > image.height * 0.5,
  );
  const windows = connectedComponents(
    image,
    (r, g, b) => r > 140 && r < 205 && g > 200 && b > 235,
  ).filter((part) => part.width >= 10 && part.height >= 10 && part.area >= 100);

  const wheelCount = tires.length;
  const windowCount = windows.length;
  let detectedType = "unknown";
  if (wheelCount >= 5 && wheelCount <= 8) detectedType = "trailer";
  else if (wheelCount === 3 || wheelCount === 4) detectedType = "truck";
  else if (wheelCount === 2 && windowCount >= 4) detectedType = "bus";
  else if (wheelCount === 2 && windowCount > 0 && windowCount <= 3)
    detectedType = "car";

  return {
    detected_type: detectedType,
    wheel_count: wheelCount,
    window_count: windowCount,
  };
}

export const TYPE_LABELS = {
  car: "Carro",
  bus: "Ônibus",
  truck: "Caminhão",
  trailer: "Carreta",
  unknown: "Inconclusivo",
};
