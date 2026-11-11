"""Validate provenance, datum separation, and native terrain against sources.

python tests/data_integrity.py /path/to/S07.tif /path/to/S08.tif
Source TIFF arguments are optional; when supplied every displayed native post
is compared to the original rather than only checking internal consistency.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import rasterio

root=Path(__file__).resolve().parents[1]
data=root/'web/data'
t=json.loads((data/'terrain.json').read_text())
s=json.loads((data/'shots.json').read_text())
provenance=json.loads((data/'provenance.json').read_text())
with (root/'footprints.csv').open() as f:
    rows=list(csv.DictReader(f))
assert len(s)==len(rows)==117
assert {r['shot'] for r in s}=={r['shot_number'] for r in rows}
assert all(isinstance(r['shot'],str) for r in s)
assert provenance['gedi_csv_sha256']==hashlib.sha256((root/'footprints.csv').read_bytes()).hexdigest()
assert len({r['date'] for r in s})==4
assert all(r['quality_flag']==1 and r['degrade_flag']==0 for r in s)
assert t['vertical_datum']=='EGM2008'
with rasterio.open(data/'copernicus-surface-crop.tif') as crop:
    a=crop.read(1)
    assert a.shape==(t['rows'],t['columns'])==(66,66)
    assert np.isfinite(a).all() and 700<a.min()<a.max()<1300
    np.testing.assert_allclose(a,np.array(t['elevations_m']),atol=.006)
    coords=[rasterio.transform.xy(crop.transform,r,c) for r in range(crop.height) for c in range(crop.width)]
    if len(sys.argv)>1:
        original=np.full(a.size,np.nan)
        for filename,record in zip(sys.argv[1:],provenance['copernicus_source_files']):
            p=Path(filename)
            assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256']
            with rasterio.open(p) as src:
                mask=np.array([src.bounds.left<=x<src.bounds.right and src.bounds.bottom<y<=src.bounds.top for x,y in coords])
                original[mask]=np.array([v[0] for v in src.sample([coords[i] for i in np.flatnonzero(mask)])])
        np.testing.assert_array_equal(a.ravel(),original)
assert hashlib.sha256((root/'sources/paper-2023-retracted.pdf').read_bytes()).hexdigest()=='d6fcfd71deb9f3706180d026c863a6038154a5e9f8b8249c7c92398461d77751'
print('PASS: 4,356 native posts match source pixels; 117 exact shot IDs retained; vertical datums separated; provenance hashes verified.' if len(sys.argv)>1 else 'PASS: crop, shots, datum declarations, and archived-paper integrity.')
