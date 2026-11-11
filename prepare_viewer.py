"""Build the browser data from native Copernicus pixels and saved GEDI shots.

Usage: python prepare_viewer.py /path/to/S07.tif /path/to/S08.tif
No interpolation is used to create new elevation posts. The GeoTIFF preserves
the source grid. Browser coordinates are local metres about the registry point.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys
import numpy as np
import rasterio
from rasterio.merge import merge

ROOT = Path(__file__).parent
OUT = ROOT / 'web' / 'data'
OUT.mkdir(parents=True, exist_ok=True)
LAT, LON = -6.993939, 107.056273
BOUNDS = (107.0472, -7.0030, 107.0654, -6.9849)
MX, MY = 111320 * np.cos(np.deg2rad(LAT)), 111320
paths = [Path(a) for a in sys.argv[1:]]
if len(paths) != 2:
    raise SystemExit(__doc__)
sources = [rasterio.open(p) for p in paths]
# Snap outward to source cell edges, including the cross-tile southern edge.
win = rasterio.windows.from_bounds(*BOUNDS, transform=sources[0].transform)
c0, r0 = np.floor([win.col_off, win.row_off]).astype(int)
c1, r1 = np.ceil([win.col_off+win.width, win.row_off+win.height]).astype(int)
aligned_bounds = rasterio.windows.bounds(rasterio.windows.Window(c0,r0,c1-c0,r1-r0), sources[0].transform)
arr, tr = merge(sources, bounds=aligned_bounds)
heights = arr[0]
assert np.isfinite(heights).all() and heights.min() > 0
rows, cols = heights.shape
xs = tr.c + (np.arange(cols) + .5) * tr.a
ys = tr.f + (np.arange(rows) + .5) * tr.e
metadata = dict(driver='GTiff', width=cols, height=rows, count=1,
                dtype='float32', crs='EPSG:4326', transform=tr, compress='deflate')
with rasterio.open(OUT / 'copernicus-surface-crop.tif', 'w', **metadata) as dst:
    dst.write(arr)
    dst.update_tags(source='Copernicus GLO-30 AWS 2021 release', vertical_datum='EGM2008', AREA_OR_POINT='Point')
terrain = dict(origin=dict(latitude=LAT, longitude=LON), columns=cols, rows=rows,
               east_m=np.round((xs-LON)*MX, 3).tolist(),
               north_m=np.round((ys-LAT)*MY, 3).tolist(),
               elevations_m=np.round(heights, 2).tolist(), vertical_datum='EGM2008',
               nominal_resolution_m=30, resampling='none; native source posts',
               minimum_m=round(float(heights.min()),2), maximum_m=round(float(heights.max()),2))
(OUT / 'terrain.json').write_text(json.dumps(terrain, separators=(',', ':'))+'\n')
shots = []
with (ROOT / 'footprints.csv').open() as f:
    for row in csv.DictReader(f):
        shots.append(dict(shot=row['shot_number'], date=row['time'], beam=row['beam_name'],
                          latitude=float(row['latitude']), longitude=float(row['longitude']),
                          east_m=round((float(row['longitude'])-LON)*MX,3),
                          north_m=round((float(row['latitude'])-LAT)*MY,3),
                          elev_lowestmode_ellipsoid_m=float(row['elev_lowestmode']),
                          quality_flag=int(row['quality_flag']), degrade_flag=int(row['degrade_flag']),
                          sensitivity=float(row['sensitivity'])))
(OUT / 'shots.json').write_text(json.dumps(shots,separators=(',', ':'))+'\n')
manifest = dict(accessed='2026-11-11', bounds_wsen=BOUNDS, terrain_grid=dict(rows=rows,columns=cols),
                copernicus_source_files=[dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
                source_urls=[f'https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_S{s}_00_E107_00_DEM/Copernicus_DSM_COG_10_S{s}_00_E107_00_DEM.tif' for s in ['07','08']],
                gedi_source='GFZ public dog-ext.gedidb.gedi-l2-l4-v002.0', gedi_shots=len(shots),
                gedi_csv_sha256=hashlib.sha256((ROOT/'footprints.csv').read_bytes()).hexdigest(),
                vertical_alignment='GEDI footprint rings are draped on DSM for location only. GEDI ellipsoidal heights are NOT transformed to EGM2008 or used as terrain vertices.',
                model='Conceptual geometry based on Figure 14 and Table 1; no georeferenced subsurface volume is available in this repository.')
(OUT / 'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
for s in sources:
    s.close()
print(f'{rows} x {cols} native elevation posts; {len(shots)} shots; surface {heights.min():.1f}–{heights.max():.1f} m EGM2008')
