import sys; sys.path.insert(0,'.')
from common import *
cd='out/20150327/1111474560_target/caltables/'
Gt=table(cd+'selfcal_1111474560_ch_113.gcal',ack=False); Bt=table(cd+'selfcal_1111474560_ch_113.bcal',ack=False)
G=Gt.getcol('CPARAM')[:,0,:]; Gf=Gt.getcol('FLAG')[:,0,:]; B=Bt.getcol('CPARAM'); Bf=Bt.getcol('FLAG')
ga=Gt.getcol('ANTENNA1'); ba=Bt.getcol('ANTENNA1')
assert (ga==np.arange(128)).all() and (ba==np.arange(128)).all()
spw=table(Bt.getkeyword('SPECTRAL_WINDOW'),ack=False).getcol('CHAN_FREQ')[0]/1e6
print('G flagged',Gf.sum(),'B flagged',Bf.sum(),'B freqs',spw, 'refant row phases', np.degrees(np.angle(G[:3])))
o=readms('target/1111474560_ch113-114.ms'); d,f,a1,a2,uvw,fr,t,names=o['d'],o['f'],o['a1'],o['a2'],o['uvw'],o['fr'],o['t'],o['names']
idx=[int(np.argmin(abs(fr/1e6-x))) for x in spw]; print('raw chan idx',idx)
dead=np.array([np.all(d[(a1==i)|(a2==i)]==0) for i in range(128)])
tm=np.unique(t)[len(np.unique(t))//2]
sel=(a1!=a2)&~dead[a1]&~dead[a2]&(t==tm)&~Gf[a1,0]&~Gf[a2,0]
k=3; c=idx[k]; lam=299792458/fr[c]
L=np.hypot(uvw[sel,0],uvw[sel,1])/lam
V=d[sel,c,0]; J=G[:,0]*B[:,k,0]
Vc=V/(J[a1[sel]]*np.conj(J[a2[sel]]))
fig=plt.figure(figsize=(13,9.2),constrained_layout=True); gs=fig.add_gridspec(2,3)
fig.suptitle('B4 → C3 with real P-AIRCARS products: self-cal solutions of the 29 Sep run (coarse ch 113, XX)',fontsize=11,x=0.01,ha='left',color=INK)
ok=~Gf[:,0]&~dead
a=fig.add_subplot(gs[0,0]); a.plot(np.arange(128)[ok],np.abs(G[ok,0]),'o',ms=3,color=C1,label='XX'); a.plot(np.arange(128)[~Gf[:,1]&~dead],np.abs(G[~Gf[:,1]&~dead,1]),'o',ms=3,color=C2,label='YY',alpha=0.7)
a.set_xlabel('antenna index'); a.set_ylabel('|g|'); a.set_title('.gcal: gain amplitude per tile'); a.legend(frameon=False)
a=fig.add_subplot(gs[0,1]); a.plot(np.arange(128)[ok],np.degrees(np.angle(G[ok,0])),'o',ms=3,color=C1); a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180])
a.set_xlabel('antenna index'); a.set_ylabel('gain phase (deg)'); a.set_title('.gcal: gain phase per tile')
note(a,'one solution per tile and pol for the\nwhole self-cal interval (CASA G Jones)')
a=fig.add_subplot(gs[0,2])
Bn=np.abs(B[:,:,0])/np.abs(B[:,:,0]).mean(1,keepdims=True)
for i in np.where(~dead)[0][::4]:
    a.plot(spw,Bn[i],'-',color=C1,alpha=0.35,lw=1)
a.plot(spw,np.median(Bn[~dead],axis=0),'-o',color=INK,lw=2,ms=4)
a.set_xlabel('frequency (MHz)'); a.set_ylabel('|B| / tile mean'); a.set_title('.bcal: bandpass shape (amplitude), every 4th tile')
note(a,f'black: median over tiles. Absolute |B| median {np.median(np.abs(B[~dead,:,0])):.2f};\nthe flux scale sits in B. From quiet-Sun self-cal\n(no calibrator bandpass was available)','tl')
a=fig.add_subplot(gs[1,0])
for i in np.where(~dead)[0][::4]:
    a.plot(spw,np.degrees(np.angle(B[i,:,0])),'-',color=C1,alpha=0.35,lw=1)
a.set_ylim(-60,60); a.set_xlabel('frequency (MHz)'); a.set_ylabel('bandpass phase (deg)'); a.set_title('.bcal: bandpass phase')
a=fig.add_subplot(gs[1,1]); a.scatter(L,np.degrees(np.angle(V)),s=2,c=C2,lw=0,alpha=0.5,rasterized=True); a.set_xscale('log')
a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180]); a.set_xlabel('baseline length (λ)'); a.set_ylabel('phase (deg)'); a.set_title(f'Raw solar DATA, {fr[c]/1e6:.2f} MHz')
a=fig.add_subplot(gs[1,2]); a.scatter(L,np.degrees(np.angle(Vc)),s=2,c=C3,lw=0,alpha=0.5,rasterized=True); a.set_xscale('log')
a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180]); a.set_xlabel('baseline length (λ)'); a.set_ylabel('phase (deg)'); a.set_title('C3: DATA / (Jᵢ Jⱼ*), J = G·B')
note(a,'short baselines at 0° without any phase-centre move,\nconsistent with self-cal having put the Sun at the old\nphase centre (the move failed in this run)')
fig.text(0.01,-0.03,'Tables read with python-casacore from out/20150327/1111474560_target/caltables/selfcal_1111474560_ch_113.{gcal,bcal}; applied here in numpy to the raw target MS (one 2 s timestamp). '
 'In the pipeline C3 is CASA applycal on the split, rephased target MS.',fontsize=8,color=INK2)
fig.savefig('fig/C_selfcal_tables_apply.png',dpi=140,bbox_inches='tight')
