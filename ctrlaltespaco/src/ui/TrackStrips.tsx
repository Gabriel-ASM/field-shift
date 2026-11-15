import { useEffect, useRef } from "react";
import { playhead } from "../state/playhead.ts";
import type { Track } from "../types.ts";
import { caneShade } from "./caneShade.ts";
import { cropColor } from "./colors.ts";

const ROW_HEIGHT = 3;
const ROW_GAP = 1;

function cellColor(track: Track, step: number, cuts: number | null): string {
  const cut = track.cane_cut[step] ?? 0;
  return cut > 0 && cuts ? caneShade(cut, cuts) : cropColor(track.crop[step]!);
}

function drawTracks(canvas: HTMLCanvasElement, tracks: Track[], period: number, cuts: number | null): void {
  const context = canvas.getContext("2d");
  const steps = tracks[0]?.crop.length ?? 0;
  if (!context || !steps) return;
  const cell = canvas.width / steps;
  context.clearRect(0, 0, canvas.width, canvas.height);
  tracks.forEach((track, row) => {
    for (let step = 0; step <= Math.min(period, steps - 1); step++) {
      context.fillStyle = cellColor(track, step, cuts);
      context.fillRect(step * cell, row * (ROW_HEIGHT + ROW_GAP), Math.ceil(cell), ROW_HEIGHT);
    }
  });
}

/** Under the strips when cane appears: one swatch per cut, lighter to darker. */
function CaneCuts({ cuts }: { cuts: number }) {
  return (
    <p className="cane-cuts">Sugarcane by cut:{" "}
      {Array.from({ length: cuts }, (_, index) => <span key={index}><i style={{ background: caneShade(index + 1, cuts) }} />{index + 1}</span>)}
      <small> · after cut {cuts} the field is reformed</small>
    </p>
  );
}

/** Simulated trajectories, one thin row each, revealed up to the playhead. Cane is shaded by its cut. */
export function TrackStrips({ tracks, cuts }: { tracks: Track[]; cuts: number | null }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const draw = () => canvas.current && drawTracks(canvas.current, tracks, Math.floor(playhead.period), cuts);
    draw();
    return playhead.subscribe(draw);
  }, [tracks, cuts]);
  const height = tracks.length * (ROW_HEIGHT + ROW_GAP);
  const cane = tracks.some((track) => track.cane_cut.some((cut) => cut > 0));
  return (
    <>
      <canvas ref={canvas} className="tracks" width={480} height={height} aria-label={`${tracks.length} simulated trajectories`} />
      {cane && cuts ? <CaneCuts cuts={cuts} /> : null}
    </>
  );
}
