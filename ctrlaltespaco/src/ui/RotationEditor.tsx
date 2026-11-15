import { cropColor, cropLabel } from "./colors.ts";

interface RotationEditorProps {
  crops: string[];
  sequence: string[];
  onChange: (sequence: string[]) => void;
}

/** Build the fixed rotation compared against what the region usually does. */
export function RotationEditor({ crops, sequence, onChange }: RotationEditorProps) {
  const without = (index: number) => sequence.filter((_, position) => position !== index);
  return (
    <div className="rotation">
      <div className="chips">
        {sequence.map((crop, index) => (
          <button key={index} type="button" className="chip" style={{ borderColor: cropColor(crop) }}
            title="Remove" disabled={sequence.length === 1} onClick={() => onChange(without(index))}>
            {cropLabel(crop)}
          </button>
        ))}
      </div>
      <select value="" aria-label="Add a crop to the rotation" onChange={(event) => onChange([...sequence, event.target.value])}>
        <option value="" disabled>Add crop…</option>
        {crops.map((crop) => <option key={crop} value={crop}>{cropLabel(crop)}</option>)}
      </select>
    </div>
  );
}
