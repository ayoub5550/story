"""Validate shot lists: durations, tokens, refs, required fields. Prints a timecoded table.
Usage: python tools/validate_shots.py [--part 1|2] [--quiet]"""
import sys, argparse
from common import ROOT, characters, locations, parts, iter_shots, tc

PART_LEN = {1: 600, 2: 720}
PART_START = {1: 0, 2: 600}
METHODS = {"KF2V", "T2V", "PX", "HF"}
STATUSES = {"todo", "kf_done", "clip_done", "approved"}
REQ = ["id", "dur", "method", "chars", "action", "status"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", type=int); ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    chars, locs = characters(), locations()
    errors, warns = [], []
    for c in chars.values():
        if c.get("ref") and not (ROOT / c["ref"]).exists():
            errors.append(f"missing ref file {c['ref']} for {c['token']}")
    for p, doc in parts().items():
        if a.part and p != a.part:
            continue
        t = PART_START[p]; total = 0; ids = set()
        for sc in doc["scenes"]:
            shots = sc.get("shots") or []
            if not shots:
                warns.append(f"P{p} {sc['scene']}: no shots yet (target {sc.get('target_dur')} s)")
                total += sc.get("target_dur", 0); t += sc.get("target_dur", 0); continue
            sdur = sum(s["dur"] for s in shots)
            if sc.get("target_dur") and sdur != sc["target_dur"]:
                errors.append(f"{sc['scene']}: shots sum {sdur}s != target_dur {sc['target_dur']}s")
            for lt in ([sc["loc"]] if isinstance(sc.get("loc"), str) else sc.get("loc", [])):
                if lt not in locs: errors.append(f"{sc['scene']}: unknown location {lt}")
            for s in shots:
                for f in REQ:
                    if f not in s: errors.append(f"{s.get('id')}: missing field {f}")
                if s["id"] in ids: errors.append(f"duplicate id {s['id']}")
                ids.add(s["id"])
                if s["method"] not in METHODS: errors.append(f"{s['id']}: bad method {s['method']}")
                if s["status"] not in STATUSES: errors.append(f"{s['id']}: bad status {s['status']}")
                if not 2 <= s["dur"] <= 15: warns.append(f"{s['id']}: unusual duration {s['dur']}s")
                for ch in s["chars"]:
                    if ch not in chars: errors.append(f"{s['id']}: unknown char {ch}")
                    elif s["method"] == "KF2V" and not chars[ch].get("ref"):
                        warns.append(f"{s['id']}: {ch} has no ref sheet yet (generate before producing)")
                if not a.quiet:
                    print(f"{tc(t)}–{tc(t+s['dur'])}  {s['id']:7} {s['dur']:>3}s {s['method']:5} {s['status']:9} {','.join(s['chars'])}")
                t += s["dur"]
            total += sdur
        print(f"== Part {p}: {total}s ({tc(total)}) / expected {PART_LEN[p]}s")
        if total != PART_LEN[p]:
            errors.append(f"Part {p} length {total}s != {PART_LEN[p]}s")
    for w in warns: print("WARN ", w)
    for e in errors: print("ERROR", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
