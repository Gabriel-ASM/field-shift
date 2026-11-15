/** Pixel-art drawings of the crops, on a 120 x 120 grid. Ported from cropArtInner in
 *  field_shift/front/producer.js (Gabriel): same paths and colours, as data instead of HTML strings. */

export interface Shape {
  d: string;
  fill: string;
}

const GREEN = "#477a45";
const DARK = "#315e39";
const LIGHT = "#77a657";
const GROUND = "#d7c5a3";

/** Leaf colour of the crops without a drawing of their own, from the same file. */
const LEAF: Record<string, string> = {
  sorghum_grain: "#b98545", wheat: "#c8a85d", dry_bean: "#9a7151", peanut: "#b78b50", oat: "#90a469",
  forage_radish: "#7c9a67", brachiaria: "#5f8b58", millet: "#a18b54", crotalaria: "#7d9b4f", mucuna: "#68895d",
};

const ground: Shape = { d: "M20 105h80v6H20z", fill: GROUND };

const DRAWINGS: Record<string, Shape[]> = {
  soybean: [
    ground,
    { d: "M57 100h6V43h-6z", fill: DARK },
    { d: "M60 57 39 43l-4 5 22 19zm2 14 22-17 4 5-25 22zM59 83 38 70l-4 5 23 17z", fill: GREEN },
    { d: "M34 37h18v7H38v7H25v-7h9zm49 10h18v8H88v7H75v-8h8zM28 64h18v7H34v7H20v-8h8z", fill: LIGHT },
    { d: "M68 77h8v20h-8zM46 82h8v17h-8z", fill: "#c4a849" },
    { d: "M70 80h3v13h-3zM48 85h3v10h-3z", fill: "#e1c967" },
  ],
  maize_grain: [
    ground,
    { d: "M57 101h7V22h-7z", fill: DARK },
    { d: "M57 46 36 29h-8v7l29 24zm7 15 28-22h8v8L64 76zM57 75 33 57h-9v8l33 25z", fill: GREEN },
    { d: "M66 45h14v25H66z", fill: "#d9ad37" },
    { d: "M69 48h3v3h-3zm6 0h3v3h-3zm-6 6h3v3h-3zm6 6h3v3h-3zm-6 6h3v3h-3z", fill: "#f2d365" },
    { d: "m64 42 16-7v12l-9-2zm0 9-9 19h9l8-19z", fill: LIGHT },
    { d: "M54 21h14v5H54z", fill: "#b4944b" },
  ],
  sugarcane: [
    { d: "M16 105h88v6H16z", fill: GROUND },
    { d: "M34 100h6V27h-6zm25 0h6V15h-6zm25 0h6V31h-6z", fill: "#78964d" },
    { d: "M34 49h6v5h-6zm0 22h6v5h-6zm25-32h6v5h-6zm0 25h6v5h-6zm25-12h6v5h-6zm0 24h6v5h-6z", fill: "#d0bd67" },
    { d: "M37 43 20 22h-6v8l20 26zm3 23 22-22h7v8L40 80zm22-35L44 9h-7v8l22 28zm3 30 23-24h8v8L65 76zm22-13 19-22h-7l-12 13z", fill: GREEN },
    { d: "M59 15 70 2h8L65 22zM34 27l-8-20h7l7 20z", fill: LIGHT },
  ],
  fallow: [ground],
};

function generic(leaf: string): Shape[] {
  return [
    ground,
    { d: "M57 102h7V48h-7z", fill: DARK },
    { d: "M59 66C40 66 31 56 31 39c19 0 28 10 28 27Zm3 12c0-19 9-29 28-29 0 17-9 27-28 29Z", fill: leaf },
    { d: "M58 91C43 91 35 83 35 70c15 0 23 8 23 21Z", fill: LIGHT },
  ];
}

/** The shapes of a crop's drawing; crops without one get the generic plant in their leaf colour. */
export function cropShapes(crop: string): Shape[] {
  return DRAWINGS[crop] ?? generic(LEAF[crop] ?? GREEN);
}
