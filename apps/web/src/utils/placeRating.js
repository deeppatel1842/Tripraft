// Purpose: Provides place Rating logic and exports for apps\web\src\utils.
export function placeRating(place = {}) {
  const raw = place.rating ?? (Number(place.rank_score) / 2);
  const score = Number(raw);
  return Number.isFinite(score) ? Math.max(0, Math.min(5, score)) : 0;
}
