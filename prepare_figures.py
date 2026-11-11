"""Rebuild cropped source figures; requires Poppler and Pillow.

The paper is CC BY 4.0. Crops omit surrounding prose; no plotted content is
retouched. Attribution and the retraction status accompany all figures in UI.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image

ROOT=Path(__file__).parent
poppler=shutil.which('/usr/bin/pdftoppm') or shutil.which('pdftoppm')
config=[(22,1800,'reconstruction-fig14.webp',(155,115,1215,840)),
        (16,1800,'radar-fig9.webp',(135,140,1240,1090)),
        (18,1800,'resistivity-fig10.webp',(220,110,1190,1240)),
        (20,1800,'seismic-fig12.webp',(180,115,1210,840)),
        (2,2000,'site-map-fig1.webp',(230,460,1190,1555))]
with tempfile.TemporaryDirectory() as temp:
    for page,scale,name,crop in config:
        prefix=str(Path(temp)/str(page))
        subprocess.run([poppler,'-f',str(page),'-l',str(page),'-scale-to',str(scale),'-png','-singlefile',str(ROOT/'sources/paper-2023-retracted.pdf'),prefix],check=True)
        Image.open(prefix+'.png').crop(crop).save(ROOT/'web/figures'/name,quality=91)
        print(name)
