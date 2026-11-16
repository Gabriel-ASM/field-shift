import type { Profile } from "../types.ts";
import type { Journey, World } from "../useFieldShift.ts";
import { PlaceSearch, type Explored } from "./PlaceSearch.tsx";

const STATE_NAMES: Record<string, string> = { RO: "Rondônia", SP: "São Paulo", MG: "Minas Gerais" };

const HECTARES = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

interface LocationStepProps {
  journey: Journey;
  world: World;
  area: number | null;
  explored: Explored | null;
  onExplore: (explored: Explored | null) => void;
  /** A profile assembled on demand from the search. */
  onBuilt: (profile: Profile) => void;
}

export function LocationStep({ journey, world, area, explored, onExplore, onBuilt }: LocationStepProps) {
  const chosen = journey.place?.profile.id;
  const picked = journey.place?.profile;
  return (
    <section>
      <p className="kicker">Let's start with your land</p>
      <h2>Where is your farm?</h2>
      <p className="lead">Select a municipality here or on the map. We consider the local climate, soil and most common crops of the region.</p>
      <div className="choices">
        {world.profiles.filter((profile) => !profile.experimental).map((profile) => (
          <button key={profile.id} type="button" className="choice" aria-pressed={profile.id === chosen} onClick={() => { onExplore(null); journey.choosePlace(profile); }}>
            <strong>{profile.municipality.name}</strong>
            <small>{STATE_NAMES[profile.municipality.uf] ?? profile.municipality.uf} · {profile.municipality.uf}</small>
          </button>
        ))}
      </div>
      <PlaceSearch profiles={world.profiles} explored={explored} onExplore={onExplore} onChooseProfile={journey.choosePlace} onBuilt={onBuilt} />
      {picked?.experimental ? (
        <p className="note">Selected: <strong>{picked.municipality.name}, {picked.municipality.uf}</strong>
          <em className="badge">experimental</em> — data assembled automatically, not reviewed yet.</p>
      ) : null}
      {area !== null && <p className="note">Your field: {HECTARES.format(area)} ha. Results are per hectare and use municipal data; the outline does not change them yet.</p>}
      <div className="actions">
        <span />
        <button type="button" className="primary" disabled={!journey.place} onClick={() => journey.go("crop")}>Continue</button>
      </div>
    </section>
  );
}
