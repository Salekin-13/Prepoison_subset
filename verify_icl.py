"""verify_icl.py -- mechanical validation of the ICL asset examples.

Parses the strict-JSON blocks in icl_asset_examples.py (PARSED PORTS,
PARSED INTERNAL SIGNALS, EMITTED OUTPUT) and enforces the same contract the
pipeline enforces on real generations (cf. validate_primary in the notebook),
so the teaching material provably obeys its own rules:
  * parsed elements mirror the real parsed shape -- ports {entity, name, dir,
    type, function}; signals {entity, name, type, kind, function} with
    kind in {register, signal};
  * EMITTED OUTPUT is ONE object with exactly the keys {"IP", "Assets"};
  * every Asset RTL binds to a closed-set element name (ports UNION signals);
  * Entity is copied verbatim from that element's "entity" field;
  * Security Objective is exactly one of the three enum values;
  * all asset fields are non-empty strings;
  * each example is actually spliced into ICL_ASSET_EXAMPLES.

Run:  python verify_icl.py   (exit 0 = all examples pass)
"""
import json
import sys

from icl_asset_examples import (EXAMPLE_GPIO, EXAMPLE_GNG, EXAMPLE_AES,
                                ICL_ASSET_EXAMPLES)

PORT_KEYS   = {"entity", "name", "dir", "type", "function"}
SIGNAL_KEYS = {"entity", "name", "type", "kind", "function"}
ASSET_KEYS  = {"Asset Name", "Asset RTL", "Entity", "Functionality",
               "Security Objective", "Justification"}
OBJECTIVES  = {"Confidentiality", "Integrity", "Availability"}
# VHDL-derived examples say in/out; Verilog-derived ones say input/output.
DIRS        = {"in", "out", "inout", "buffer", "input", "output"}
KINDS       = {"register", "signal"}
# Examples differ in how they head the ports block; accept either spelling.
PORT_MARKERS = ("PARSED PORTS:", "PARSED I/O PORTS:")


def _block(text, marker):
    """Parse the JSON value ('[' or '{') that starts right after `marker`.

    `marker` may be a tuple of acceptable spellings; the first one present wins.
    """
    for m in ((marker,) if isinstance(marker, str) else marker):
        if m in text:
            i = text.index(m) + len(m)
            starts = [x for x in (text.find("[", i), text.find("{", i)) if x != -1]
            val, _ = json.JSONDecoder().raw_decode(text[min(starts):])
            return val
    raise ValueError(f"none of {marker} found")


def check(name, text, errs):
    e = lambda msg: errs.append(f"[{name}] {msg}")
    try:
        ports   = _block(text, PORT_MARKERS)
        signals = _block(text, "PARSED INTERNAL SIGNALS:")
        out     = _block(text, "EMITTED OUTPUT:")
    except (ValueError, json.JSONDecodeError) as ex:
        e(f"JSON block failed to parse: {ex}")
        return

    for p in ports:
        if set(p) != PORT_KEYS:
            e(f"port {p.get('name')}: keys {sorted(p)} != {sorted(PORT_KEYS)}")
        elif p["dir"] not in DIRS:
            e(f"port {p['name']}: bad dir '{p['dir']}'")
    for s in signals:
        if set(s) != SIGNAL_KEYS:
            e(f"signal {s.get('name')}: keys {sorted(s)} != {sorted(SIGNAL_KEYS)}")
        elif s["kind"] not in KINDS:
            e(f"signal {s['name']}: bad kind '{s['kind']}'")

    # Keyed by (entity, name), matching validate_primary() in the notebook. A bare-name
    # map would collapse legitimate duplicates: a multi-entity file reuses names across
    # its entities (tiny_aes has clk/key/state_in/state_out in several, neorv32_trng has
    # clk_i in all three), and keying on the name alone reports false ambiguity and false
    # Entity mismatches.
    closed = {}                                   # (entity, name) -> True
    names = {}                                    # name -> {entities}
    for el in ports + signals:
        nm, ent = el.get("name"), el.get("entity")
        closed[(ent, nm)] = True
        names.setdefault(nm, set()).add(ent)

    if not (isinstance(out, dict) and set(out) == {"IP", "Assets"}):
        e("EMITTED OUTPUT is not one object with exactly the keys IP+Assets")
        return
    if not (isinstance(out["IP"], str) and out["IP"].strip()):
        e("IP is not a non-empty string")
    if not isinstance(out["Assets"], list):
        e("Assets is not a list")
        return

    for a in out["Assets"]:
        if set(a) != ASSET_KEYS:
            e(f"asset '{a.get('Asset Name')}': keys {sorted(a)} != {sorted(ASSET_KEYS)}")
            continue
        r, ent = a["Asset RTL"], a["Entity"]
        if r not in names:
            e(f"ungrounded Asset RTL '{r}' (not in closed set)")
        elif (ent, r) not in closed:
            e(f"Entity mismatch for '{r}': '{ent}' not in {sorted(names[r])}")
        if a["Security Objective"] not in OBJECTIVES:
            e(f"bad Security Objective for '{r}': '{a['Security Objective']}'")
        for k in ASSET_KEYS:
            if not (isinstance(a[k], str) and a[k].strip()):
                e(f"empty/non-string field '{k}' for '{r}'")

    print(f"  {name:5s}: {len(ports)} ports, {len(signals)} signals, "
          f"{len(out['Assets'])} assets emitted")


def main():
    errs = []
    for name, text in (("GPIO", EXAMPLE_GPIO),
                       ("GNG",  EXAMPLE_GNG),
                       ("AES",  EXAMPLE_AES)):
        check(name, text, errs)
        if text not in ICL_ASSET_EXAMPLES:
            errs.append(f"[{name}] example not spliced into ICL_ASSET_EXAMPLES")

    if errs:
        print(f"\nFAIL -- {len(errs)} issue(s):")
        for x in errs:
            print("  -", x)
        sys.exit(1)
    print("PASS -- all ICL examples obey the closed-set/entity/output contract")


if __name__ == "__main__":
    main()
