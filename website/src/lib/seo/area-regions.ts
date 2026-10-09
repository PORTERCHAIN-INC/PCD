/** GTA regions used to group the area selector (Toronto first, then by direction). */
export const AREA_REGIONS = [
  "Toronto",
  "Peel",
  "York",
  "Durham",
  "Halton",
  "Hamilton & Niagara",
] as const;
export type AreaRegion = (typeof AREA_REGIONS)[number];

const REGION_OF: Record<string, AreaRegion> = {
  "downtown-toronto": "Toronto",
  "east-york-midtown": "Toronto",
  "west-toronto": "Toronto",
  "north-york": "Toronto",
  scarborough: "Toronto",
  etobicoke: "Toronto",
  mississauga: "Peel",
  brampton: "Peel",
  vaughan: "York",
  markham: "York",
  "richmond-hill": "York",
  "newmarket-aurora": "York",
  "pickering-ajax": "Durham",
  "oshawa-whitby": "Durham",
  oakville: "Halton",
  burlington: "Halton",
  milton: "Halton",
  hamilton: "Hamilton & Niagara",
};

export function areaRegion(slug: string): AreaRegion {
  const r = REGION_OF[slug];
  if (!r) throw new Error(`area ${slug} has no region — add it to REGION_OF`);
  return r;
}

export type AreaLink = { slug: string; href: string; label: string; note?: string };

export function groupByRegion(links: AreaLink[]) {
  return AREA_REGIONS.map((region) => ({
    region,
    links: links.filter((l) => areaRegion(l.slug) === region),
  })).filter((g) => g.links.length);
}
