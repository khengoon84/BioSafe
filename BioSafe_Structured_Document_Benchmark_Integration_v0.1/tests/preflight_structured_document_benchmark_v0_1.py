#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'src'))
from structured_document_benchmark_adapter_v0_1 import BioSafeStructuredBenchmarkAdapterV01

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-root', default=str(ROOT))
    ap.add_argument('--docs', default=None)
    args = ap.parse_args()
    project = Path(args.project_root)
    docs_dir = Path(args.docs) if args.docs else project/'data/context_documents_v0_2'
    adapter = BioSafeStructuredBenchmarkAdapterV01(project)

    sop = (docs_dir/'SOP-03_LMO_Contained_Use.txt').read_text(encoding='utf-8')
    prop = (docs_dir/'PROP-01_LMO_Research_Proposal.txt').read_text(encoding='utf-8')
    form = (docs_dir/'FORM-E-SYNTHETIC-COMPLETED.txt').read_text(encoding='utf-8')

    sop_a = adapter.analyse('SOP-03_LMO_Contained_Use.txt', sop)
    prop_a = adapter.analyse('PROP-01_LMO_Research_Proposal.txt', prop)
    form_a = adapter.analyse('FORM-E-SYNTHETIC-COMPLETED.txt', form)

    assert any('appropriate ppe' in x.lower() for x in sop_a['extraction_notes'])
    assert any(m['field'] == 'host_organism' for m in prop_a['missing_fields'])
    assert any(m['field'] == 'insert_or_construct' for m in prop_a['missing_fields'])

    packet = adapter.build_packet('Compare completed Form E with proposal.', [prop_a, form_a], [], 'COMPARE_NO_SILENT_RESOLUTION')
    fields = {x['field'] for x in packet['contradictions']}
    assert 'project_title' in fields
    assert 'project_duration' in fields
    assert 'host_organism' in fields
    assert 'construct_identity' in fields
    assert 'proposed_start' not in fields, 'Identical proposed start should not be flagged.'
    assert 'institution' not in fields, 'Identical institution should not be flagged.'

    print('BioSafe structured document preflight: PASS')
    print('Vague statements:', len(sop_a['extraction_notes']))
    print('PROP-01 missing fields:', [x['field'] for x in prop_a['missing_fields']])
    print('PROP-01 vs Form E findings:', [(x['field'], x['status']) for x in packet['contradictions']])

if __name__ == '__main__':
    main()
