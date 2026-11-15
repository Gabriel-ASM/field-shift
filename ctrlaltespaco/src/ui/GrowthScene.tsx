/** "We're growing possibilities": a row of the farmer's crop growing on a field, looping while the engine runs.
 *  Scene and drawings ported from renderGrowth in field_shift/front/producer.js (Gabriel). The engine answers in
 *  one piece, so the animation tells nothing about progress: it shows no count and no percentage. */

import gsap from "gsap";
import { useEffect, useId, useRef, useState, type RefObject } from "react";
import { CropShapes } from "./CropArt.tsx";

const STAGES = ["Preparing the soil", "Planting the first seeds", "The crop is growing", "Ready for harvest"];
// producer.js draws 7 plants across the 850-unit scene for a full-width card. The journey panel is narrow, so
// the scene is cropped to its middle (CSS aspect ratio, "slice") and holds 4 plants, larger on screen.
const PLANTS = 4;
const SIZE = 125;          // full-grown plant, in scene units
const BASE = 249;          // ground line
const SPACING = 130;
const FIRST_X = 175;
const GROWTH = [0, 58 / SIZE, 91 / SIZE, 1];   // plant size at each stage, as in producer.js

const plantSize = (index: number) => SIZE * (index % 2 ? 0.92 : 1);

function Backdrop({ id }: { id: string }) {
  return (
    <>
      <defs>
        <linearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1"><stop stopColor="#eaf3ee" /><stop offset="1" stopColor="#f7f7e9" /></linearGradient>
        <linearGradient id={`${id}-ground`} x1="0" y1="0" x2="0" y2="1"><stop stopColor="#c7b184" /><stop offset="1" stopColor="#a78d62" /></linearGradient>
      </defs>
      <rect width="850" height="330" fill={`url(#${id}-sky)`} />
      <circle cx="640" cy="67" r="34" fill="#efd895" opacity="0.75" />
      <g fill="#fff" opacity="0.72">
        <path d="M100 77h104a22 22 0 0 0-20-30 30 30 0 0 0-54-9 24 24 0 0 0-30 39Z" />
        <path d="M490 100h84a18 18 0 0 0-16-25 25 25 0 0 0-45-8 20 20 0 0 0-23 33Z" />
      </g>
      <path d="M0 213q120-35 240-5t230-4q190-39 380 2v124H0Z" fill="#91ac78" />
      <path d="M0 245q205-26 425-5t425-4v94H0Z" fill={`url(#${id}-ground)`} />
      <g fill="none" stroke="#8f7854" strokeWidth="3" opacity="0.55"><path d="M0 282q210-24 425-7t425-4M0 313q210-24 425-7t425-4" /></g>
      <path d="M0 244q205-25 425-5t425-4" fill="none" stroke="#e0cfa8" strokeWidth="3" />
    </>
  );
}

function Seeds({ seeds }: { seeds: RefObject<SVGGElement | null> }) {
  return (
    <g ref={seeds}>
      {Array.from({ length: PLANTS }, (_, index) => <rect key={index} x={FIRST_X + index * SPACING + SIZE / 2 - 3} y="245" width="7" height="4" rx="2" fill="#705c43" />)}
    </g>
  );
}

function Plants({ crop, plants }: { crop: string; plants: RefObject<(SVGGElement | null)[]> }) {
  return (
    <>
      {Array.from({ length: PLANTS }, (_, index) => {
        const size = plantSize(index);
        return (
          <g key={index} transform={`translate(${FIRST_X + index * SPACING + (SIZE - size) / 2} ${BASE - size})`}>
            <g ref={(node) => { plants.current[index] = node; }}>
              <svg width={size} height={size} viewBox="0 0 120 120" shapeRendering="crispEdges"><CropShapes crop={crop} /></svg>
            </g>
          </g>
        );
      })}
    </>
  );
}

/** One growing season, repeated: seeds, then the plants grow in pixel steps, hold, and fade. */
function season(plants: Element[], seeds: Element, setStage: (stage: number) => void): gsap.core.Timeline {
  const grow = (stage: number) => ({ scale: GROWTH[stage], opacity: stage === 1 ? 0.8 : 1, duration: 0.4, ease: "steps(3)", stagger: 0.07 });
  gsap.set(plants, { scale: 0, transformOrigin: "50% 100%" });
  return gsap.timeline({ repeat: -1, repeatDelay: 0.4 })
    .call(setStage, [0]).set(plants, { scale: 0, opacity: 1 }).to(seeds, { opacity: 1, duration: 0.3 })
    .call(setStage, [1], "+=0.9").to(seeds, { opacity: 0, duration: 0.2 }).to(plants, grow(1), "<")
    .call(setStage, [2], "+=0.9").to(plants, grow(2))
    .call(setStage, [3], "+=0.9").to(plants, grow(3))
    .to(plants, { opacity: 0, duration: 0.4 }, "+=1.6");
}

function still(plants: Element[], seeds: Element, setStage: (stage: number) => void): void {
  gsap.set(plants, { scale: 1, opacity: 1 });
  gsap.set(seeds, { opacity: 0 });
  setStage(STAGES.length - 1);
}

export function GrowthScene({ crop }: { crop: string }) {
  const id = useId().replace(/:/g, "");
  const seeds = useRef<SVGGElement>(null);
  const plants = useRef<(SVGGElement | null)[]>([]);
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const nodes = plants.current.filter((node): node is SVGGElement => node !== null);
    if (!seeds.current || !nodes.length) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return still(nodes, seeds.current, setStage);
    const timeline = season(nodes, seeds.current, setStage);
    return () => void timeline.kill();
  }, [crop]);
  return (
    <div className="growth-scene">
      <div className="growth-badge" aria-hidden="true"><i />{STAGES[stage]}</div>
      <svg viewBox="0 0 850 330" preserveAspectRatio="xMidYMax slice" role="img" aria-label={`Illustration: a field of ${crop.replace(/_/g, " ")} growing`}>
        <Backdrop id={id} />
        <Seeds seeds={seeds} />
        <Plants crop={crop} plants={plants} />
      </svg>
    </div>
  );
}
