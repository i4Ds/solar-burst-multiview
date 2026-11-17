# Walk-through A2: what tfcrop sees. Approximation of CASA tfcrop's
# freqtime test (not the CASA code): per baseline/corr, fit a line in time
# per channel, robust sigma from MAD of residuals, report max |resid|/sigma.
import numpy as np, glob, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from casacore.tables import table
INK='#0b0b0b'; INK2='#52514e'; GRID='#e4e3df'; C1='#2a78d6'; C2='#eb6834'; SURF='#fcfcfb'
plt.rcParams.update({'font.size':9,'axes.edgecolor':INK2,'xtick.color':INK2,'ytick.color':INK2,'axes.titlesize':10,'axes.titleweight':'bold',
 'axes.titlelocation':'left','figure.facecolor':SURF,'axes.facecolor':SURF,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.color':GRID})
m=sorted(glob.glob('cal/*113*.ms'))[0]
ms=table(m,ack=False); d=ms.getcol('DATA'); f=ms.getcol('FLAG'); a1=ms.getcol('ANTENNA1'); a2=ms.getcol('ANTENNA2'); t=ms.getcol('TIME')
names=table(ms.getkeyword('ANTENNA'),ack=False).getcol('NAME'); fr=table(ms.getkeyword('SPECTRAL_WINDOW'),ack=False).getcol('CHAN_FREQ')[0]/1e6
ut=np.unique(t); ti=np.searchsorted(ut,t); nt=len(ut); nch=len(fr)
bl=a1*128+a2; cross=(a1!=a2)&~f.all(axis=(1,2))
ubl=np.unique(bl[cross])
order=np.lexsort((ti,bl)); 
# build cube [nbl, nt, nch, ncorr]
sel=order[cross[order]]
cube=np.abs(d[sel]).reshape(len(ubl),nt,nch,4)
x=np.arange(nt)-nt/2
A=np.vstack([np.ones(nt),x]).T; P=A@np.linalg.pinv(A)
fit=np.einsum('ij,bjcp->bicp',P,cube); res=cube-fit
mad=np.median(np.abs(res-np.median(res,axis=(1,2),keepdims=True)),axis=(1,2),keepdims=True)*1.4826
z=np.abs(res)/np.maximum(mad,1e-9)
zmax=z.max(axis=(1,2))  # [nbl, ncorr]
print('baselines',len(ubl),' max z XX/YY: median',np.median(zmax[:,0]).round(2),np.median(zmax[:,3]).round(2),' >5:',(zmax[:,[0,3]]>5).sum(),' >4:',(zmax[:,[0,3]]>4).sum(), 'overall max',zmax.max().round(2))
fig,ax=plt.subplots(1,3,figsize=(15,4.4),constrained_layout=True,gridspec_kw={'width_ratios':[1,1,1.3]})
fig.suptitle('A2 flagging: the time × frequency plane tfcrop searches, coarse channel 113 (11 × 6 per baseline)',fontsize=11,x=0.01,ha='left',color=INK)
k_med=np.argsort(zmax[:,0])[len(ubl)//2]; k_max=np.argmax(zmax[:,0])
for a,k,lab in [(ax[0],k_med,'typical baseline'),(ax[1],k_max,'baseline with the largest outlier')]:
    b=ubl[k]; im=a.imshow(cube[k,:,:,0].T,origin='lower',aspect='auto',cmap='Blues',extent=[-0.5,nt-0.5,fr[0]-0.08,fr[-1]+0.08])
    a.grid(False); a.set_xlabel('timestamp (10 s)'); a.set_ylabel('frequency (MHz)')
    a.set_title(f'{lab}: {names[b//128]}–{names[b%128]}, |V| XX')
    fig.colorbar(im,ax=a,shrink=0.85).set_label('|V|')
    a.text(0.02,0.02,f'max deviation {zmax[k,0]:.1f} σ',transform=a.transAxes,color=INK,fontsize=8,bbox=dict(fc=SURF,ec='none',alpha=0.85))
a=ax[2]; bins=np.linspace(0,max(6,zmax.max()*1.05),60)
a.hist(zmax[:,0],bins=bins,color=C1,alpha=0.8,label='XX'); a.hist(zmax[:,3],bins=bins,color=C2,alpha=0.6,label='YY')
a.axvline(5,color=INK,lw=1.5,ls='--'); a.text(5.05,0.95,'tfcrop cutoff 5σ',transform=a.get_xaxis_transform(),fontsize=8,color=INK,va='top')
a.set_xlabel('largest |residual| / robust σ per baseline'); a.set_ylabel('baselines'); a.legend(frameon=False,loc='center right')
a.set_title(f'All {len(ubl):,} baselines (approximation of tfcrop, see note)')
a.text(0.02,0.02,'line fit in time per channel, σ from MAD; not the exact CASA algorithm',transform=a.transAxes,fontsize=8,color=INK2)
fig.savefig('a2_tfcrop_view.png',dpi=150)
