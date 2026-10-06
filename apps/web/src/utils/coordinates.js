// Purpose: Provides coordinates logic and exports for apps\web\src\utils.
export function validCoordinates(lat, lng) {
  return lat != null && lng != null && lat !== '' && lng !== '' && Number.isFinite(Number(lat)) && Number.isFinite(Number(lng)) && Math.abs(Number(lat)) <= 90 && Math.abs(Number(lng)) <= 180;
}
