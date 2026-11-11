"""Convert GEDI ellipsoidal heights to EGM2008 using an archived NGA grid window."""
from pathlib import Path
import json
import hashlib
import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
root=Path(__file__).parent/'web/data'
url='https://cdn.proj.org/us_nga_egm08_25.tif'
shots=json.loads((root/'shots.json').read_text())
crop=root/'egm2008-local.tif'
if not crop.exists():
    with rasterio.open(url) as src:
        win=from_bounds(107.04,-7.01,107.08,-6.98,transform=src.transform)
        c,r=int(np.floor(win.col_off))-1,int(np.floor(win.row_off))-1
        win=Window(c,r,int(np.ceil(win.width))+4,int(np.ceil(win.height))+4)
        a=src.read(1,window=win)
        profile=src.profile.copy()
        profile.update(width=a.shape[1],height=a.shape[0],transform=src.window_transform(win),tiled=False,blockxsize=a.shape[1],blockysize=a.shape[0],compress='deflate')
        with rasterio.open(crop,'w',**profile) as dst:
            dst.write(a,1)
            dst.update_tags(source=url,quantity='geoid_undulation',units='metre')
with rasterio.open(crop) as src:
    a=src.read(1)
    for s in shots:
        col,row=(~src.transform)*(s['longitude'],s['latitude']);col-=.5;row-=.5
        c,r=int(np.floor(col)),int(np.floor(row));tx,ty=col-c,row-r
        n=(1-ty)*((1-tx)*a[r,c]+tx*a[r,c+1])+ty*((1-tx)*a[r+1,c]+tx*a[r+1,c+1])
        s['geoid_undulation_m']=round(float(n),6)
        s['ground_egm2008_m']=round(s['elev_lowestmode_ellipsoid_m']-float(n),6)
(root/'shots.json').write_text(json.dumps(shots,separators=(',',':'))+'\n')
p=json.loads((root/'provenance.json').read_text())
p['vertical_alignment']='GEDI lowest-mode ellipsoidal height minus bilinear NGA EGM2008 geoid undulation. Terrain and GEDI ground heights use EGM2008 metres.'
p['geoid_source']=dict(url=url,local_crop_sha256=hashlib.sha256(crop.read_bytes()).hexdigest(),interpolation='bilinear at each shot center',formula='H = h - N')
p['model']='Four paper-derived units in the shared landscape, anchored at the heritage registry point below the DSM. Envelope shapes, horizontal extent, and registration are visualization choices, not surveyed interfaces.'
p['model_registration']=dict(origin_latitude=-6.993939,origin_longitude=107.056273,rotation_degrees=16,footprint_metres=[200,260],height_metres=56,surface_offset_metres=2,unit_depth_offsets_metres=[0,2,6,23],chamber_dimensions_metres=[10,10,15],chamber_center_local_metres=[0,38,0],source='Natawidjaja et al. Figure 14, Table 1, Section 3.6.2; placement and envelopes chosen for visualization')
(root/'provenance.json').write_text(json.dumps(p,indent=2)+'\n')
print('Converted',len(shots),'GEDI heights; geoid range',min(s['geoid_undulation_m'] for s in shots),max(s['geoid_undulation_m'] for s in shots))
