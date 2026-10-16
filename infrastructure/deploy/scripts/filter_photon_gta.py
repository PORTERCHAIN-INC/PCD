"""Keep Photon dump places within 155 km of Toronto (GTA ±150 km plus margin)."""
import json, math, sys
HUB = (43.6532, -79.3832)
def km(lat, lng):
    p1, p2 = math.radians(HUB[0]), math.radians(lat)
    a = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lng-HUB[1])/2)**2
    return 12742 * math.asin(math.sqrt(a))
kept = dropped = 0
for line in sys.stdin:
    if '"type":"Place"' not in line[:40]:
        sys.stdout.write(line); continue
    d = json.loads(line)
    c = d["content"]
    keep = [p for p in c if p.get("centroid") and km(p["centroid"][1], p["centroid"][0]) <= 155]
    if keep:
        d["content"] = keep; sys.stdout.write(json.dumps(d, separators=(",", ":")) + "\n"); kept += 1
    else:
        dropped += 1
print(f"kept={kept} dropped={dropped}", file=sys.stderr)
