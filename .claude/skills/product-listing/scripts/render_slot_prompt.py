#!/usr/bin/env python3
"""Fill {{product.*}} placeholders in a slot template's generation_request.prompt_json.
usage: render_slot_prompt.py <slot: 01|01gmc|02..06> <template.json> <run-folder>
Reads <run-folder>/product_reference_facts.json, writes <run-folder>/prompts/<slot>.prompt.json, prints it."""
import json, sys, pathlib
slot, tpl, run = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
facts = json.load(open(run / 'product_reference_facts.json'))['product']
def fill(o):
    if isinstance(o, str) and o.startswith('{{product.') and o.endswith('}}'):
        return facts[o[10:-2]]  # KeyError = missing product fact, stop
    if isinstance(o, dict): return {k: fill(v) for k, v in o.items()}
    if isinstance(o, list): return [fill(v) for v in o]
    return o
d = json.load(open(tpl))
gr = d['gmc_feed_rendition']['generation_request'] if slot == '01gmc' else d['generation_request']
s = json.dumps(fill(gr['prompt_json']), separators=(',', ':'), ensure_ascii=False)
assert '{{' not in s, 'unfilled placeholder'
(run / 'prompts').mkdir(exist_ok=True)
(run / 'prompts' / f'{slot}.prompt.json').write_text(s)
print(s)
