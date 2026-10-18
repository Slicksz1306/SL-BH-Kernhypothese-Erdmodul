"""Required scalar slots, independent of acquired or successfully parsed rows.

Reviewed scope: ATLAS Table 2 and CMS section 3 declared grids / section 9.
This is not a claim that all slots have published limits. Curves and additional
observables remain separate explicit gaps in the snapshot coverage document.
"""


def declared_scope():
    rows = []

    def add(analysis, benchmark, channel, observable='MASS_THRESHOLD'):
        rows.append(dict(analysis_id=analysis, benchmark_id=benchmark,
                         channel_id=channel, observable_type=observable))

    for family, dimension in [('RS', 1), ('ADD', 2), ('ADD', 4), ('ADD', 6)]:
        for channel in ('electron_jet', 'muon_jet'):
            add('EXOT-2024-32', f'ATLAS_{family}_n{dimension}', channel)
    channel = 'inclusive_multibody'
    for model in ('B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6'):
        for dimension in (2, 4, 6):
            for scale in range(2, 10):
                add('EXO-24-028', f'CMS_{model}_n{dimension}_MD{scale}', channel)
    for scale in ('1', '1.5', '2', '2.5', '3', '3.5', '4'):
        for coupling in ('0.2', '0.3', '0.4'):
            add('EXO-24-028', f'CMS_SB_MS{scale}_gs{coupling}', channel)
    for energy in ('8.5', '8.75', '9', '9.25', '9.5'):
        for probability in ('0', '0.5', '1'):
            add('EXO-24-028', f'CMS_sph_E{energy}_pNCS{probability}', channel, 'DIMENSIONLESS_PARAMETER')
    add('EXO-24-028', 'CMS_sph_abstract_fraction_E9', channel, 'SPHALERON_FRACTION')
    add('EXO-24-028', 'CMS_generic_Nge4', channel, 'SIGMA_TIMES_ACCEPTANCE')
    return rows
