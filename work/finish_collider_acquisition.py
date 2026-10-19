"""Follow only the additional CMS HEPData alias actually linked by the source."""
from acquire_collider_sources import store
from sl_constraints.collider.sources import acquire_public

if __name__ == '__main__':
    for name, url in [('cms_hepdata_inspire', 'https://www.hepdata.net/record/ins3144373?format=json'),
                      ('cms_hepdata_doi', 'https://doi.org/10.17182/hepdata.165871')]:
        raw, receipt = acquire_public(url)
        receipt['requested_source_id'] = name
        store.artifact('receipts', name, receipt)
        if raw:
            store._publish('raw/' + receipt['sha256'], raw)
        print(name, receipt, flush=True)
