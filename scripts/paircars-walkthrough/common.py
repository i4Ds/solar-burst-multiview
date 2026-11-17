import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from casacore.tables import table
INK='#0b0b0b'; INK2='#52514e'; GRID='#e4e3df'; C1='#2a78d6'; C2='#eb6834'; C3='#1baf7a'; C4='#6250d6'; SURF='#fcfcfb'
plt.rcParams.update({'font.size':9,'axes.edgecolor':INK2,'axes.labelcolor':INK,'xtick.color':INK2,'ytick.color':INK2,'axes.titlesize':10,'axes.titleweight':'bold',
 'axes.titlelocation':'left','figure.facecolor':SURF,'axes.facecolor':SURF,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.color':GRID,'grid.linewidth':0.6})
def note(a,s,loc='bl'):
    x,y,va=(0.02,0.02,'bottom') if loc=='bl' else (0.02,0.98,'top')
    a.text(x,y,s,transform=a.transAxes,fontsize=8,color=INK,va=va,bbox=dict(fc=SURF,ec='none',alpha=0.88))
def readms(path):
    ms=table(path,ack=False)
    o=dict(d=ms.getcol('DATA'),f=ms.getcol('FLAG'),a1=ms.getcol('ANTENNA1'),a2=ms.getcol('ANTENNA2'),uvw=ms.getcol('UVW'),t=ms.getcol('TIME'))
    o['fr']=table(ms.getkeyword('SPECTRAL_WINDOW'),ack=False).getcol('CHAN_FREQ')[0]
    o['names']=table(ms.getkeyword('ANTENNA'),ack=False).getcol('NAME')
    o['pd']=table(ms.getkeyword('FIELD'),ack=False).getcol('PHASE_DIR')[0,0]
    return o
def stefcal(V,M,good,nant,niter=100):
    # V,M: (nbl,) complex for one time/chan/pol; solve V_ij = g_i conj(g_j) M_ij
    pass
