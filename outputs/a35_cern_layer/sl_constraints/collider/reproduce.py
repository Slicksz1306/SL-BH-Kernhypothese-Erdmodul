"""Reviewed adapters for TWO pinned publication byte revisions only.

This is a data recipe, not a general PDF extractor. New source bytes require review.
Absent curves become explicit null slots on declared grids, never invented limits.
"""
from copy import deepcopy
from hashlib import sha256
import re
from ..common.provenance import canonical_bytes
from ..common.types import ContractError
from .extraction import check_raw, extract_html_table, extract_paragraph
from .normalize import normalize_reviewed
from .schema_document import ASSUMPTIONS

SNAPSHOT = 'cern_lhc_snapshot_2026_10_07'
PINNED = {'ATLAS': '6871595fe1a737fb5cdcc57f322626d870b24a7afc3060feb3ec4a9186c10444',
          'CMS': '7fadcfce5fce60055ccd817d98d05c9d09e4c759f1691022a0d3f4f7cf2be955'}


def _check(payload, source, experiment):
    check_raw(payload, source)
    if source['sha256'] != PINNED[experiment]:
        raise ContractError('SOURCE_CHANGED', 'reviewed adapter is pinned to original bytes')


def _ref(source, locator):
    return dict(source_id=source['source_id'], source_version=source['source_version'],
                sha256=source['sha256'], locator=locator)


def _base(source, experiment, extracted):
    atlas = experiment == 'ATLAS'
    return dict(schema_version='1.0.0', constraint_id='pending', snapshot_id=SNAPSHOT,
                source_id=source['source_id'], source_version=source['source_version'],
                experiment=experiment, collaboration=experiment, analysis_id=source['analysis_id'],
                benchmark_id='pending', channel_id='electron_jet' if atlas else 'inclusive_multibody',
                dataset_id='ATLAS_Run3_2022_2024' if atlas else 'CMS_Run2_2016_2018',
                publication_date=source['published_at'], data_period='2022-2024' if atlas else '2016-2018',
                sqrt_s={'value': '13.6' if atlas else '13', 'unit': 'TeV', 'definition': 'pp center-of-mass collision energy'},
                luminosity={'value': '164' if atlas else '138', 'unit': 'fb^-1', 'definition': 'integrated luminosity of analysis sample'},
                object_class='QUANTUM_BLACK_HOLE' if atlas else 'SEMICLASSICAL_BLACK_HOLE',
                model_family='ADD', model_version=None, n_extra_dimensions=None, model_parameters=[],
                observable_type='MASS_THRESHOLD', observable_definition='excluded lower threshold mass of the declared generator benchmark',
                limit_type='LOWER_BOUND', confidence_level='0.95', observed_value=None, expected_value=None,
                unit='TeV', expected_bands=[], statistical_method='CLs asymptotic' if atlas else 'CLs non-asymptotic; log-normal constrained nuisances',
                validity_domain=None, assumptions={k: None for k in ASSUMPTIONS['properties']},
                selection_id='EXOT-2024-32_section4_SR' if atlas else 'EXO-24-028_PS_Nge4_Sgt0.1_SVMgt0.63',
                comparison_group=None, provenance=[_ref(source, item.get('table_id', item.get('locator'))) for item in extracted],
                extraction_refs=[{'artifact_id': item['artifact_id'], 'sha256': sha256(canonical_bytes(item)).hexdigest()} for item in extracted],
                missing_fields=[], validation_status='PROPOSED', purpose='RESEARCH')


def _param(name, value, definition, role='FIXED'):
    return dict(name=name, value=value, definition=definition, role=role)


def atlas_constraints(payload, source):
    _check(payload, source, 'ATLAS')
    table = extract_html_table(payload, source, 'S6.T2')
    paragraphs = [extract_paragraph(payload, source, p) for p in ('S1.p2.1', 'S3.p2.1')]
    extractions = [table, *paragraphs]
    rows = table['rows']
    # Exact header/spacer/span layout reviewed against this pinned original table.
    if (len(rows) != 7 or rows[1] != ['n', '', '1', '2', '4', '6'] or
            rows[2][2:] != ['e+j', '\\mu+j'] * 4 or rows[3][-1] != 'Expected' or rows[5][-1] != 'Observed' or
            len(rows[4]) != 10 or len(rows[6]) != 10):
        raise ContractError('PARSE_ERROR', 'ATLAS table layout changed')
    records = []
    for model_index, (family, n) in enumerate([('RS', 1), ('ADD', 2), ('ADD', 4), ('ADD', 6)]):
        for channel_index, channel in enumerate(('electron_jet', 'muon_jet')):
            index = 2 + 2 * model_index + channel_index
            row = _base(source, 'ATLAS', extractions)
            row.update(constraint_id=f'ATLAS_{family}_n{n}_{channel}_Mth', benchmark_id=f'ATLAS_{family}_n{n}',
                       channel_id=channel, model_family=family, n_extra_dimensions=n, model_version='QBH3.02',
                       model_parameters=[_param('Mth', None, 'Threshold mass Mth=MD in TeV; QBH mass in [1,3]*Mth', 'SCAN')],
                       validity_domain='Mth scan 6-8.5 TeV step 0.5' if family == 'RS' else 'Mth scan 8-10.5 TeV step 0.5')
            row['assumptions'].update(generator='QBH v3.02 + Pythia8 shower/hadronization',
                                      pdf='CTEQ6L1; factorization scale inverse gravitational radius',
                                      threshold_convention='Mth=MD; generated MQBH in [1,3]*Mth',
                                      fundamental_scale_definition='D-dimensional gravity scale MD of the stated RS/ADD benchmark; QBH convention',
                                      spin='zero angular momentum J=0',
                                      charge='diquarks uu,ud,dd: QBH charges 4/3,1/3,-2/3',
                                      decay_regime='nonthermal two-body lepton+antiquark; baryon/lepton violation permitted; tau contribution neglected',
                                      branching_ratios='per lepton flavor: uu 11%; ud 5.6%; dd 6.7%')
            row['provenance'][0]['locator'] = f'S6.T2/observed:row6,col{index};expected:row4,col{index};zero_based'
            records.append(normalize_reviewed(row, rows[6][index], rows[4][index]))
    return extractions, records


def _quoted(fragment, value):
    if not re.search(r'(?<![0-9.])' + re.escape(value) + r'(?![0-9.])', fragment['original_html']):
        raise ContractError('PARSE_ERROR', 'reviewed scalar absent at locator')
    return value


def cms_constraints(payload, source):
    _check(payload, source, 'CMS')
    ids = ['Ch0.S3.p1.1', 'Ch0.S3.p2.1', 'Ch0.S3.p6.1', 'Ch0.S3.p7.1', 'Ch0.S3.p7.2',
           'Ch0.S3.p8.1', 'Ch0.S3.p9.2', 'Ch0.S3.p10.1', 'Ch0.S9.p2.1',
           'Ch0.S9.SS1.p2.1', 'Ch0.S9.SS2.p1.1', 'Ch0.S9.SS2.p2.1', 'Ch0.S9.SS2.p9.1', 'abstract1.1']
    ids += [f'Ch0.S3.I1.i{i}.p1.1' for i in range(1, 4)] + [f'Ch0.S3.I2.i{i}.p1.1' for i in range(1, 7)]
    fragments = {p: extract_paragraph(payload, source, p) for p in ids}
    common = [fragments[p] for p in ('Ch0.S3.p1.1', 'Ch0.S3.p2.1', 'Ch0.S3.p10.1', 'Ch0.S9.p2.1', 'Ch0.S9.SS2.p1.1')]
    records = []
    descriptions = {'B1': ('nonrotating', None, None), 'B2': ('rotating', 'no graviton emission', None),
                    'B3': ('rotating', 'energy and angular momentum loss including gravitons', None),
                    'C1': ('rotating', None, None), 'C2': ('nonrotating', None, None),
                    'C3': ('rotating', None, 'alternative evaporation refs42,43'),
                    'C4': ('rotating', 'Yoshino-Rychkov loss model', None),
                    'C5': ('rotating', None, 'stable colorless remnant'),
                    'C6': ('rotating', None, 'boiling remnant until maximum Hawking temperature MD')}
    for model, (spin, loss, remnant) in descriptions.items():
        model_fragment = fragments[f'Ch0.S3.I{1 if model[0] == "B" else 2}.i{model[1]}.p1.1']
        for n in (2, 4, 6):
            for md in range(2, 10):
                ex = [*common, model_fragment, fragments['Ch0.S3.p6.1']]
                observed = None
                if model == 'B1' and n == 2 and md in (2, 4):
                    ex.append(fragments['Ch0.S9.SS2.p2.1'])
                    observed = _quoted(ex[-1], '11.0' if md == 2 else '10.4')
                row = _base(source, 'CMS', ex)
                row.update(constraint_id=f'CMS_{model}_n{n}_MD{md}_Mmin', benchmark_id=f'CMS_{model}_n{n}_MD{md}',
                           model_version='BlackMax2.02.0' if model[0] == 'B' else 'Charybdis2_1.003',
                           n_extra_dimensions=n, validity_domain=f'MD={md} TeV; Mmin scan {md+1}-12 TeV step 1',
                           model_parameters=[_param('MD', str(md), 'fundamental Planck scale in TeV'),
                                             _param('MBH_min', None, 'minimum black-hole production mass in TeV', 'SCAN')])
                row['assumptions'].update(generator=row['model_version'] + '; LO; Pythia8.205 CP5',
                                          pdf='NNPDF3.1 NNLO', spin=spin, loss_model=loss, remnant=remnant,
                                          threshold_convention='minimum production mass MBH_min independently scanned above MD',
                                          fundamental_scale_definition='ADD fundamental Planck scale MD; generator convention not independently verified',
                                          decay_regime='semiclassical Hawking evaporation; ' + model)
                records.append(normalize_reviewed(row, observed, None))
    for ms in ('1', '1.5', '2', '2.5', '3', '3.5', '4'):
        for gs in ('0.2', '0.3', '0.4'):
            row = _base(source, 'CMS', [*common, fragments['Ch0.S3.p7.1'], fragments['Ch0.S3.p7.2']])
            key = f'CMS_SB_MS{ms}_gs{gs}'
            row.update(constraint_id=key + '_Mmin', benchmark_id=key, object_class='STRING_BALL',
                       model_family='WEAKLY_COUPLED_STRING', model_version='Charybdis2_1.003', n_extra_dimensions=6,
                       model_parameters=[_param('MS', ms, 'string scale in TeV'), _param('gs', gs, 'dimensionless string coupling'),
                                         _param('MSB_min', None, 'minimum string-ball mass in TeV', 'SCAN')],
                       validity_domain='MS 1-4 TeV step 0.5; gs 0.2/0.3/0.4; MSB_min 7-12 TeV step1; n6')
            row['assumptions'].update(generator='Charybdis2 v1.003; Pythia8.205 CP5', pdf='NNPDF3.1 NNLO',
                                      threshold_convention='minimum string-ball mass; transition to semiclassical BH above MS/gs^2',
                                      fundamental_scale_definition='MD=gs^(-2/(n-2))*MS (paper Eq1)',
                                      decay_regime='string-ball evaporation into high-multiplicity SM particles')
            records.append(normalize_reviewed(row, None, None))
    for energy in ('8.5', '8.75', '9', '9.25', '9.5'):
        for probability in ('0', '0.5', '1'):
            ex = [*common, fragments['Ch0.S3.p8.1'], fragments['Ch0.S3.p9.2'], fragments['Ch0.S9.SS2.p9.1']]
            row = _base(source, 'CMS', ex)
            key = f'CMS_sph_E{energy}_pNCS{probability}'
            row.update(constraint_id=key + '_prefactor', benchmark_id=key, object_class='SPHALERON',
                       model_family='ELECTROWEAK', model_version='BaryoGEN1.0',
                       model_parameters=[_param('E_sph', energy, 'sphaleron transition energy threshold in TeV'),
                                         _param('p_NCS_plus1', probability, 'probability of NCS=+1; remaining NCS=-1')],
                       observable_type='DIMENSIONLESS_PARAMETER', unit='1', limit_type='UPPER_BOUND',
                       observable_definition='p_sph pre-exponential factor: partonic sigma=p_sph/mW^2 * Theta(sqrt(s_hat)-E_sph); NOT an event fraction',
                       validity_domain='E_sph 8.5-9.5 TeV step0.25; p(NCS=+1)=0/0.5/1; generator p_sph=1')
            row['assumptions'].update(generator='BaryoGEN v1.0; Pythia8.205 CP5', pdf='NNPDF3.1 NNLO',
                                      threshold_convention='partonic energy threshold E_sph in Heaviside step function',
                                      fundamental_scale_definition='NOT_APPLICABLE: electroweak model; mW in Eq2',
                                      decay_regime='NCS=+/-1 baryon/lepton violating electroweak transition')
            obs, exp = (None, None)
            if energy == '9' and probability == '0.5':
                obs, exp = (_quoted(ex[-1], '0.0034'), _quoted(ex[-1], '0.0035'))
            records.append(normalize_reviewed(row, obs, exp))
    row = _base(source, 'CMS', [fragments['abstract1.1']])
    row.update(constraint_id='CMS_sph_abstract_fraction_E9', benchmark_id='CMS_sph_abstract_fraction_E9',
               object_class='SPHALERON', model_family='ELECTROWEAK', model_version='BaryoGEN1.0',
               observable_type='SPHALERON_FRACTION', observable_definition='Abstract claim: fraction of qq interactions above E_sph9TeV causing transition; relationship to Eq2 p_sph UNRESOLVED',
               limit_type='UPPER_BOUND', unit='1', model_parameters=[_param('E_sph', '9', 'transition energy in TeV')])
    records.append(normalize_reviewed(row, _quoted(fragments['abstract1.1'], '0.0034'), None))
    row = _base(source, 'CMS', [*common, fragments['Ch0.S9.SS1.p2.1']])
    row.update(constraint_id='CMS_model_independent_Nge4_sigmaA', benchmark_id='CMS_generic_Nge4',
               object_class='GENERIC_HIGH_MULTIPLICITY', model_family='MODEL_INDEPENDENT',
               observable_type='SIGMA_TIMES_ACCEPTANCE', unit='fb', limit_type='UPPER_BOUND',
               observable_definition='fiducial cross section times full event/object selection acceptance above ST_min',
               selection_id='EXO-24-028_SI_SR_Nge4_Sgt0.1',
               model_parameters=[_param('ST_min', None, 'scalar sum of object transverse momenta threshold in TeV', 'SCAN')])
    records.append(normalize_reviewed(row, None, None))
    return list(fragments.values()), records
