"""Build paircars_calibration_walkthrough.ipynb (no outputs).

Run:  python make_notebook.py
The notebook reads ~/Projects/P-AIRCARS-data (set DATA in the first code cell).
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s.strip("\n")))
code = lambda s: C.append(nbf.v4.new_code_cell(s.strip("\n")))

md(r"""
# P-AIRCARS calibration, step by step

Companion notebook to `docs/paircars-calibration-walkthrough.md` (i4Ds/solar-burst-multiview, PR #7).
Each section explains one step of the P-AIRCARS calibration block, gives the command to run it
in the `paircars` container, and inspects what it produced.

**Data**: MWA Phase I sample, target `1111474560` (Sun, 2015-03-27 06:56 UTC, 2 s × 40 kHz → 160 kHz),
calibrator `1111476056` (Pictor A, 07:20 UTC, 10 s × 160 kHz). This notebook uses coarse channels 113–114.

**Two kinds of cells**

- *Inspect* cells read the products from disk with python-casacore and plot them. They run on the Mac.
- *Illustrate* cells (A3/A4, B1/B2) do a step in numpy on the real visibilities where the P-AIRCARS product
  does not exist yet. They are labelled **ILLUSTRATION** and are not P-AIRCARS output.

**Kernel**: the `solar-burst-multiview` conda env (has python-casacore, astropy, matplotlib, jupyterlab):

```bash
conda activate solar-burst-multiview
jupyter lab paircars_calibration_walkthrough.ipynb
```

The P-AIRCARS commands themselves run in the container (Colima profile `paircars`), where `/data` is
`~/Projects/P-AIRCARS-data`:

```bash
colima start --profile paircars
docker --context colima-paircars start paircars
docker --context colima-paircars exec -u paircars -e HOME=/home/paircars \
  -it paircars bash -lc 'source /opt/miniforge3/etc/profile.d/conda.sh && conda activate paircars && bash'
```
""")

code(r"""
# Setup
import glob, os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from casacore.tables import table
from astropy.io import fits
from astropy.time import Time
from astropy.coordinates import get_sun, SkyCoord

DATA = Path(os.environ.get("PAIRCARS_DATA", "~/Projects/P-AIRCARS-data")).expanduser()
RAW_CAL   = DATA / "cal/1111476056_ch113-114.ms"
CAL_META  = DATA / "cal/1111476056.metafits"
A1_DIR    = DATA / "stepwise/cal_after_A1"      # copy taken after A1
WORK      = DATA / "stepwise/cal"               # current state (A2 and later)
TARGET    = DATA / "target/1111474560_ch113-114.ms"
OUT29     = DATA / "out/20150327/1111474560_target"   # products of the 29 Sep full run
CH = 113                                        # coarse channel used below
for p in [RAW_CAL, CAL_META, WORK, TARGET, OUT29]:
    print(("ok      " if p.exists() else "MISSING ") + str(p))

C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.grid": True, "grid.color": "#e4e3df",
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlelocation": "left", "axes.titleweight": "bold"})

def readms(path):
    ms = table(str(path), ack=False)
    o = dict(d=ms.getcol("DATA"), f=ms.getcol("FLAG"), a1=ms.getcol("ANTENNA1"), a2=ms.getcol("ANTENNA2"),
             uvw=ms.getcol("UVW"), t=ms.getcol("TIME"), cols=ms.colnames())
    o["fr"] = table(ms.getkeyword("SPECTRAL_WINDOW"), ack=False).getcol("CHAN_FREQ")[0]
    ant = table(ms.getkeyword("ANTENNA"), ack=False)
    o["names"], o["pos"] = np.array(ant.getcol("NAME")), ant.getcol("POSITION")
    o["pd"] = table(ms.getkeyword("FIELD"), ack=False).getcol("PHASE_DIR")[0, 0]
    if "MODEL_DATA" in o["cols"]:
        o["model"] = ms.getcol("MODEL_DATA")
    return o

def ms_for(folder, ch=CH):
    m = sorted(glob.glob(str(folder / f"*_ch_{ch}_t_*.ms")))
    return Path(m[0]) if m else None

def dead_tiles(o):
    d, a1, a2 = o["d"], o["a1"], o["a2"]
    return np.array([np.all(d[(a1 == i) | (a2 == i)] == 0) for i in range(len(o["names"]))])

def phase_axis(a):
    a.set_ylim(-180, 180); a.set_yticks([-180, -90, 0, 90, 180]); a.set_ylabel("phase (deg)")

def note(a, s, top=False):
    a.text(0.02, 0.98 if top else 0.02, s, transform=a.transAxes, fontsize=8, va="top" if top else "bottom",
           bbox=dict(fc="white", ec="none", alpha=0.85))
""")

md(r"""
## Order of the calibration block

From `paircars/pipeline/flows.py`. The pipeline calls Python functions; the stand-alone CLI is given for each step.

| # | Step | Code | CLI |
|---|---|---|---|
| A1 | Split calibrator, 10 s / 160 kHz | `basic_cal_subflow`, flows.py 247 | `run-mwa-split` |
| A2 | Flag calibrator | flows.py 335 | `run-mwa-flag` |
| A3 | Import model visibilities (hyperdrive) | flows.py 422, import_model.py 51 | `run-mwa-import-model` |
| A4 | Bandpass (+ cross-hand phase) | flows.py 489, basic_cal.py | `run-mwa-basic-cal` |
| B1 | Split target, move phase centre to Sun | `selfcal_subflow`, flows.py 886 | `run-mwa-split --move_solarcenter` |
| B2 | Apply calibrator solutions | flows.py 1018 | `run-mwa-apply-basiccal` |
| B3 | Solar sidereal-motion correction | flows.py 1125 | `run-mwa-solar-siderealcor` |
| B4 | Intensity, then polarisation self-cal | flows.py 1184 | `run-mwa-selfcal` |
| C1–C4 | Split target, apply basic + self-cal, flag corrected data | `applysol_subflow`, flows.py 1482–1776 | |
| D | Dynamic spectrum, imaging, primary-beam correction | `imaging_subflow` | `run-mwa-imaging`, … |
""")

# ---------------- A0
md(r"""
## A0. The raw calibrator visibilities

The MS as delivered: averaged by ASVO to 10 s × 160 kHz (metafits `INTTIME` 0.5 s, `FINECHAN` 40 kHz),
11 timestamps × 8256 rows (128 tiles with autocorrelations), 16 channels = coarse channels 113 + 114.
Its `HISTORY` shows Birli 0.18.2 (cable, digital-gain, PFB-gain and geometric corrections, AOFlagger) and then a
full `flagdata(mode='unflag')`, so nothing is flagged.
""")
code(r"""
raw = readms(RAW_CAL)
h = fits.getheader(CAL_META)
print({k: h.get(k) for k in ["DATE-OBS", "INTTIME", "FINECHAN", "RAPHASE", "DECPHASE", "QUACKTIM"]})
print("rows", raw["d"].shape, " timestamps", len(np.unique(raw["t"])), " freqs MHz", np.round(raw["fr"] / 1e6, 3))
print("flagged fraction", raw["f"].mean(), " all-zero tiles", raw["names"][dead_tiles(raw)].tolist())
mt = fits.open(CAL_META)[1].data; tn, tf = np.asarray(mt["TileName"]).astype(str), np.asarray(mt["Flag"])
print("metafits-flagged tiles", sorted(set(tn[tf == 1].tolist())))
""")
code(r"""
d, a1, a2, uvw, fr = raw["d"], raw["a1"], raw["a2"], raw["uvw"], raw["fr"]
dead = dead_tiles(raw); good = (a1 != a2) & ~dead[a1] & ~dead[a2]
lam_c = (299792458 / fr).mean(); L = np.hypot(uvw[:, 0], uvw[:, 1]) / lam_c
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
u, v = uvw[good, 0] / lam_c, uvw[good, 1] / lam_c
ax[0].scatter(np.r_[u, -u], np.r_[v, -v], s=0.3, c=C1, alpha=0.3, lw=0, rasterized=True)
ax[0].set_aspect("equal"); ax[0].set_xlabel("u (λ)"); ax[0].set_ylabel("v (λ)"); ax[0].set_title("uv coverage, 11 × 10 s")
for c, col, lab in [(0, C1, "XX"), (3, C2, "YY")]:
    ax[1].plot(fr / 1e6, np.median(np.abs(d[good][:, :, c]), axis=0), "-o", color=col, label=lab)
ax[1].axvline((fr[7] + fr[8]) / 2e6, color="k", ls="--", lw=0.8); ax[1].legend(frameon=False)
ax[1].set_xlabel("frequency (MHz)"); ax[1].set_ylabel("median |V|"); ax[1].set_title("Spectrum: edge channels low")
t0 = np.unique(raw["t"])[5]; m = good & (raw["t"] == t0)
ax[2].scatter(L[m], np.degrees(np.angle(d[m, 4, 0])), s=2, c=C1, alpha=0.6, lw=0)
ax[2].set_xscale("log"); phase_axis(ax[2]); ax[2].set_xlabel("baseline length (λ)")
ax[2].set_title("Phase vs baseline: scrambled by tile phases"); plt.show()
""")

# ---------------- A1
md(r"""
## A1. Split the calibrator per coarse channel

CASA `mstransform` (`do_target_split.py`, `utils/casatasks.py` `single_mstransform`): one MS per coarse channel,
edge channels dropped (`get_bad_chans`, mwa_utils.py 152), averaging to 10 s / 160 kHz (a no-op here), then
`initweights(wtmode='ones')` and `flagdata(mode='clip', clipzeros=True)`.

**Quack.** The pipeline computes it from the *target* (2 s): `int(4.0 / 2) = 2` (master_flow.py 874, 926) and
`get_timeranges` then drops 3 timestamps at each end of the calibrator scan (5 of 11 kept). The walk-through first
ran with `--quack_timestamps 0`; use 2 to match the pipeline.

```bash
run-mwa-split /data/cal/1111476056_ch113-114.ms /data/cal/1111476056.metafits \
  --workdir /data/stepwise/cal --prefix calibrator \
  --timeres 10 --freqres 0.16 --quack_timestamps 2 --cpu_frac 0.5 --mem_frac 0.6
cp -r /data/stepwise/cal /data/stepwise/cal_after_A1
```
""")
code(r"""
for ch in (113, 114):
    p = ms_for(A1_DIR, ch)
    if p is None: print("no A1 output for", ch); continue
    o = readms(p)
    idx = [int(np.argmin(abs(raw["fr"] - x))) for x in o["fr"]]
    rt = np.unique(raw["t"]); ot = np.unique(o["t"]); keep = np.isin(raw["t"], ot)
    same = np.allclose(raw["d"][keep][:, idx, :], o["d"])
    print(p.name)
    print(f"  {len(o['fr'])} channels {np.round(o['fr'] / 1e6, 3)} = raw channels {idx}")
    print(f"  {len(ot)} of {len(rt)} timestamps; DATA identical to raw: {same}")
    print(f"  flagged {o['f'].mean():.4f}; flagged tiles {[str(n) for i, n in enumerate(o['names']) if o['f'][(o['a1'] == i) | (o['a2'] == i)].mean() > 0.99]}")
    print(f"  columns added: {sorted(set(o['cols']) - set(raw['cols']))}")
""")

# ---------------- A2
md(r"""
## A2. Flag the calibrator

`flagging.py` `single_ms_flag`: metafits bad tiles → `clip` (zeros) → `tfcrop` (freqtime, cutoff 5σ) →
`extend` (80 %). Edge channels and quack are not flagged here (`flag_bad_spw=False`, `flag_quack=False`).

```bash
run-mwa-flag /data/stepwise/cal/calibrator_1111476056_ch_113_t_*.ms,/data/stepwise/cal/calibrator_1111476056_ch_114_t_*.ms \
  /data/cal/1111476056.metafits --workdir /data/stepwise/cal --outdir /data/stepwise/out \
  --datacolumn data --use_tfcrop --no_flag_bad_spw --no_flag_quack --no_flagbackup --cpu_frac 0.5 --mem_frac 0.6
```
(expand the `*` yourself: the CLI takes a comma-separated list.)
""")
code(r"""
p2, p1 = ms_for(WORK), ms_for(A1_DIR)
f2 = table(str(p2), ack=False).getcol("FLAG"); f1 = table(str(p1), ack=False).getcol("FLAG")
print(f"flagged after A1 {f1.mean():.4f}, after A2 {f2.mean():.4f}, new flags {(f2 & ~f1).sum()}")
hist = table(str(p2 / "HISTORY"), ack=False).getcol("MESSAGE")
print("flagdata modes in HISTORY:", [m.split('"')[1] for m in hist if m.strip().startswith("mode ")])
""")
code(r"""
# what tfcrop looks at: the 11 x 6 time-frequency plane per baseline (approximate statistic, not the CASA algorithm)
o = readms(p2); ut = np.unique(o["t"]); ti = np.searchsorted(ut, o["t"])
sel = (o["a1"] != o["a2"]) & ~o["f"].all(axis=(1, 2))
bl = o["a1"] * 128 + o["a2"]; ubl = np.unique(bl[sel]); order = np.lexsort((ti, bl)); order = order[sel[order]]
cube = np.abs(o["d"][order]).reshape(len(ubl), len(ut), len(o["fr"]), 4)
x = np.arange(len(ut)) - len(ut) / 2; A = np.vstack([np.ones_like(x), x]).T; P = A @ np.linalg.pinv(A)
res = cube - np.einsum("ij,bjcp->bicp", P, cube)
mad = 1.4826 * np.median(np.abs(res - np.median(res, axis=(1, 2), keepdims=True)), axis=(1, 2), keepdims=True)
zmax = (np.abs(res) / np.maximum(mad, 1e-9)).max(axis=(1, 2))
fig, ax = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
k = np.argsort(zmax[:, 0])[len(ubl) // 2]
im = ax[0].imshow(cube[k, :, :, 0].T, origin="lower", aspect="auto", cmap="Blues"); ax[0].grid(False)
ax[0].set_xlabel("timestamp"); ax[0].set_ylabel("channel"); ax[0].set_title("a typical baseline, |V| XX"); fig.colorbar(im, ax=ax[0])
ax[1].hist(zmax[:, 0], bins=60, color=C1, alpha=0.8, label="XX"); ax[1].hist(zmax[:, 3], bins=60, color=C2, alpha=0.6, label="YY")
ax[1].axvline(5, color="k", ls="--"); ax[1].legend(frameon=False)
ax[1].set_xlabel("largest |residual| / robust σ per baseline"); ax[1].set_title("all baselines vs the 5σ cutoff"); plt.show()
""")

# ---------------- A3
md(r"""
## A3. Import the calibrator model (hyperdrive)

`import_model.py` 51–188: `hyperdrive vis-simulate` predicts the visibilities of the brightest 1000 GGSM
sources within the beam FWHM, weighted by the FEE beam (`mwa_full_embedded_element_pattern_160.h5`), on the
MS's time/frequency grid, into `<ms>_model.ms`. `setjy(standard='manual', fluxdensity=[1,0,0,0])` only creates the
`MODEL_DATA` column (a 1 Jy point source), which `putcol` then overwrites with the hyperdrive model.
hyperdrive returns an error if fewer than `-n` sources survive the veto (hyperdrive docs, vis_simulate); a
candidate reason for the 29 Sep failure, not verified.

```bash
cp -r /data/stepwise/cal /data/stepwise/cal_after_A2
run-mwa-import-model /data/stepwise/cal/calibrator_1111476056_ch_113_t_…ms,/data/stepwise/cal/calibrator_1111476056_ch_114_t_…ms \
  /data/cal/1111476056.metafits --workdir /data/stepwise/cal --cpu_frac 0.5 --mem_frac 0.6 --verbose 2>&1 | tee /data/stepwise/a3_import_model.log
```
""")
code(r"""
cal = readms(ms_for(WORK))
if "model" in cal:
    good = (cal["a1"] != cal["a2"]) & ~cal["f"][:, 0, 0]
    L = np.hypot(cal["uvw"][:, 0], cal["uvw"][:, 1]) / (299792458 / cal["fr"].mean())
    fig, ax = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    ax[0].scatter(L[good], np.abs(cal["model"][good, 3, 0]), s=1, c=C3, alpha=0.4, lw=0, label="MODEL_DATA")
    ax[0].scatter(L[good], np.abs(cal["d"][good, 3, 0]), s=1, c=C1, alpha=0.2, lw=0, label="DATA")
    ax[0].set_xscale("log"); ax[0].set_yscale("log"); ax[0].legend(frameon=False, markerscale=6)
    ax[0].set_xlabel("baseline length (λ)"); ax[0].set_title("A3: model vs data amplitude")
    ax[1].scatter(L[good], np.degrees(np.angle(cal["model"][good, 3, 0])), s=1, c=C3, alpha=0.4, lw=0)
    ax[1].set_xscale("log"); phase_axis(ax[1]); ax[1].set_title("A3: model phase"); plt.show()
else:
    print("A3 not run yet: no MODEL_DATA in", ms_for(WORK).name)
""")

# ---------------- A4
md(r"""
## A4. Bandpass and cross-hand phase

`basic_cal.py`: CASA `bandpass` → `<prefix>.bcal` (one complex gain per tile, polarisation and channel),
`crossphasecal` → `.kcrosscal` (full-pol only), `applycal`, post-calibration flagging; final tables in
`out/…/calibrators/caltables/`. Solves V<sub>ij,obs</sub> ≈ B<sub>i</sub>(ν) B<sub>j</sub>*(ν) V<sub>ij,model</sub>.

**ILLUSTRATION below** (not P-AIRCARS): model = unit point source at the phase centre, time-averaged, solved
per channel with a simple StEFCal-type iteration.
""")
code(r"""
def stefcal(Vm, M, W, niter=300):
    nant = Vm.shape[0]; g = np.ones(nant, complex)
    for it in range(niter):
        z = M * g.conj()[None, :]
        gn = np.sum(W * Vm * z.conj(), axis=1) / np.maximum(np.sum(W * np.abs(z) ** 2, axis=1), 1e-12)
        gn[W.sum(1) == 0] = 0
        if it % 2: gn = 0.5 * (gn + g)
        if np.max(np.abs(gn - g)) < 1e-9: return gn
        g = gn
    return g

cal = readms(ms_for(WORK)); nant = 128; nch = len(cal["fr"])
G = np.zeros((nch, 2, nant), complex)
for c in range(nch):
    for pi, p in enumerate([0, 3]):
        m = (cal["a1"] != cal["a2"]) & ~cal["f"][:, c, p]
        Vm = np.zeros((nant, nant), complex); W = np.zeros((nant, nant))
        np.add.at(Vm, (cal["a1"][m], cal["a2"][m]), cal["d"][m, c, p]); np.add.at(W, (cal["a1"][m], cal["a2"][m]), 1)
        Vm = Vm / np.maximum(W, 1); Vm = Vm + Vm.conj().T; W = ((W + W.T) > 0).astype(float)
        G[c, pi] = stefcal(Vm, np.ones((nant, nant)), W)
G = G * np.exp(-1j * np.angle(G[:, :, :1]))      # reference tile = antenna 0

c = 3; good = (cal["a1"] != cal["a2"]) & ~cal["f"][:, c, 0]
L = (np.hypot(cal["uvw"][:, 0], cal["uvw"][:, 1]) / (299792458 / cal["fr"][c]))[good]
raw_v = cal["d"][good, c, 0]; cor = raw_v / (G[c, 0][cal["a1"][good]] * np.conj(G[c, 0][cal["a2"][good]]))
fig, ax = plt.subplots(1, 3, figsize=(16, 4.4), constrained_layout=True)
ax[0].scatter(L, np.degrees(np.angle(raw_v)), s=1, c=C1, alpha=0.3, lw=0, rasterized=True); ax[0].set_title("before: DATA phase")
for k in range(nch):
    ok = np.abs(G[k, 0]) > 0; ax[1].plot(np.arange(nant)[ok], np.degrees(np.angle(G[k, 0][ok])), "o", ms=2.5, alpha=0.8,
                                         label=f"{cal['fr'][k] / 1e6:.2f} MHz")
ax[1].legend(frameon=False, fontsize=7, ncol=3); phase_axis(ax[1]); ax[1].set_xlabel("antenna index"); ax[1].set_title("solution: gain phase per tile")
ax[2].scatter(L, np.degrees(np.angle(cor)), s=1, c=C3, alpha=0.3, lw=0, rasterized=True); ax[2].set_title("after: DATA / (gᵢ gⱼ*)")
for a in (ax[0], ax[2]): a.set_xscale("log"); phase_axis(a); a.set_xlabel("baseline length (λ)")
fig.suptitle("ILLUSTRATION (point-source model, own solver), coarse ch %d, %.2f MHz, XX" % (CH, cal["fr"][c] / 1e6), x=0.01, ha="left"); plt.show()

real_b = sorted(glob.glob(str(DATA / "stepwise/out/**/calibrator*.bcal"), recursive=True))
print("P-AIRCARS A4 tables found:" if real_b else "A4 not run yet: no calibrator .bcal under stepwise/out", real_b)
""")

# ---------------- B1-B3
md(r"""
## B1–B3. Target: calibrator gains, phase centre to the Sun, sidereal motion

B1 splits the target and moves the phase centre to the Sun with `chgcenter` (WSClean container), using the
Sun's position from astropy `get_sun` (`sunpos_utils.py` 98). B2 applies the A4 tables. B3 re-centres every
timestamp on the moving Sun. In the 29 Sep run the move **failed on all 6 MSs** (log: "done successfully",
then "Total failure: 6").

**ILLUSTRATION below** (not P-AIRCARS): Pictor A gains from the A4 cell applied to the raw solar data, then a
numpy phase rotation to the Sun (sign chosen to centre the short baselines; uvw not re-projected).
""")
code(r"""
tg = readms(TARGET)
c = int(np.argmin(abs(tg["fr"] - cal["fr"][3]))); lam = 299792458 / tg["fr"][c]
deadt = dead_tiles(tg); ut = np.unique(tg["t"]); tm = ut[len(ut) // 2]
sel = (tg["a1"] != tg["a2"]) & ~deadt[tg["a1"]] & ~deadt[tg["a2"]] & (tg["t"] == tm)
u, v, w = (tg["uvw"][sel] / lam).T; L = np.hypot(u, v); V = tg["d"][sel, c, 0]
s = get_sun(Time(tm / 86400, format="mjd", scale="utc")); ra0, dec0 = tg["pd"]; ra, dec = s.ra.rad, s.dec.rad
l = np.cos(dec) * np.sin(ra - ra0); m = np.sin(dec) * np.cos(dec0) - np.cos(dec) * np.sin(dec0) * np.cos(ra - ra0); n = np.sqrt(1 - l * l - m * m)
print(f"target: {len(ut)} timestamps × {np.diff(ut)[0]:.0f} s; Sun is {np.degrees(np.arccos(n)) * 60:.1f}′ from the phase centre")
s0, s1 = [get_sun(Time(x / 86400, format="mjd")) for x in (ut[0], ut[-1])]
dr = SkyCoord(s0.ra, s0.dec).separation(SkyCoord(s1.ra, s1.dec)).arcsec
print(f"B3: Sun moves {dr:.1f}″ in {ut[-1] - ut[0]:.0f} s ({dr / (ut[-1] - ut[0]) * 60:.1f}′ per hour)")
Vc = V / (G[3, 0][tg["a1"][sel]] * np.conj(G[3, 0][tg["a2"][sel]]))
cands = [Vc * np.exp(sg * 2j * np.pi * (u * l + v * m + w * (n - 1))) for sg in (+1, -1)]
Vr = min(cands, key=lambda x: np.abs(np.angle(x[L < 60])).mean())
fig, ax = plt.subplots(1, 4, figsize=(18, 4), constrained_layout=True)
ax[0].scatter(L, np.abs(V), s=2, c=C2, alpha=0.5, lw=0); ax[0].set_yscale("log"); ax[0].set_title("raw |V|: the solar disc")
ax[1].scatter(L, np.degrees(np.angle(V)), s=2, c=C2, alpha=0.5, lw=0); phase_axis(ax[1]); ax[1].set_title("raw phase")
ax[2].scatter(L, np.degrees(np.angle(Vc)), s=2, c=C1, alpha=0.5, lw=0); phase_axis(ax[2]); ax[2].set_title("B2: calibrator gains applied")
ax[3].scatter(L, np.degrees(np.angle(Vr)), s=2, c=C3, alpha=0.5, lw=0); phase_axis(ax[3]); ax[3].set_title("B1: phase centre on the Sun")
for a in ax: a.set_xscale("log"); a.set_xlabel("baseline length (λ)")
fig.suptitle("ILLUSTRATION on the target, %.2f MHz, XX, one 2 s timestamp" % (tg["fr"][c] / 1e6), x=0.01, ha="left"); plt.show()
""")

# ---------------- B4 / C3
md(r"""
## B4 → C3. Self-calibration solutions and applying them (29 Sep products)

`selfcal_utils.py`: CASA `gaincal` / `bandpass` with WSClean imaging between rounds (intensity), QuartiCal for
polarisation. Final tables per coarse channel in `out/…/caltables/selfcal_<obsid>_ch_<N>.{gcal,bcal}` (`.dcal`
for leakage when polarisation self-cal succeeds; it failed on 29 Sep). C3 applies them with CASA `applycal`;
here they are applied in numpy to the raw target data.
""")
code(r"""
Gt = table(str(OUT29 / f"caltables/selfcal_1111474560_ch_{CH}.gcal"), ack=False)
Bt = table(str(OUT29 / f"caltables/selfcal_1111474560_ch_{CH}.bcal"), ack=False)
Gs, Gf = Gt.getcol("CPARAM")[:, 0, :], Gt.getcol("FLAG")[:, 0, :]; Bs = Bt.getcol("CPARAM")
bfr = table(Bt.getkeyword("SPECTRAL_WINDOW"), ack=False).getcol("CHAN_FREQ")[0] / 1e6
names = tg["names"]; flagged = np.where(Gf.any(1))[0]
r = np.linalg.norm(tg["pos"] - tg["pos"].mean(0), axis=1)
print("G flagged tiles:", [(str(names[i]), int(r[i])) for i in flagged], "(name, metres from array centre)")
k = 3; c = int(np.argmin(abs(tg["fr"] / 1e6 - bfr[k])))
sel2 = sel & ~Gf[tg["a1"], 0] & ~Gf[tg["a2"], 0]
J = Gs[:, 0] * Bs[:, k, 0]; Vt = tg["d"][sel2, c, 0]
Vtc = Vt / (J[tg["a1"][sel2]] * np.conj(J[tg["a2"][sel2]])); L2 = np.hypot(*(tg["uvw"][sel2, :2] / (299792458 / tg["fr"][c])).T)
fig, ax = plt.subplots(1, 4, figsize=(18, 4), constrained_layout=True)
ok = ~Gf[:, 0] & ~deadt
ax[0].plot(np.arange(128)[ok], np.abs(Gs[ok, 0]), "o", ms=3, color=C1); ax[0].set_title(".gcal |g| per tile"); ax[0].set_xlabel("antenna index")
ax[1].plot(np.arange(128)[ok], np.degrees(np.angle(Gs[ok, 0])), "o", ms=3, color=C1); phase_axis(ax[1]); ax[1].set_title(".gcal phase per tile")
Bn = np.abs(Bs[:, :, 0]) / np.abs(Bs[:, :, 0]).mean(1, keepdims=True)
for i in np.where(~deadt)[0][::4]: ax[2].plot(bfr, Bn[i], color=C1, alpha=0.35)
ax[2].plot(bfr, np.median(Bn[~deadt], 0), "k-o"); ax[2].set_title(".bcal shape |B| / tile mean"); ax[2].set_xlabel("MHz")
ax[3].scatter(L2, np.degrees(np.angle(Vtc)), s=2, c=C3, alpha=0.5, lw=0); ax[3].set_xscale("log"); phase_axis(ax[3])
ax[3].set_title("C3: raw DATA / (Jᵢ Jⱼ*), J = G·B"); ax[3].set_xlabel("baseline length (λ)"); plt.show()
""")

# ---------------- C4
md(r"""
## C4. Flags on the corrected target data (29 Sep products)

`flagdata` on the corrected column with `flag_quack=True` (flows.py 1788: 4 s at start and end). The flag versions
are kept in `out/…/ms_flags/<ms>.flagversions`. Rows follow the split target MS: 24 timestamps × 8256 baselines
(the split already dropped 3 of the 30 timestamps at each end).
""")
code(r"""
fv = sorted(glob.glob(str(OUT29 / f"ms_flags/target_1111474560_ch_{CH}_t_*.flagversions")))[0]
F = table(fv + "/flags.finalflag_1", ack=False).getcol("FLAG"); nt = F.shape[0] // 8256; F = F.reshape(nt, 8256, *F.shape[1:])
ms0 = table(str(TARGET), ack=False); b1, b2 = ms0.getcol("ANTENNA1", 0, 8256), ms0.getcol("ANTENNA2", 0, 8256)
Lm = np.hypot(*ms0.getcol("UVW", 0, 8256)[:, :2].T)
print(f"flagged overall {F.mean():.3f}; by timestamp {np.round(F.mean(axis=(1, 2, 3)), 2)}")
tilefrac = np.array([F[3:-3][:, (b1 == i) | (b2 == i)].mean() for i in range(128)])
print("fully flagged tiles:", names[tilefrac > 0.99].tolist(), " same as G-flagged:", set(names[tilefrac > 0.99]) == set(names[flagged]))
fig, ax = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
ax[0].bar(range(nt), 100 * F.mean(axis=(1, 2, 3)), color=C1); ax[0].set_xlabel("timestamp (2 s)"); ax[0].set_ylabel("flagged (%)")
bins = [0, 50, 100, 200, 350, 500, 750, 1000, 1500, 3000]; fb = F[3:-3].mean(axis=(0, 2, 3)); cr = b1 != b2
ax[1].bar(range(len(bins) - 1), [100 * fb[cr & (Lm >= lo) & (Lm < hi)].mean() for lo, hi in zip(bins[:-1], bins[1:])], color=C1)
ax[1].set_xticks(range(len(bins) - 1)); ax[1].set_xticklabels([f"{lo}–{hi}" for lo, hi in zip(bins[:-1], bins[1:])], rotation=40)
ax[1].set_xlabel("baseline length (m)"); ax[1].set_ylabel("flagged (%)"); plt.show()
""")

# ---------------- D
md(r"""
## D. Images (29 Sep products)

WSClean images (`imagedir_f_1.28_t_10.0_pol_IQUV_w_briggs_0.0/images/`), one per coarse channel and 10 s,
Stokes IQUV. In the 29 Sep run the phase-centre move failed and the primary-beam / phase-shift step found no
images, so `pbcor_*` is empty and the WCS still has the old phase centre (`CRVAL1` 4.966°).
The dashed circle is the optical disc (radius 16′).
""")
code(r"""
fs = sorted(glob.glob(str(OUT29 / "imagedir_f_1.28_t_10.0_pol_IQUV_w_briggs_0.0/images/time_20150327065607.0_*.fits")))
fig, ax = plt.subplots(1, len(fs) + 1, figsize=(3.2 * (len(fs) + 1), 3.4), constrained_layout=True)
tt = np.linspace(0, 2 * np.pi, 200)
for a, f in zip(ax, fs):
    hd = fits.getheader(f); im = fits.getdata(f)[0, 0]; pix = abs(hd["CDELT1"]) * 60; c0 = im.shape[0] // 2; h = 60
    a.imshow(im[c0 - h:c0 + h, c0 - h:c0 + h], origin="lower", cmap="inferno", extent=np.array([-h, h, -h, h]) * pix)
    a.plot(16 * np.cos(tt), 16 * np.sin(tt), "w--", lw=0.8); a.grid(False); a.set_title(f"I {hd['CRVAL3'] / 1e6:.2f} MHz")
hd = fits.getheader(fs[3]); vim = fits.getdata(fs[3])[3, 0]; c0 = vim.shape[0] // 2; h = 60; vmax = np.nanmax(np.abs(vim))
ax[-1].imshow(vim[c0 - h:c0 + h, c0 - h:c0 + h], origin="lower", cmap="RdBu_r", vmin=-vmax, vmax=vmax,
              extent=np.array([-h, h, -h, h]) * abs(hd["CDELT1"]) * 60)
ax[-1].plot(16 * np.cos(tt), 16 * np.sin(tt), "k--", lw=0.8); ax[-1].grid(False); ax[-1].set_title(f"V {hd['CRVAL3'] / 1e6:.2f} MHz")
print("CRVAL1/2 of the first image:", hd["CRVAL1"], hd["CRVAL2"], " beam (arcmin):", round(hd["BMAJ"] * 60, 1), round(hd["BMIN"] * 60, 1)); plt.show()
""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3 (solar-burst-multiview)", "language": "python"}
nbf.write(nb, "paircars_calibration_walkthrough.ipynb")
print("written", len(C), "cells")
