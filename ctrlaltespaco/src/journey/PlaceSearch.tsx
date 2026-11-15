/** Experimental: search any Brazilian municipality (IBGE list), show its real boundary on the map, and say whether
 *  it has a complete profile to simulate. Only Ariquemes, Franca and Varginha do for now. */

import { useEffect, useState } from "react";
import { getMunicipalityBoundary, searchMunicipalities } from "../api.ts";
import { centre, nearest } from "../map/places.ts";
import type { Boundary, Municipality, Profile } from "../types.ts";

const DEBOUNCE_MS = 250;
const KM = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

/** A municipality picked in the search, with its boundary once IBGE answers. */
export interface Explored {
  municipality: Municipality;
  boundary: Boundary | null;
  error: string | null;
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

interface PlaceSearchProps {
  profiles: Profile[];
  explored: Explored | null;
  onExplore: (explored: Explored | null) => void;
  onChooseProfile: (profile: Profile) => void;
}

function Status({ explored, profiles, onChooseProfile }: { explored: Explored; profiles: Profile[]; onChooseProfile: (profile: Profile) => void }) {
  const { municipality, boundary, error } = explored;
  if (error) return <p className="note">Could not load the boundary of {municipality.name}: {error}</p>;
  if (!boundary) return <p className="note">Loading the boundary of {municipality.name} from IBGE…</p>;
  const closest = nearest(profiles, centre(boundary));
  return (
    <div className="explored">
      <p><strong>{municipality.name}, {municipality.uf}</strong> has no complete profile yet. A simulation needs its climate,
        soil, crop history, planting windows and production costs assembled and checked; so far that is done for three
        municipalities.</p>
      {closest ? (
        <button type="button" className="choice" onClick={() => onChooseProfile(closest.profile)}>
          <strong>Use {closest.profile.municipality.name}, {closest.profile.municipality.uf}</strong>
          <small>Nearest complete profile · {KM.format(closest.km)} km away</small>
        </button>
      ) : null}
    </div>
  );
}

export function PlaceSearch({ profiles, explored, onExplore, onChooseProfile }: PlaceSearchProps) {
  const [query, setQuery] = useState("");
  const matches = useMatches(query);
  const pick = (municipality: Municipality) => {
    setQuery("");
    const profile = profiles.find((item) => item.municipality.ibge_code === municipality.code);
    if (profile) {
      onExplore(null);
      onChooseProfile(profile);
      return;
    }
    onExplore({ municipality, boundary: null, error: null });
    getMunicipalityBoundary(municipality.code).then(
      (boundary) => onExplore({ municipality, boundary, error: null }),
      (failure: unknown) => onExplore({ municipality, boundary: null, error: failure instanceof Error ? failure.message : String(failure) }),
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
      {explored ? <Status explored={explored} profiles={profiles} onChooseProfile={(profile) => { onExplore(null); onChooseProfile(profile); }} /> : null}
    </div>
  );
}
