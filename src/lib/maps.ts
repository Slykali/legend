import { ADDRESS, VENUE } from "../constants/site";

export function getGoogleDirectionsUrl(): string {
  const d = encodeURIComponent(`${VENUE}, ${ADDRESS}`);
  return `https://www.google.com/maps/dir/?api=1&destination=${d}`;
}

export function getMapsEmbedUrl(): string {
  const q = encodeURIComponent(`${VENUE}, ${ADDRESS}`);
  return `https://www.google.com/maps?q=${q}&hl=tr&z=17&output=embed`;
}
