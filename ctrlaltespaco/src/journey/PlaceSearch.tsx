/** Experimental: search any Brazilian municipality (IBGE list), show its real boundary on the map, and say whether
 *  it has a profile to simulate: a reviewed one is chosen at once, an experimental one is offered after the nearest reviewed. */

import { useEffect, useState } from "react";
import { getBuild, getMunicipalityBoundary, getProfile, searchMunicipalities, startBuild } from "../api.ts";
import { centre, nearest } from "../map/places.ts";
import type { Boundary, BuildView, Municipality, Profile } from "../types.ts";
import { percent } from "../ui/format.ts";

const DEBOUNCE_MS = 250;
const POLL_EVERY = 500;
const KM = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

/** A municipality picked in the search, with its boundary once it is loaded, and its experimental profile if it has one. */
export interface Explored {
  municipality: Municipality;
  boundary: Boundary | null;
  error: string | null;
  profile: Profile | null;
}

function useMatches(query: string): Municipality[] {
  const [found, setFound] = useState<{ query: string; rows: Municipality[] }>({ query: "", rows: [] });
  useEffect(() => {
    if (query.trim().length < 2) return;
    let live = true;
    const timer = setTimeout(() => {
      searchMunicipalities(query).then((rows) => live && setFound({ query, rows }), () => live && setFound({ query, rows: [] }));
    }, DEBOUNCE_MS);
    return () => { live = false; clearTimeout(timer); };
  }, [query]);
  return query.trim().length < 2 || found.query !== query ? [] : found.rows;
}

/** Assembling the data of one municipality on demand: null until asked, then the build as last polled. */
function useBuild(municipality: Municipality, onBuilt: (profile: Profile) => void) {
  const [build, setBuild] = useState<BuildView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asked, setAsked] = useState(0);
  useEffect(() => {
    if (!asked) return;
    let live = true;
    const fail = (failure: unknown) => live && setError(failure instanceof Error ? failure.message : String(failure));
    const follow = async () => {
      let view = await startBuild(municipality.code);
      for (;;) {
        if (!live) return;
        setBuild(view);
        if (view.status === "failed") throw new Error(view.error ?? "the data could not be assembled");
        if (view.status === "done") break;
        await new Promise((resolve) => setTimeout(resolve, POLL_EVERY));
        view = await getBuild(view.id);
      }
      const profile = await getProfile(view.profile);
      if (live) onBuilt(profile);
    };
    follow().catch(fail);
    return () => { live = false; };
    // One run per request for this municipality; onBuilt is the same handler throughout.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asked, municipality.code]);
  const start = () => { setError(null); setBuild(null); setAsked((count) => count + 1); };
  return { build, error, running: asked > 0 && !error && build?.status !== "done", start };
}

function BuildProgress({ build }: { build: BuildView | null }) {
  const fraction = build?.fraction ?? 0;
  return (
    <div className="run-progress">
      <div className="run-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(fraction * 100)}>
        <div style={{ width: `${fraction * 100}%` }} />
      </div>
      <p><strong>{build?.stage ?? "Starting"}</strong><span>{percent(fraction)}</span></p>
    </div>
  );
}

interface PlaceSearchProps {
  profiles: Profile[];
  explored: Explored | null;
  onExplore: (explored: Explored | null) => void;
  onChooseProfile: (profile: Profile) => void;
  /** A profile was assembled on demand: it joins the profiles and the explored municipality. */
  onBuilt: (profile: Profile) => void;
}

function Status({ explored, profiles, onChooseProfile, onBuilt }: { explored: Explored; profiles: Profile[]; onChooseProfile: (profile: Profile) => void; onBuilt: (profile: Profile) => void }) {
  const { municipality, boundary, error, profile } = explored;
  const reviewed = profiles.filter((item) => !item.experimental);
  const closest = boundary ? nearest(reviewed, centre(boundary)) : null;
  const fetching = useBuild(municipality, onBuilt);
  if (!profile && error) return <p className="note">Could not load the boundary of {municipality.name}: {error}</p>;
  if (!profile && !boundary) return <p className="note">Loading the boundary of {municipality.name}…</p>;
  return (
    <div className="explored">
      <p><strong>{municipality.name}, {municipality.uf}</strong></p>
      <div className="choices">
        {closest ? (
          <button type="button" className="choice" onClick={() => onChooseProfile(closest.profile)}>
            <strong>Use {closest.profile.municipality.name}, {closest.profile.municipality.uf}</strong>
            <small>Nearest reviewed profile · {KM.format(closest.km)} km away</small>
          </button>
        ) : null}
        {profile ? (
          <button type="button" className="choice" onClick={() => onChooseProfile(profile)}>
            <strong>Use {municipality.name}, {municipality.uf} <em className="badge">experimental</em></strong>
            <small>Local data, assembled automatically · not reviewed</small>
          </button>
        ) : fetching.running ? null : (
          <button type="button" className="choice" onClick={fetching.start}>
            <strong>Fetch the data of {municipality.name}, {municipality.uf} <em className="badge">experimental</em></strong>
            <small>Crop history, planting windows, weather and soil from public sources · under a minute</small>
          </button>
        )}
      </div>
      {fetching.running ? <BuildProgress build={fetching.build} /> : null}
      {fetching.error ? <p className="error">{fetching.error}</p> : null}
    </div>
  );
}

export function PlaceSearch({ profiles, explored, onExplore, onChooseProfile, onBuilt }: PlaceSearchProps) {
  const [query, setQuery] = useState("");
  const matches = useMatches(query);
  const pick = (municipality: Municipality) => {
    setQuery("");
    const profile = profiles.find((item) => item.municipality.ibge_code === municipality.code) ?? null;
    if (profile && !profile.experimental) {
      onExplore(null);
      onChooseProfile(profile);
      return;
    }
    onExplore({ municipality, boundary: null, error: null, profile });
    getMunicipalityBoundary(municipality.code).then(
      (boundary) => onExplore({ municipality, boundary, error: null, profile }),
      (failure: unknown) => onExplore({ municipality, boundary: null, error: failure instanceof Error ? failure.message : String(failure), profile }),
    );
  };
  return (
    <div className="place-search">
      <label>
        <span>Search any municipality in Brazil <em className="badge">experimental</em></span>
        <input type="search" value={query} placeholder="e.g. Rio Verde" autoComplete="off" role="combobox"
          aria-expanded={matches.length > 0} aria-controls="place-matches" onChange={(event) => setQuery(event.target.value)} />
      </label>
      {matches.length ? (
        <ul id="place-matches" role="listbox" className="place-matches">
          {matches.map((municipality) => (
            <li key={municipality.code} role="option" aria-selected="false">
              <button type="button" onClick={() => pick(municipality)}>{municipality.name} <small>{municipality.uf}</small></button>
            </li>
          ))}
        </ul>
      ) : null}
      {explored ? <Status key={explored.municipality.code} explored={explored} profiles={profiles}
        onChooseProfile={(profile) => { onExplore(null); onChooseProfile(profile); }}
        onBuilt={(profile) => { onBuilt(profile); onExplore({ ...explored, profile }); }} /> : null}
    </div>
  );
}
