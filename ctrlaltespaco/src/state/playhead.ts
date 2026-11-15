/** The moment of the simulation being shown, in periods. Animated by GSAP, read every frame by the scene. */

import gsap from "gsap";

type Listener = () => void;

export class Playhead {
  /** Current period, fractional while animating. Read it directly inside render loops. */
  period = 0;
  #periods = 0;
  #tween: gsap.core.Tween | null = null;
  #listeners = new Set<Listener>();

  get periods(): number {
    return this.#periods;
  }

  get playing(): boolean {
    return Boolean(this.#tween?.isActive());
  }

  /** Start over with a run of `periods` periods. */
  reset(periods: number): void {
    this.#tween?.kill();
    this.#tween = null;
    this.#periods = periods;
    this.period = 0;
    this.#notify();
  }

  play(secondsPerYear: number, periodsPerYear: number): void {
    if (this.period >= this.#periods) this.period = 0;
    const duration = ((this.#periods - this.period) / periodsPerYear) * secondsPerYear;
    this.#tween?.kill();
    this.#tween = gsap.to(this, { period: this.#periods, duration, ease: "none", onUpdate: this.#notify, onComplete: this.#notify });
    this.#notify();
  }

  pause(): void {
    this.#tween?.kill();
    this.#tween = null;
    this.#notify();
  }

  seek(period: number): void {
    this.pause();
    this.period = Math.min(this.#periods, Math.max(0, period));
    this.#notify();
  }

  subscribe = (listener: Listener): (() => void) => {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  };

  #notify = (): void => {
    for (const listener of this.#listeners) listener();
  };
}

export const playhead = new Playhead();
