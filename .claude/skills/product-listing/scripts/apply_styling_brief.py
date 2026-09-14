#!/usr/bin/env python3
"""Validate <run>/styling_brief.json and write its decisions into <run>/product_reference_facts.json.
usage: apply_styling_brief.py <run-folder> [--recent profiles/ondine/recent-settings.json]
Every decision needs a non-empty `because`; the lifestyle setting may not repeat any of the last three recorded settings.
poses carries one stance per model slot (01, 02, 03, 05); near-duplicate wording between two slots is refused.
ponytail: schema check by key presence, not JSON Schema; upgrade if a second store profile needs different fields."""
import json, sys, pathlib, re
run = pathlib.Path(sys.argv[1]); recent_path = pathlib.Path(sys.argv[sys.argv.index('--recent') + 1]) if '--recent' in sys.argv else None
b = json.load(open(run / 'styling_brief.json'))
for k in ('listing_date', 'season_on_sale', 'occasions', 'uk_context', 'competitor_styling_evidence'):
    assert b['inputs'].get(k), f'missing input {k}'
d = b['decisions']
for k in ('footwear', 'accessories', 'lifestyle_setting', 'movement', 'light'):
    assert d.get(k, {}).get('value') and d[k].get('because'), f'decision {k} needs value and because'
POSE_SLOTS = ('01', '02', '03', '05')  # the four model slots; the GMC square reuses 01, slots 04/06 have no full-body pose
poses = d.get('poses', {})
for s in POSE_SLOTS:
    assert poses.get(s, {}).get('value') and poses[s].get('because'), f'poses.{s} needs value and because'
# ponytail: word-overlap check, not semantics; two slots that share most of their pose wording read as the same picture (Ilias 2026-09-03)
words = lambda v: {w for w in re.findall(r'[a-z]+', v.lower()) if len(w) > 3}
for i, a in enumerate(POSE_SLOTS):
    for c in POSE_SLOTS[i + 1:]:
        wa, wc = words(poses[a]['value']), words(poses[c]['value'])
        assert len(wa & wc) / len(wa | wc) < 0.45, f'poses {a} and {c} are near-duplicates; every slide needs its own stance'
if recent_path and recent_path.exists():
    recent = json.load(open(recent_path))
    last3 = [r for r in recent if r.get('product') != b.get('product_handle')][-3:]  # a re-run never collides with itself
    assert d['lifestyle_setting']['value'] not in [r['setting'] for r in last3], 'setting repeats one of the last three products'
    TYPES = {'sandal','boot','loafer','flat','trainer','sneaker','heel','mule','court','ballet','brogue','espadrille','clog','slide','pump','hoop','stud','pendant','chain','necklace','bracelet','earring','none'}
    key = lambda v: frozenset(w.rstrip('s') for w in re.findall(r'[a-z]+', v.lower()) if w.rstrip('s') in TYPES)  # ponytail: the type words, order-free
    assert key(d['footwear']['value']) not in [key(r.get('footwear', '')) for r in last3], 'footwear repeats one of the last three products'
    assert key(d['accessories']['value']) not in [key(r.get('accessories', '')) for r in last3], 'accessories repeat one of the last three products'
facts_path = run / 'product_reference_facts.json'; f = json.load(open(facts_path)); p = f['product']
p['model']['footwear'] = d['footwear']['value']
p['model']['accessories'] = 'none'
p['model_styled'] = dict(p['model'], accessories=d['accessories']['value'])
p['lifestyle_setting'] = d['lifestyle_setting']['value'] + ' ' + d['light']['value']
p['movement'] = d['movement']['value']
for s in POSE_SLOTS:
    p[f'pose_{s}'] = poses[s]['value']
p['styling_brief_applied'] = b['inputs']['listing_date']
json.dump(f, open(facts_path, 'w'), indent=1, ensure_ascii=False)
if recent_path:
    recent = json.load(open(recent_path)) if recent_path.exists() else []
    recent = [r for r in recent if r.get('product') != b.get('product_handle')]  # re-running a product replaces its own entry
    recent.append({'product': b.get('product_handle'), 'date': b['inputs']['listing_date'], 'setting': d['lifestyle_setting']['value'], 'footwear': d['footwear']['value'], 'accessories': d['accessories']['value']})
    json.dump(recent, open(recent_path, 'w'), indent=1, ensure_ascii=False)
print('brief applied:', {k: (d[k]['value'][:60] if k != 'poses' else {s2: poses[s2]['value'][:40] for s2 in POSE_SLOTS}) for k in d})
