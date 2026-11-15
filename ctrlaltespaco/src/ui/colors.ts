/** One colour per crop, the same everywhere a crop appears. */

const CROP_COLORS: Record<string, string> = {
  soybean: "#3f9d63",
  maize_grain: "#e3a82b",
  sugarcane: "#4f8fd0",
  dry_bean: "#b9603f",
  sorghum_grain: "#c9793a",
  wheat: "#d8c36a",
  peanut: "#a67c52",
  oat: "#9fb86b",
  forage_radish: "#c06aa8",
  brachiaria: "#5fb3a1",
  millet: "#8f7fd0",
  crotalaria: "#e0d04a",
  mucuna: "#6a8f4f",
  fallow: "#6b7280",
};

const UNKNOWN = "#94a3b8";

export function cropColor(crop: string): string {
  return CROP_COLORS[crop] ?? UNKNOWN;
}

export function cropLabel(crop: string): string {
  return crop.replace(/_/g, " ");
}
