import type { Journey, World } from "../useFieldShift.ts";

const STATE_NAMES: Record<string, string> = { RO: "Rondônia", SP: "São Paulo", MG: "Minas Gerais" };

export function LocationStep({ journey, world }: { journey: Journey; world: World }) {
  const chosen = journey.place?.profile.id;
  return (
    <section>
      <h2>Where is your farm?</h2>
      <p className="lead">Choose your municipality, here or on the map.</p>
      <div className="choices">
        {world.profiles.map((profile) => (
          <button key={profile.id} type="button" className="choice" aria-pressed={profile.id === chosen} onClick={() => journey.choosePlace(profile)}>
            <strong>{profile.municipality.name}</strong>
            <small>{STATE_NAMES[profile.municipality.uf] ?? profile.municipality.uf} · {profile.municipality.uf}</small>
          </button>
        ))}
      </div>
      <div className="actions">
        <span />
        <button type="button" className="primary" disabled={!journey.place} onClick={() => journey.go("crop")}>Continue</button>
      </div>
    </section>
  );
}
