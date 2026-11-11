"""Summarize retrieved footprints; distances are local approximations."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

p = Path(__file__).parent
d = pd.read_csv(p / 'footprints.csv', dtype={'shot_number': str})
d['east_m'] = (d.longitude - 107.056273) * 111320 * np.cos(np.deg2rad(-6.993939))
d['north_m'] = (d.latitude + 6.993939) * 111320
d['distance_m'] = np.hypot(d.east_m, d.north_m)
d.sort_values('distance_m').to_csv(p / 'footprints-by-distance.csv', index=False)
summary = dict(shots=len(d), nearest_m=float(d.distance_m.min()),
               radius_counts={str(r): int((d.distance_m <= r).sum()) for r in [100,250,500,1000]},
               dates=d.groupby('time').size().to_dict(),
               quality_flag_counts=d.quality_flag.value_counts().to_dict(),
               degrade_flag_counts=d.degrade_flag.value_counts().to_dict(),
               sensitivity_min=float(d.sensitivity.min()))
(p / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
fig, axs = plt.subplots(1, 2, figsize=(12, 6), layout='constrained')
for ax, limit in zip(axs, [1050,300]):
    for date, g in d.groupby('time'):
        ax.scatter(g.east_m, g.north_m, s=32, label=date)
    for r in [100,250,500,1000]:
        ax.add_patch(Circle((0,0), r, fill=False, color='grey', lw=.6, alpha=.5))
    ax.scatter([0],[0],marker='*',s=180,color='black',label='Heritage registry point',zorder=5)
    ax.set(xlim=(-limit,limit),ylim=(-limit,limit),aspect='equal',xlabel='East of registry point (m)',ylabel='North of registry point (m)')
    ax.grid(alpha=.15)
axs[0].legend(fontsize=8,loc='lower left')
axs[0].set_title('Local coverage: 117 retrieved shot centers')
axs[1].set_title('Site vicinity: 8 shot centers within 250 m')
fig.suptitle('Gunung Padang — GEDI V2 public GFZ database\nCoverage screening; registry point is not a mapped site boundary',fontsize=12)
fig.savefig(p / 'coverage.png', dpi=180)
print(json.dumps(summary, indent=2))
