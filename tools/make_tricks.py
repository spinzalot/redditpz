"""Builds notes.json: ride notes for each class, in the shape of sourdoughrides.com's ride_notes
(type code + text), so the page reads them the same way once they come from Sean's database.
Today the only notes are Recommendations (spinzalot's interval tips), worked out from the
interval data in his program designer export.

    python3 tools/make_tricks.py path/to/designer-data.json

Each rule looks at a class's main set (warm-up and cool-down trimmed) and returns the start times
(seconds into the class) where its trick applies. Add a rule: write a function and list it in RULES.
"""
import json, sys

WARMUP, COOLDOWN = 300, 300          # seconds trimmed from each end before looking for patterns

def blocks(c):
    """The class's target blocks as (start, seconds, zone), with back-to-back blocks of one zone merged."""
    s, out = c['seg'], []
    for i in range(0, len(s), 3):
        start, end, z = s[i], s[i + 1], s[i + 2]
        if out and out[-1][2] == z and start <= out[-1][0] + out[-1][1] + 1:
            st, _, _ = out[-1]; out[-1] = (st, end - st + 1, z)
        else:
            out.append((start, end - start + 1, z))
    return out

def main_set(c):
    b = blocks(c)
    end = b[-1][0] + b[-1][1]
    return [x for x in b if x[0] >= WARMUP and x[0] + x[1] <= end - COOLDOWN + 60]

# ---------- rules: each returns a list of start times (empty = doesn't apply) ----------

def z3_is_recovery(m):
    """3+ minutes of Z3 that sit between harder (Z4+) efforts."""
    hits = [x for i, x in enumerate(m) if x[2] == 3 and 0 < i < len(m) - 1 and m[i - 1][2] >= 4 and m[i + 1][2] >= 4]
    return [hits[0][0]] if sum(x[1] for x in hits) >= 180 else []

def long_z4(m):
    """Z4 blocks of 8 minutes or more."""
    return [x[0] for x in m if x[2] == 4 and x[1] >= 480]

def long_z5(m):
    """Z5 blocks of 3 minutes or more."""
    return [x[0] for x in m if x[2] == 5 and x[1] >= 180]

RULES = [
    ('z3rec', 'Zone 3 is recovery.', z3_is_recovery),
    ('z4breathe', 'Long Z4: focus on breathing smoothly.', long_z4),
    ('z5cadence', 'Long Z5: hold your power steady and play with other things, like cadence.', long_z5),
]

def main(path):
    d = json.load(open(path))
    classes, counts, multi = {}, {r[0]: 0 for r in RULES}, {}
    for c in d['classes']:
        if not c.get('seg'):
            continue
        m = main_set(c)
        found = []
        for rid, _, fn in RULES:
            at = fn(m)
            if at:
                found.append([rid, at]); counts[rid] += 1
        if found:
            found.sort(key=lambda f: f[1][0])          # in ride order
            classes[c['id']] = found
            multi[len(found)] = multi.get(len(found), 0) + 1
    texts = {rid: text for rid, text, _ in RULES}
    notes = {cid: [{'type': 'recommendation', 'text': texts[rid], 'at': at} for rid, at in found] for cid, found in classes.items()}
    out = {'source': 'sourdoughrides.com program designer data', 'snapshot': d.get('snapshot'), 'classes': notes}
    json.dump(out, open('notes.json', 'w'), separators=(',', ':'))
    print('classes with tricks:', len(classes), '| per rule:', counts, '| by number of tricks:', dict(sorted(multi.items())))

if __name__ == '__main__':
    main(sys.argv[1])
