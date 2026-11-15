import { useEffect, useRef } from "react";
import { playhead } from "../state/playhead.ts";
import { caneShade } from "./caneShade.ts";
import { cropColor, cropLabel } from "./colors.ts";
import { groupTracks, segments, type Segment, type StripTrack } from "./tracks.ts";

const WIDTH = 1000;          // viewBox units; the SVG stretches to the card
const ROW = 22;
const GAP = 8;
const MAX_GROUPS = 6;

function month(period: number, periodsPerYear: number): number {
  return Math.round((period * 12) / periodsPerYear);
}

function label(segment: Segment, periodsPerYear: number): string {
  const name = segment.cut ? `${cropLabel(segment.crop)}, cut ${segment.cut}` : cropLabel(segment.crop);
  return `${name}: month ${month(segment.start, periodsPerYear) + 1} to ${month(segment.end, periodsPerYear)}`;
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

/** The simulated trajectories grouped by how they unfolded: one strip per distinct timeline, with its share of the
 *  scenarios, revealed up to the playhead. Hovering a stretch names the crop and its months. Cane is shaded by cut. */
export function TrackStrips({ tracks, cuts, periodsPerYear }: { tracks: StripTrack[]; cuts: number | null; periodsPerYear: number }) {
  const reveal = useRef<SVGRectElement>(null);
  const groups = groupTracks(tracks);
  const shown = groups.slice(0, MAX_GROUPS);
  const steps = tracks[0]?.crop.length ?? 0;
  useEffect(() => {
    const draw = () => reveal.current?.setAttribute("width", String(WIDTH * Math.min(1, (Math.floor(playhead.period) + 1) / Math.max(steps, 1))));
    draw();
    return playhead.subscribe(draw);
  }, [steps]);
  if (!steps) return null;
  const height = shown.length * (ROW + GAP) - GAP;
  const scale = WIDTH / steps;
  const rest = tracks.length - shown.reduce((total, group) => total + group.count, 0);
  const cane = tracks.some((track) => track.cane_cut.some((cut) => cut > 0));
  return (
    <>
      <p className="note tracks-summary">
        {groups.length === 1
          ? `All ${tracks.length} sampled scenarios followed the same timeline.`
          : `${tracks.length} sampled scenarios, ${groups.length} different timelines.`}
      </p>
      <div className="tracks">
        <svg viewBox={`0 0 ${WIDTH} ${height}`} preserveAspectRatio="none" role="img"
          aria-label={`${groups.length} distinct timelines among ${tracks.length} simulated trajectories`}>
          <defs><clipPath id="tracks-reveal"><rect ref={reveal} x="0" y="0" width="0" height={height} /></clipPath></defs>
          <g clipPath="url(#tracks-reveal)">
            {shown.map((group, row) => segments(group.track).map((segment) => (
              <rect key={`${row}-${segment.start}`} x={segment.start * scale} y={row * (ROW + GAP)}
                width={(segment.end - segment.start) * scale} height={ROW}
                fill={segment.cut && cuts ? caneShade(segment.cut, cuts) : cropColor(segment.crop)}>
                <title>{label(segment, periodsPerYear)}</title>
              </rect>
            )))}
          </g>
        </svg>
        <ul className="tracks-counts" style={{ gridTemplateRows: `repeat(${shown.length}, ${ROW}fr)` }}>
          {shown.map((group, row) => <li key={row}>{group.count === tracks.length ? "all" : `${group.count} of ${tracks.length}`}</li>)}
        </ul>
      </div>
      {rest > 0 ? <p className="note">{rest} more scenarios follow {groups.length - shown.length} other timelines.</p> : null}
      {cane && cuts ? <CaneCuts cuts={cuts} /> : null}
    </>
  );
}
