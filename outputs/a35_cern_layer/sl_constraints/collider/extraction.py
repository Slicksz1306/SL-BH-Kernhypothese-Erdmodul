"""Bounded, offline adapters. Source bytes are checked before interpretation."""
from copy import deepcopy
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
from ..common.types import ContractError
from ..common.provenance import canonical_bytes
from .contracts import exact

PARSER_VERSION = '1.0.0'
MAX_BYTES = 50 * 1024 * 1024


def check_raw(payload, source):
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_BYTES:
        raise ContractError('RESOURCE_LIMIT')
    if sha256(payload).hexdigest() != source['sha256']:
        raise ContractError('HASH_MISMATCH')


def parse_json(payload):
    if len(payload) > MAX_BYTES:
        raise ContractError('RESOURCE_LIMIT')
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ContractError('PARSE_ERROR', 'duplicate key')
            result[k] = v
        return result
    def bad_constant(value):
        raise ContractError('PARSE_ERROR', value)
    try:
        data = json.loads(payload, object_pairs_hook=pairs, parse_float=str, parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError('PARSE_ERROR', type(exc).__name__) from exc
    count = 0
    def walk(value, depth=0):
        nonlocal count
        count += 1
        if depth > 32 or count > 1000000:
            raise ContractError('RESOURCE_LIMIT')
        if isinstance(value, dict):
            for v in value.values():
                walk(v, depth + 1)
        elif isinstance(value, list):
            for v in value:
                walk(v, depth + 1)
    walk(data)
    return data


def parse_cell(value):
    if type(value) not in (str, int):
        raise ContractError('PARSE_ERROR', 'non-scalar cell')
    text = str(value)
    if re.fullmatch(r'[<>]=?\s*[0-9.]+', text):
        return None, 'CENSORED'
    if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', text) or len(text) > 128:
        raise ContractError('PARSE_ERROR', 'not an exact decimal')
    exact(text)
    return text, 'PARSED'


def _envelope(source, kind):
    return dict(schema_version='1.0.0', parser_version=PARSER_VERSION, format_id=kind,
                source_id=source['source_id'], source_version=source['source_version'],
                source_hash=source['sha256'], purpose=source['purpose'])


def extract_hepdata(payload, source, binding, confirmed_identity):
    """Caller supplies independently verified record/version/table identity.

    Parsing alone does NOT confer ACQUIRED/ACCEPTED status; cross-check remains required.
    The complete decoded table retains original qualifiers, axes and uncertainties.
    """
    check_raw(payload, source)
    data = parse_json(payload)
    if any(type(binding.get(k)) is not str or not binding[k].strip() for k in ('record_id', 'version')):
        raise ContractError('SOURCE_CHANGED', 'verified identity required')
    if (binding['record_id'] != source.get('hepdata_record_id') or
            binding['version'] != source.get('hepdata_version')):
        raise ContractError('SOURCE_CHANGED', 'binding differs from source record')
    if binding.get('record_id') != confirmed_identity.get('record_id') or binding.get('version') != confirmed_identity.get('version'):
        raise ContractError('SOURCE_CHANGED')
    if (binding.get('table_id') not in confirmed_identity.get('table_ids', []) or
            binding.get('table_id') not in source.get('table_ids', [])):
        raise ContractError('TABLE_NOT_FOUND')
    if binding.get('limit_role') not in ('OBSERVED', 'EXPECTED'):
        raise ContractError('LIMIT_ROLE_REQUIRED')
    try:
        variables = data['dependent_variables']
        selected = [v for v in variables if v['header']['name'] == binding['dependent_name']]
        if len(selected) != 1:
            raise ContractError('PARSE_ERROR', 'ambiguous dependent variable')
        variable = selected[0]
        if variable['header'].get('units', '1') != binding['unit']:
            raise ContractError('UNIT_MISMATCH')
        qualifiers = variable['qualifiers']
        names = [q['name'] for q in qualifiers]
        if len(set(names)) != len(names):
            raise ContractError('BENCHMARK_MISMATCH', 'duplicate qualifiers')
        actual = {q['name']: str(q['value']) for q in qualifiers}
        if not binding['qualifiers'] or any(actual.get(k) != v for k, v in binding['qualifiers'].items()):
            raise ContractError('BENCHMARK_MISMATCH')
        values = variable['values']
        if not values or not data['independent_variables'] or any(len(v['values']) != len(values) for v in data['independent_variables']):
            raise ContractError('PARSE_ERROR', 'empty or inconsistent table axes')
        cells = []
        for i, cell in enumerate(values):
            value, status = parse_cell(cell['value'])
            cells.append(dict(original_cell_text=str(cell['value']), parsed_value=value,
                              original_unit=binding['unit'], interpretation_status=status,
                              locator=f"{binding['table_id']}/dependent_variables/{variables.index(variable)}/values/{i}"))
    except (KeyError, TypeError, IndexError) as exc:
        raise ContractError('PARSE_ERROR', 'invalid HEPData structure') from exc
    result = {**_envelope(source, 'hepdata-json-v1'), 'binding': deepcopy(binding), 'table': data, 'cells': cells}
    result['artifact_id'] = 'extract_' + sha256(canonical_bytes(result)).hexdigest()[:24]
    return result


class _Table(HTMLParser):
    def __init__(self, identity):
        super().__init__(convert_charrefs=True)
        self.identity, self.rows, self.spans = identity, [], []
        self.active = False
        self.table_depth = 0
        self.found = 0
        self.row = None
        self.cell = None
        self.capture_tag = None
        self.math_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id') == self.identity:
            self.active = True
            self.capture_tag = tag
            self.found += 1
        if not self.active:
            return
        if tag == 'table':
            self.table_depth += 1
        if tag == 'tr':
            self.row = []
        if tag in ('td', 'th'):
            self.cell = []
            self.spans.append({'rowspan': attrs.get('rowspan', '1'), 'colspan': attrs.get('colspan', '1')})
        if tag == 'math':
            if self.cell is not None and attrs.get('alttext'):
                self.cell.append(attrs['alttext'])
            self.math_depth += 1

    def handle_data(self, data):
        if self.active and self.cell is not None and not self.math_depth:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag == 'math':
            self.math_depth = max(0, self.math_depth - 1)
        if tag in ('td', 'th') and self.cell is not None:
            if self.row is not None:
                self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == 'table':
            self.table_depth -= 1
        if tag == self.capture_tag and self.table_depth <= 0:
            self.active = False


def extract_html_table(payload, source, table_id):
    check_raw(payload, source)
    parser = _Table(table_id)
    try:
        parser.feed(payload.decode('utf-8'))
        parser.close()
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ContractError('PARSE_ERROR') from exc
    if parser.found != 1 or not parser.rows:
        raise ContractError('TABLE_NOT_FOUND', table_id)
    if sum(map(len, parser.rows)) > 1000000:
        raise ContractError('RESOURCE_LIMIT')
    result = {**_envelope(source, 'reviewed-html-table-v1'), 'table_id': table_id,
              'rows': parser.rows, 'cell_spans': parser.spans,
              'review_status': 'PROPOSED'}
    result['artifact_id'] = 'extract_' + sha256(canonical_bytes(result)).hexdigest()[:24]
    return result


def extract_paragraph(payload, source, paragraph_id):
    """Exact single <p id=...> fragment; no positional or numeric inference."""
    check_raw(payload, source)
    key = re.escape(paragraph_id.encode('utf-8'))
    matches = list(re.finditer(rb'<p\b[^>]*\bid="' + key + rb'"[^>]*>.*?</p>', payload, re.DOTALL))
    if len(matches) != 1:
        raise ContractError('PARSE_ERROR', 'paragraph absent or ambiguous: ' + paragraph_id)
    match = matches[0]
    result = {**_envelope(source, 'reviewed-html-paragraph-v1'),
              'locator': paragraph_id, 'original_html': match.group().decode('utf-8'),
              'byte_start': match.start(), 'byte_end': match.end(), 'review_status': 'PROPOSED'}
    result['artifact_id'] = 'extract_' + sha256(canonical_bytes(result)).hexdigest()[:24]
    return result
