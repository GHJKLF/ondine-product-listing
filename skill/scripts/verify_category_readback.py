#!/usr/bin/env python3
"""Fail closed on actual category/metafield readback before completion or sheet Draft."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(expected, readback):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    try:
        require(expected.get('source_inventory_reviewed') is True, 'Source-supported field inventory was not reviewed')
        fields = expected['fields']
        require(isinstance(fields, list) and bool(fields), 'Expected category fields must not be empty')
        require(not readback.get('errors'), 'GraphQL returned errors')
        data = readback['data']
        product = data['product']
        require(bool(expected['shop_id']) and data['shop']['id'] == expected['shop_id'], 'Wrong shop')
        require(bool(expected['product_id']) and product['id'] == expected['product_id'], 'Wrong product')
        require(product['status'] == 'DRAFT', 'Product is not DRAFT')
        require(bool(expected['category_id']) and product['category']['id'] == expected['category_id'], 'Missing or wrong taxonomy category')
        require(bool(expected['product_updated_at']) and product['updatedAt'] == expected['product_updated_at'], 'Readback does not match the final-write revision')
        connection = product['metafields']
        require(connection['pageInfo']['hasNextPage'] is False, 'Metafield readback is incomplete')
        nodes = connection['nodes']
        actual = {(m['namespace'], m['key']): m for m in nodes}
        require(len(actual) == len(nodes), 'Duplicate readback fields')
        seen = set()
        for field in fields:
            key = field['key']
            require(key not in seen, 'Duplicate expected field: ' + key)
            seen.add(key)
            require(isinstance(field['source_evidence'], str) and bool(field['source_evidence'].strip()), 'Missing source evidence: ' + key)
            want = field['values']
            require(isinstance(want, list) and bool(want) and all(isinstance(v, str) and v for v in want), 'Empty expected values: ' + key)
            m = actual.get(('shopify', key))
            if m is None:
                errors.append('Missing category metafield: ' + key)
                continue
            require(m['type'] == field['type'], 'Wrong type: ' + key)
            value = json.loads(m['value']) if m['type'].startswith('list.') else [m['value']]
            require(isinstance(value, list) and sorted(value) == sorted(want), 'Wrong saved values: ' + key)
            if 'metaobject_reference' in m['type']:
                refs = m['references']
                require(refs['pageInfo']['hasNextPage'] is False, 'Incomplete display-value references: ' + key)
                resolved = {n['id']: n['displayName'] for n in refs['nodes']}
                require(len(resolved) == len(refs['nodes']), 'Duplicate display references: ' + key)
                require(set(resolved) == set(want), 'Unresolved saved references: ' + key)
                require(resolved == field['display_values'] and all(resolved.values()), 'Wrong display values: ' + key)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        errors.append('Missing or malformed verification evidence: ' + str(exc))
    return {'ok': not errors, 'category_verified': not errors,
            'completion_allowed': not errors, 'sheet_draft_allowed': not errors,
            'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('expected', type=Path)
    parser.add_argument('readback', type=Path)
    args = parser.parse_args()
    try:
        expected_bytes, readback_bytes = args.expected.read_bytes(), args.readback.read_bytes()
        result = verify(json.loads(expected_bytes), json.loads(readback_bytes))
        result.update(expected_sha256=hashlib.sha256(expected_bytes).hexdigest(),
                      readback_sha256=hashlib.sha256(readback_bytes).hexdigest())
    except (OSError, ValueError) as exc:
        result = {'ok': False, 'completion_allowed': False, 'sheet_draft_allowed': False, 'errors': [str(exc)]}
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
