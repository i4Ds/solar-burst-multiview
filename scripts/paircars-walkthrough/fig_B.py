import sys; sys.path.insert(0,'.')
from common import *
from astropy.time import Time; from astropy.coordinates import get_sun
import astropy.units as u
o=readms('target/1111474560_ch113-114.ms')
d,f,a1,a2,uvw,fr,t,pd=o['d'],o['f'],o['a1'],o['a2'],o['uvw'],o['fr'],o['t'],o['pd']
# use coarse ch 113 = raw channels 1..6 (as the split would), take channel index 4 (=raw ch4, 144.715 MHz)
c=4; lam=299792458/fr[c]
dead=np.array([np.all(d[(a1==i)|(a2==i)]==0) for i in range(128)])
good=(a1!=a2)&~dead[a1]&~dead[a2]
tm=np.unique(t)[len(np.unique(t))//2]
sel=good&(t==tm)
u_,v_,w_=(uvw[sel]/lam).T; L=np.hypot(u_,v_)
V=d[sel,c,0]
# Sun position (P-AIRCARS method: astropy get_sun, GCRS RA/Dec used as J2000)
s=get_sun(Time(tm/86400,format='mjd',scale='utc'))
ra0,dec0=pd; ra,dec=s.ra.rad,s.dec.rad
l=np.cos(dec)*np.sin(ra-ra0); m=np.sin(dec)*np.cos(dec0)-np.cos(dec)*np.sin(dec0)*np.cos(ra-ra0); n=np.sqrt(1-l*l-m*m)
sep=np.degrees(np.arccos(n))*60
# PicA gains (illustration) for the same frequency: PicA ch113 split channel index 3 == 144.715 MHz
G=np.load('picA_gains_ch113.npy')[3,0]
Vc=V/(G[a1[sel]]*np.conj(G[a2[sel]]))
best=None
for sgn in (+1,-1):
    Vr=Vc*np.exp(sgn*2j*np.pi*(u_*l+v_*m+w_*(n-1)))
    sc=np.abs(np.angle(Vr[L<60])).mean()
    if best is None or sc<best[0]: best=(sc,sgn,Vr)
sc,sgn,Vr=best
fig,ax=plt.subplots(2,2,figsize=(13,8.6),constrained_layout=True)
fig.suptitle(f'B1–B2 illustrated on the Sun (target 1111474560, {fr[c]/1e6:.2f} MHz, XX, one 2 s timestamp)',fontsize=11,x=0.01,ha='left',color=INK)
a=ax[0,0]; a.scatter(L,np.abs(V),s=2,c=C2,lw=0,alpha=0.5,rasterized=True); a.set_xscale('log'); a.set_yscale('log')
a.set_xlabel('baseline length (λ)'); a.set_ylabel('|V| raw'); a.set_title('Raw solar visibilities: amplitude')
note(a,'the Sun is a ~0.5° disc: visibility amplitude drops steeply\nbeyond ~100 λ (compare Pictor A, which stays flat to ~200 λ)')
a=ax[0,1]; a.scatter(L,np.degrees(np.angle(V)),s=2,c=C2,lw=0,alpha=0.5,rasterized=True); a.set_xscale('log')
a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180]); a.set_xlabel('baseline length (λ)'); a.set_ylabel('phase (deg)')
a.set_title('Raw solar visibilities: phase'); note(a,'instrumental phases: no structure')
a=ax[1,0]; a.scatter(L,np.degrees(np.angle(Vc)),s=2,c=C1,lw=0,alpha=0.5,rasterized=True); a.set_xscale('log')
a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180]); a.set_xlabel('baseline length (λ)'); a.set_ylabel('phase (deg)')
a.set_title('B2: after applying calibrator gains (Pictor A, illustration)')
note(a,f'phases now coherent but wind with baseline: the Sun sits\n{sep:.1f}′ from the phase centre, giving a phase ramp 2π(ul + vm)')
a=ax[1,1]; a.scatter(L,np.degrees(np.angle(Vr)),s=2,c=C3,lw=0,alpha=0.5,rasterized=True); a.set_xscale('log')
a.set_ylim(-180,180); a.set_yticks([-180,-90,0,90,180]); a.set_xlabel('baseline length (λ)'); a.set_ylabel('phase (deg)')
a.set_title('B1: after moving the phase centre to the Sun')
note(a,'short baselines now near 0°: the disc is centred.\nLong baselines resolve the disc and its structure')
fig.text(0.01,-0.075,f'ILLUSTRATION, not P-AIRCARS output. Gains: own point-source solve on Pictor A (figure A3+A4), coarse ch 113. Sun position: astropy get_sun as in P-AIRCARS sunpos_utils.py;\n'
 f'phase rotation exp(±2πi(ul+vm+w(n−1))) applied in numpy with the sign that centres the short baselines ({"+" if sgn>0 else "−"}); uvw not re-projected.\n'
 f'B3 (sidereal motion): the Sun moves 2.4″ against the sky in the 58 s of data (2.5′ per hour), i.e. up to 5° of phase on the longest baseline (2.6 km); '
 f'over a longer observation this grows, which is why P-AIRCARS re-centres every timestamp.',fontsize=8,color=INK2,va='bottom')
fig.savefig('fig/B12_sun_illustration.png',dpi=140,bbox_inches='tight')
print('sep arcmin',sep,'sign',sgn,'scatter',np.degrees(sc))
