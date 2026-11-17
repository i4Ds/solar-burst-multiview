import sys,glob; sys.path.insert(0,'.')
from common import *
from astropy.io import fits
p='out/20150327/1111474560_target/ms_flags/target_1111474560_ch_113_t_20150327065607_20150327065653.ms.flagversions/'
F=table(p+'flags.finalflag_1',ack=False).getcol('FLAG').reshape(24,8256,6,4)
ms=table('target/1111474560_ch113-114.ms',ack=False)
a1=ms.getcol('ANTENNA1',0,8256); a2=ms.getcol('ANTENNA2',0,8256); uvw=ms.getcol('UVW',0,8256)
ant=table(ms.getkeyword('ANTENNA'),ack=False); pos=ant.getcol('POSITION'); names=ant.getcol('NAME')
gf=table('out/20150327/1111474560_target/caltables/selfcal_1111474560_ch_113.gcal',ack=False).getcol('FLAG')[:,0,:].any(1)
# local E/N from ITRF: rotate about centre
c=pos.mean(0); lon=np.arctan2(c[1],c[0]); lat=np.arctan2(c[2],np.hypot(c[0],c[1]))
dx=pos-c; E=-np.sin(lon)*dx[:,0]+np.cos(lon)*dx[:,1]; N=-np.sin(lat)*np.cos(lon)*dx[:,0]-np.sin(lat)*np.sin(lon)*dx[:,1]+np.cos(lat)*dx[:,2]
fig,ax=plt.subplots(1,3,figsize=(15,4.8),constrained_layout=True)
fig.suptitle('C4 with real P-AIRCARS products: final flags on the target (coarse ch 113, 24 × 2 s, 29 Sep run)',fontsize=11,x=0.01,ha='left',color=INK)
a=ax[0]; ft=F.mean(axis=(1,2,3)); a.bar(np.arange(24),ft*100,color=[C2 if x>0.99 else C1 for x in ft],width=0.8)
a.set_xlabel('timestamp (2 s)'); a.set_ylabel('flagged (%)'); a.set_ylim(0,105); a.set_title('By timestamp')
note(a,'first and last 3 timestamps fully flagged: flagdata quack, 4 s at\nstart and end (flows.py 1788). This is on top of the split,\nwhich already dropped 3 timestamps at each end (30 → 24)','tl')
a=ax[1]; L=np.hypot(uvw[:,0],uvw[:,1]); fb=F[3:21].mean(axis=(0,2,3)); cross=a1!=a2
bins=np.array([0,50,100,200,350,500,750,1000,1500,3000]); mid=[]; val=[]
for lo,hi in zip(bins[:-1],bins[1:]):
    m=cross&(L>=lo)&(L<hi); mid.append(f'{lo}–{hi}'); val.append(fb[m].mean()*100)
a.bar(range(len(val)),val,color=C1,width=0.8); a.set_xticks(range(len(val))); a.set_xticklabels(mid,rotation=40,ha='right',fontsize=7.5)
a.set_xlabel('baseline length (m)'); a.set_ylabel('flagged (%), middle 18 timestamps'); a.set_title('By baseline length')
note(a,'flags grow with baseline length:\nthe flagged tiles are the outer ones','tl')
a=ax[2]; a.scatter(E[~gf],N[~gf],s=12,c=C1,lw=0,label='used'); a.scatter(E[gf],N[gf],s=36,c=C2,marker='x',label='flagged (14 tiles)')
for i in np.where(gf)[0]: a.annotate(names[i].replace('Tile',''),(E[i],N[i]),fontsize=6.5,color=INK2,xytext=(3,3),textcoords='offset points')
a.set_aspect('equal'); a.set_xlabel('east (m)'); a.set_ylabel('north (m)'); a.set_title('Which tiles: array layout'); a.legend(frameon=False,loc='lower left',fontsize=8)
note(a,'same 14 tiles as the flagged solutions in the\nself-cal .gcal: no gain solution → data flagged','tl')
fig.savefig('fig/C4_flags.png',dpi=140,bbox_inches='tight')

fs=sorted(glob.glob('out/20150327/1111474560_target/imagedir*/images/time_20150327065607.0_*.fits'))
fig,ax=plt.subplots(2,4,figsize=(15,8),constrained_layout=True)
fig.suptitle('D2 with real P-AIRCARS products: WSClean images, 06:56:07 UTC, 1.28 MHz × 10 s (29 Sep run)',fontsize=11,x=0.01,ha='left',color=INK)
def show(a,im,hd,title,cmap,sym=False):
    pix=abs(hd['CDELT1'])*60; n=im.shape[0]; half=60; c0=n//2
    sub=im[c0-half:c0+half,c0-half:c0+half]; ext=np.array([-half,half,-half,half])*pix
    v=np.nanmax(np.abs(sub)) if sym else None
    h=a.imshow(sub,origin='lower',cmap=cmap,extent=ext,vmin=-v if sym else None,vmax=v if sym else None)
    a.grid(False); a.set_title(title); a.set_xlabel('arcmin'); a.set_ylabel('arcmin')
    t=np.linspace(0,2*np.pi,200); a.plot(16*np.cos(t),16*np.sin(t),color='#ffffff' if not sym else INK,lw=0.8,ls='--')
    return h
for k,f in enumerate(fs[:6]):
    h=fits.open(f); hd=h[0].header; im=h[0].data[0,0]
    hh=show(ax.flat[k],im,hd,f"Stokes I, {hd['CRVAL3']/1e6:.2f} MHz",'inferno'); fig.colorbar(hh,ax=ax.flat[k],shrink=0.8).set_label('Jy/beam (uncal. scale)',fontsize=7)
f=fs[3]; h=fits.open(f); hd=h[0].header
hh=show(ax.flat[6],h[0].data[3,0],hd,f"Stokes V, {hd['CRVAL3']/1e6:.2f} MHz",'RdBu_r',sym=True); fig.colorbar(hh,ax=ax.flat[6],shrink=0.8)
a=ax.flat[7]; a.axis('off')
a.text(0,0.95,'How to read these',fontsize=10,fontweight='bold',color=INK,va='top',transform=a.transAxes)
a.text(0,0.82,'• Dashed circle: optical disc, radius 16′.\n• Beam ≈ 7.5′ × 4′ (BMAJ/BMIN in the headers).\n'
 '• No A4 solutions existed, so the flux scale\n  comes from self-cal assumptions (paper §4).\n• Stokes V: polarisation self-cal failed in this\n'
 '  run, so V is uncorrected for leakage.\n• Images are labelled with the original phase\n  centre (CRVAL1 4.966°): the move to the Sun\n'
 '  failed and pbcor found no images, so the\n  pbcor_* folders are empty.',fontsize=8.5,color=INK,va='top',transform=a.transAxes,linespacing=1.5)
fig.savefig('fig/D2_images.png',dpi=140,bbox_inches='tight')
print([fits.getheader(x)['CRVAL3']/1e6 for x in fs])
