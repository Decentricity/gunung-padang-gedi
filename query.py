"""Query GFZ's public GEDI V2 database around Gunung Padang."""
from pathlib import Path
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
import gedidb as gdb
import geopandas as gpd
from shapely.geometry import box

OUT = Path(__file__).parent
roi = gpd.GeoDataFrame(geometry=[box(107.0472, -7.0030, 107.0654, -6.9849)], crs=4326)
provider = gdb.GEDIProvider(storage_type='s3', s3_bucket='dog-ext.gedidb.gedi-l2-l4-v002.0', url='https://s3.gfz.de')
print('Connected', flush=True)
data = provider.get_data(variables=['shot_number', 'elev_lowestmode', 'quality_flag', 'degrade_flag', 'sensitivity', 'beam_name'], query_type='bounding_box', geometry=roi, start_time='2019-01-01', end_time='2026-11-11', return_type='dataframe')
print(type(data), flush=True)
print(data, flush=True)
if data is not None:
    data.to_csv(OUT / 'footprints.csv', index=False)
