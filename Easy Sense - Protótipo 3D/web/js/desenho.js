/** Geometria do trajeto. As unidades visuais são compartilhadas com cena3d.js. */
const DETECTION_X = 520;
const ENTRY_MARGIN = 35;
const TRAVEL_END = 1170;

export function vehiclePosition(vehicle, progress) {
  const startX = -vehicle.length - ENTRY_MARGIN;
  return startX + progress * (TRAVEL_END + vehicle.length);
}

export function detectionProgress(vehicle, axlePosition) {
  const startX = vehiclePosition(vehicle, 0);
  return (
    (DETECTION_X - startX - axlePosition * vehicle.length) /
    (TRAVEL_END + vehicle.length)
  );
}
