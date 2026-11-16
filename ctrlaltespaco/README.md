# ctrlaltespaco

Field Shift front: TypeScript, React, React Three Fiber and GSAP over a real basemap (NASA GIBS tiles) and IBGE boundaries.
It only talks to the Field Shift API; every number on screen comes from `POST /runs`.

```bash
npm install
npm run dev        # http://localhost:5173, API calls forwarded to FIELD_SHIFT_API (see .env.example)
npm test           # unit tests of the pure modules
npm run build      # type-check and build into dist/
```

To serve the build from the API itself: `FIELD_SHIFT_WEB_DIR=ctrlaltespaco/dist uv run uvicorn --factory field_shift.api:create_app`.

The map needs the API up, and the API needs MongoDB loaded with the profiles (`python -m field_shift.ingest --mongo ...`);
`docker run -p 8000:8000 field-shift` starts all three. State and municipality boundaries are files under `data/geo`,
served by `/geo/*`; the front never calls IBGE.

Runtime settings (basemap tiles, CMS address, run size) are not baked into the build. The front reads them from the API's
`GET /config`, which the deployment sets with `FIELD_SHIFT_*` environment variables.

| Folder | Role |
|---|---|
| `src/api.ts`, `src/types.ts` | Typed API client |
| `src/geo` | Web Mercator and tile arithmetic |
| `src/scene` | The 3D map: basemap, boundaries, sites, scenario columns, camera |
| `src/state` | The playhead (simulation time), animated by GSAP |
| `src/ui` | Panel: rotation editor, time bar, scenario cards, trajectory strips |
| `src/useFieldShift.ts`, `src/scenarios.ts` | Loading, selection and the scenarios sent to the engine |
