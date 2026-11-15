import { useEffect, useRef } from "react";
import { playhead } from "../state/playhead.ts";
import type { Track } from "../types.ts";
import { cropColor } from "./colors.ts";

const ROW_HEIGHT = 3;
const ROW_GAP = 1;

function drawTracks(canvas: HTMLCanvasElement, tracks: Track[], period: number): void {
  const context = canvas.getContext("2d");
  const steps = tracks[0]?.crop.length ?? 0;
  if (!context || !steps) return;
  const cell = canvas.width / steps;
  context.clearRect(0, 0, canvas.width, canvas.height);
  tracks.forEach((track, row) => {
    for (let step = 0; step <= Math.min(period, steps - 1); step++) {
      context.fillStyle = cropColor(track.crop[step]!);
      context.fillRect(step * cell, row * (ROW_HEIGHT + ROW_GAP), Math.ceil(cell), ROW_HEIGHT);
    }
  });
}

/** Simulated trajectories, one thin row each, revealed up to the playhead. */
export function TrackStrips({ tracks }: { tracks: Track[] }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const draw = () => canvas.current && drawTracks(canvas.current, tracks, Math.floor(playhead.period));
    draw();
    return playhead.subscribe(draw);
  }, [tracks]);
  const height = tracks.length * (ROW_HEIGHT + ROW_GAP);
  return <canvas ref={canvas} className="tracks" width={480} height={height} aria-label={`${tracks.length} simulated trajectories`} />;
}
