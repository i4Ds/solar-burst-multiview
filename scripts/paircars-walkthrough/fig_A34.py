import sys; sys.path.insert(0,'.')
from common import *
o=readms('/home/claude/vis/a2/cal/calibrator_1111476056_ch_113_t_20150327072047_20150327072227.ms')
d,f,a1,a2,uvw,fr,names=o['d'],o['f'],o['a1'],o['a2'],o['uvw'],o['fr'],o['names']
G=np.load('picA_gains_ch113.npy')   # (chan, pol[XX,YY], ant)
ref=0
G=G*np.exp(-1j*np.angle(G[:,:,ref:ref+1]))
good=(a1!=a2)&~f[:,0,0]
lam=299792458/fr; c=3
L=(np.hypot(uvw[:,0],uvw[:,1])/lam[c])[good]
raw=d[good,c,0]
gi=G[c,0][a1[good]]; gj=G[c,0][a2[good]]
cor=raw/(gi*np.conj(gj))
fig,ax=plt.subplots(2,2,figsize=(13,8.6),constrained_layout=True)
fig.suptitle(f'A3 + A4 illustrated: what a gain/bandpass solve does to the Pictor A data (coarse ch 113, {fr[c]/1e6:.2f} MHz, XX, all 11 timestamps)',fontsize=11,x=0.01,ha='left',color=INK)
a=ax[0,0]; a.scatter(L,np.degrees(np.angle(raw)),s=1,c=C1,lw=0,alpha=0.35,rasterized=True)
a.set_xscale('log'); a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180]); a.set_xlabel('baseline length (λ)'); a.set_ylabel('phase (deg)')
a.set_title('Before: DATA phase vs baseline'); note(a,'instrumental phases φᵢ − φⱼ scramble everything')
a=ax[0,1]
for k,col in zip(range(6),[C1,C2,C3,C4,'#a2539c','#888780']):
    ph=np.degrees(np.angle(G[k,0])); ok=np.abs(G[k,0])>0
    a.plot(np.arange(128)[ok],ph[ok],'o',ms=3,color=col,label=f'{fr[k]/1e6:.2f} MHz',alpha=0.8)
a.set_xlabel('antenna index'); a.set_ylabel('gain phase (deg, rel. to Tile011)'); a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180])
a.set_title('The solution: one complex gain per tile, channel, pol'); a.legend(frameon=False,fontsize=7,ncol=3,loc='upper right')
note(a,'the 6 channels lie on top of each other:\nthe tile phases hardly change across 960 kHz')
a=ax[1,0]; a.scatter(L,np.degrees(np.angle(cor)),s=1,c=C3,lw=0,alpha=0.35,rasterized=True)
a.set_xscale('log'); a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180]); a.set_xlabel('baseline length (λ)'); a.set_ylabel('phase (deg)')
a.set_title('After: DATA / (gᵢ gⱼ*)'); note(a,'phases collapse towards 0: Pictor A dominates and sits at the phase centre.\nWider spread beyond ~200 λ: the source is partly resolved and SNR is lower')
a=ax[1,1]
amp=np.abs(cor); a.scatter(L,amp,s=1,c=C3,lw=0,alpha=0.35,rasterized=True)
a.set_xscale('log'); a.set_yscale('log'); a.set_xlabel('baseline length (λ)'); a.set_ylabel('|V| / model')
a.axhline(1,color=INK,lw=1,ls='--'); a.set_title('After: corrected amplitude relative to the model')
note(a,'model here = 1 on every baseline (point source).\nCorrected |V| sits near 1; the scatter grows on\nlong baselines where a point model is too simple')
fig.text(0.01,-0.03,'ILLUSTRATION, not P-AIRCARS output: model = unit point source at the phase centre (like setjy manual 1 Jy), solved with a simple StEFCal-type '
         'least-squares iteration, time-averaged. P-AIRCARS uses the hyperdrive GGSM model (A3) and CASA bandpass (A4).',fontsize=8,color=INK2)
fig.savefig('fig/A34_solve_illustration.png',dpi=140,bbox_inches='tight')
