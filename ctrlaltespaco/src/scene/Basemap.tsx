import { useEffect, useMemo } from "react";
import { SRGBColorSpace, TextureLoader } from "three";
import { tilePlacement, tileUrl, type Tile } from "../geo/mercator.ts";

interface TilePlaneProps {
  tile: Tile;
  template: string;
  lift: number;
}

/** One map tile lying on the ground, north towards -z. */
function TilePlane({ tile, template, lift }: TilePlaneProps) {
  const url = tileUrl(template, tile);
  const texture = useMemo(() => {
    const loaded = new TextureLoader().load(url);
    loaded.colorSpace = SRGBColorSpace;
    return loaded;
  }, [url]);
  useEffect(() => () => texture.dispose(), [texture]);
  const { size, centre } = tilePlacement(tile);
  return (
    <mesh position={[centre[0], lift, centre[1]]} rotation-x={-Math.PI / 2}>
      <planeGeometry args={[size, size]} />
      <meshBasicMaterial map={texture} toneMapped={false} />
    </mesh>
  );
}

interface BasemapProps {
  tiles: Tile[];
  template: string;
  /** Height above the ground, so finer tiles sit on top of coarser ones. */
  lift?: number;
}

export function Basemap({ tiles, template, lift = 0 }: BasemapProps) {
  return (
    <group>
      {tiles.map((tile) => (
        <TilePlane key={`${tile.zoom}/${tile.x}/${tile.y}`} tile={tile} template={template} lift={lift} />
      ))}
    </group>
  );
}
