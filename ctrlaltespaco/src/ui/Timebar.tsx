import { playhead } from "../state/playhead.ts";
import { usePeriod, usePlaying } from "../state/usePlayhead.ts";

const SECONDS_PER_YEAR = 2.4;

export function Timebar({ periodsPerYear }: { periodsPerYear: number }) {
  const period = usePeriod();
  const playing = usePlaying();
  const toggle = () => (playing ? playhead.pause() : playhead.play(SECONDS_PER_YEAR, periodsPerYear));
  return (
    <div className="timebar">
      <button type="button" onClick={toggle}>{playing ? "Pause" : "Play"}</button>
      <input type="range" min={0} max={playhead.periods} value={period} aria-label="Time"
        onChange={(event) => playhead.seek(Number(event.target.value))} />
      <output>Year {(period / periodsPerYear).toFixed(1)}</output>
    </div>
  );
}
