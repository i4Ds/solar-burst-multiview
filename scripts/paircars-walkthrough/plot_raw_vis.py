# Plot raw visibilities of an MWA MS (uv coverage, |V| and phase vs baseline,
# baseline matrix, spectra, autocorrelations). Usage: run in the directory that
# holds the MS; MS name set below. Walk-through step A0, docs/paircars-calibration-walkthrough.md.

import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from casacore.tables import table

MS='1111476056_ch113-114.ms'
ms=table(MS,ack=False)
d=ms.getcol('DATA'); a1=ms.getcol('ANTENNA1'); a2=ms.getcol('ANTENNA2'); uvw=ms.getcol('UVW'); t=ms.getcol('TIME')
names=table(ms.getkeyword('ANTENNA'),ack=False).getcol('NAME')
fr=table(ms.getkeyword('SPECTRAL_WINDOW'),ack=False).getcol('CHAN_FREQ')[0]
lam=299792458.0/fr; nant=128; nch=len(fr)
auto=a1==a2; cross=~auto
dead=np.array([np.all(d[(a1==i)|(a2==i)]==0) for i in range(nant)])
good=cross & ~dead[a1] & ~dead[a2]

INK='#0b0b0b'; INK2='#52514e'; GRID='#e4e3df'; C_XX='#2a78d6'; C_YY='#eb6834'; SURF='#fcfcfb'
plt.rcParams.update({'font.size':9,'axes.edgecolor':INK2,'axes.labelcolor':INK,'xtick.color':INK2,'ytick.color':INK2,
 'axes.titlesize':10,'axes.titleweight':'bold','axes.titlelocation':'left','figure.facecolor':SURF,'axes.facecolor':SURF,
 'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.color':GRID,'grid.linewidth':0.6})

# per-baseline, time+freq averaged (vector average over freq would decorrelate due to delays -> use mean of |V|)
lam_c=lam.mean()
uvd_l=np.hypot(uvw[:,0],uvw[:,1])/lam_c
ub=a1*nant+a2
def per_bl(x):
    s=np.bincount(ub[good],weights=x[good],minlength=nant*nant); n=np.bincount(ub[good],minlength=nant*nant)
    return s/np.maximum(n,1), n
ampXX=np.abs(d[...,0]).mean(1); ampYY=np.abs(d[...,3]).mean(1)
bXX,n=per_bl(ampXX); bYY,_=per_bl(ampYY); bU,_=per_bl(uvd_l)
sel=n>0

fig,ax=plt.subplots(2,3,figsize=(15,9.2),constrained_layout=True)
fig.suptitle('Raw visibilities: Pictor A calibrator, obs 1111476056, coarse channels 113–114 (144.0–146.6 MHz), 10 s × 160 kHz, before any calibration',
             fontsize=11,color=INK,x=0.01,ha='left')

# A uv coverage
a=ax[0,0]
u=uvw[good,0]/lam_c; v=uvw[good,1]/lam_c
a.scatter(np.r_[u,-u],np.r_[v,-v],s=0.3,c=C_XX,alpha=0.35,lw=0,rasterized=True)
a.set_aspect('equal'); a.set_xlabel('u (λ)'); a.set_ylabel('v (λ)')
a.set_title('A  uv coverage, all 11 timestamps (110 s)')
a.text(0.02,0.02,f'{good.sum()//11:,} baselines per timestamp\n(127 working tiles), mirrored ±(u,v)\nbaselines 7 m – 2.6 km = 3.4 – 1250 λ',transform=a.transAxes,fontsize=8,color=INK2,va='bottom')

# B amp vs uv distance
a=ax[0,1]
a.scatter(bU[sel],bXX[sel],s=2,c=C_XX,lw=0,alpha=0.6,label='XX',rasterized=True)
a.scatter(bU[sel],bYY[sel],s=2,c=C_YY,lw=0,alpha=0.6,label='YY',rasterized=True)
a.set_xscale('log'); a.set_yscale('log'); a.set_xlabel('baseline length (λ)'); a.set_ylabel('|V| (uncalibrated units)')
a.set_title('B  Amplitude vs baseline length')
a.legend(loc='upper right',frameon=False,markerscale=5)
a.text(0.02,0.02,'one point per baseline, mean |V| over 11 × 16 samples',transform=a.transAxes,fontsize=8,color=INK2)

# C raw phase vs uv distance (single timestamp, single channel)
a=ax[0,2]
t0=np.unique(t)[5]; ch=4
m=good&(t==t0)
a.scatter(uvd_l[m],np.degrees(np.angle(d[m,ch,0])),s=2,c=C_XX,lw=0,alpha=0.6,rasterized=True)
a.set_xscale('log'); a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180])
a.set_xlabel('baseline length (λ)'); a.set_ylabel('phase XX (deg)')
a.set_title(f'C  Phase vs baseline length (1 timestamp, {fr[ch]/1e6:.2f} MHz)')
a.text(0.02,0.02,'a point source at the phase centre would give 0° everywhere;\nhere the tile-based instrumental phases scramble it',transform=a.transAxes,fontsize=8,color=INK,bbox=dict(fc=SURF,ec='none',alpha=0.9))

# D baseline matrix
a=ax[1,0]
M=np.full((nant,nant),np.nan)
idx=np.where(sel)[0]; i=idx//nant; j=idx%nant
M[i,j]=bXX[sel]; M[j,i]=bXX[sel]
dead_i=np.where(dead)[0]
im=a.imshow(M,origin='lower',cmap='Blues',norm=LogNorm(np.nanpercentile(M,2),np.nanpercentile(M,99.5)),interpolation='nearest')
for k in dead_i:
    a.axhline(k,color=C_YY,lw=1.2); a.axvline(k,color=C_YY,lw=1.2)
a.set_xlabel('antenna index'); a.set_ylabel('antenna index'); a.grid(False)
a.set_title('D  Baseline matrix, mean |V| XX')
cb=fig.colorbar(im,ax=a,shrink=0.85); cb.set_label('|V|')
a.text(0.02,0.98,f'orange: {", ".join(names[k] for k in dead_i)}: all zeros (flagged in metafits,\nnot yet in the MS FLAG column)',transform=a.transAxes,fontsize=8,color=INK,va='top',
       bbox=dict(fc=SURF,ec='none',alpha=0.85))

# E spectrum of cross-correlations
a=ax[1,1]
fM=fr/1e6
for c,col,lab in [(0,C_XX,'XX'),(3,C_YY,'YY')]:
    med=np.median(np.abs(d[good][:,:,c]),axis=0)
    a.plot(fM,med,'-o',color=col,lw=2,ms=4,label=lab)
for k in range(2):
    lo=fM[8*k]-0.08; hi=fM[8*k+7]+0.08
    a.axvspan(lo,lo+0.16,color=GRID,zorder=0); a.axvspan(hi-0.16,hi,color=GRID,zorder=0)
    a.text((lo+hi)/2,0.97,f'coarse ch {113+k}',transform=a.get_xaxis_transform(),ha='center',va='top',fontsize=8,color=INK2)
a.axvline(fM[7]+0.08,color=INK2,lw=0.8,ls='--')
a.set_xlabel('frequency (MHz)'); a.set_ylabel('median |V| over baselines')
a.set_title('E  Spectrum, cross-correlations')
a.legend(loc='center',bbox_to_anchor=(0.27,0.38),frameon=False)
a.text(0.02,0.02,'grey bands: edge channels the split drops',transform=a.transAxes,fontsize=8,color=INK2)

# F autocorrelation per tile x channel (normalised per tile)
a=ax[1,2]
A=np.full((nant,nch),np.nan)
for k in range(nant):
    if dead[k]: continue
    r=np.abs(d[(a1==k)&(a2==k),:,0]).mean(0); A[k]=r/np.median(r)
im=a.imshow(A,aspect='auto',origin='lower',cmap='Blues',extent=[fM[0]-0.08,fM[-1]+0.08,-0.5,nant-0.5],vmin=np.nanpercentile(A,1),vmax=np.nanpercentile(A,99))
a.axvline(fM[7]+0.08,color=INK2,lw=0.8,ls='--'); a.grid(False)
a.set_xlabel('frequency (MHz)'); a.set_ylabel('antenna index')
a.set_title('F  Autocorrelations XX, each tile ÷ its median')
cb=fig.colorbar(im,ax=a,shrink=0.85); cb.set_label('relative power')
fig.savefig('raw_vis_overview.png',dpi=150)

# Figure 2: per-baseline spectra (amp + phase vs freq)
fig2,ax2=plt.subplots(2,1,figsize=(9,6.5),sharex=True,constrained_layout=True)
fig2.suptitle('Single baselines, XX, one timestamp: raw amplitude and phase across the 16 channels',fontsize=11,color=INK,x=0.01,ha='left')
L=np.hypot(uvw[:,0],uvw[:,1])
cands=[]
for target in [30,150,600,2000]:
    mm=np.where(good&(t==t0))[0]; k=mm[np.argmin(np.abs(L[mm]-target))]; cands.append(k)
cols=['#2a78d6','#eb6834','#1baf7a','#6250d6']
for k,col in zip(cands,cols):
    lab=f'{names[a1[k]]}–{names[a2[k]]}  ({L[k]:.0f} m)'
    ax2[0].plot(fM,np.abs(d[k,:,0]),'-o',color=col,lw=2,ms=4,label=lab)
    ax2[1].plot(fM,np.degrees(np.angle(d[k,:,0])),'-o',color=col,lw=2,ms=4,label=lab)
for a in ax2:
    a.axvline(fM[7]+0.08,color=INK2,lw=0.8,ls='--')
    for k in range(2):
        lo=fM[8*k]-0.08; hi=fM[8*k+7]+0.08
        a.axvspan(lo,lo+0.16,color=GRID,zorder=0); a.axvspan(hi-0.16,hi,color=GRID,zorder=0)
ax2[0].set_yscale('log'); ax2[0].set_ylabel('|V|'); ax2[0].legend(frameon=False,fontsize=8,loc='upper left',bbox_to_anchor=(1.0,1.0))
ax2[1].set_ylim(-180,180); ax2[1].set_yticks([-180,-90,0,90,180]); ax2[1].set_ylabel('phase (deg)'); ax2[1].set_xlabel('frequency (MHz)')
fig2.savefig('raw_vis_baselines.png',dpi=150)
print('dead',[names[k] for k in dead_i]); print('C channel',fr[ch]/1e6)
