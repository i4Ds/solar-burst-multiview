#!/usr/bin/env python3
"""Export the image products for the image board page (~/mwa/board/).

Reads the product registry (~/mwa/products/*.json), the event table (events.json), the
P-AIRCARS images, the MWA light curves (dynspec npz) and the metafits, and writes
  board.json        events (meta, channel list, Stonyhurst grid, context figure) and products
                    (parameters, state, attempts, frames with peak / rms / centroid, light curve)
  data/<prod>.txt   all frames of a product, Stokes I cropped to +-1500 arcsec, int16 scaled
                    per frame (value = int16 * frame scale), row-major, y up, little-endian,
                    base64 (artifact pages do not serve raw binary files)
  movies/<prod>.mp4 series with more than MAX_FRAMES frames (burst_movie_mwa.py: full Sun and
                    zoom on the source, Stonyhurst grid, peak curve), <prod>_peak.png poster
  img/              context figures; <prod>_full.png: brightest frame at full resolution
                    (event_figure.py); <prod>_euv.png: MWA contours on AIA 193 A with NOAA
                    regions and PFSS lines (euv_context.py, brightest frame)
  events: GOES flares during the observation (HEK, cached in events.json);
  products: calibration method, calibrator source (metafits CALIBSRC) and obsid
The page draws the images itself, so scale, colour map and comparisons are chosen there.
Run with ~/mwa/tools-venv/bin/python; copy ~/mwa/board to the Mac and publish the page.
"""
import base64
import glob
import json
import os
import re
import shutil
import subprocess
import time

import numpy as np
from astropy.io import fits

H = os.path.expanduser("~")
PR, EV, OUT = f"{H}/mwa/products", f"{H}/mwa/events", f"{H}/mwa/board"
SCR = f"/scratch/{os.environ.get('USER', 'andre_csillaghy')}"
HALF = 1500.0   # arcsec
EVENTS = {}     # events.json, for markers in the full figures
MAX_FRAMES = 10  # more frames: a movie (burst_movie_mwa.py) instead of frames drawn by the page


def legacy_state(p):
    """State of a product made with event_image.sh, from ~/mwa/events/<SUN>.md."""
    md = p.get("legacy_md", "")
    txt = open(md).read() if os.path.exists(md) else ""
    last = [l for l in txt.splitlines() if l.startswith("- ")]
    lastl = last[-1] if last else ""
    state = ("done" if re.search(r"DONE|logged to MLflow|MLflow logging", lastl) or "DONE:" in txt and "FAILED" not in lastl
             else "failed" if "FAILED" in lastl else "waiting" if not last else "running")
    m = re.search(r"window (\S+)", txt)
    p.update(state=state, trange=m.group(1) if m else p.get("trange", ""), log_tail=last[-3:])
    # event_image.sh rewrote its status file at every attempt: only the last attempt is known
    start = re.findall(r"started (\d{4}-\d\d-\d\d \d\d:\d\d)", txt)
    ends = [l for l in last if re.search(r"DONE|FAILED", l)]
    if start:
        a = {"start": start[-1]}
        if ends:
            a.update(end=ends[-1][2:18], result="done" if "DONE" in ends[-1] else "failed")
        p["attempts"] = [a]
    return p


def image_dir(p):
    if p.get("imgdir"):
        return p["imgdir"]
    g = glob.glob(f"{SCR}/paircars/out/{p['tag']}/{p['datedir']}/{p['sun']}_target/imagedir_*_{p['label']}/pbcor_hpcs")
    return g[0] if g else ""


def frame(fn):
    h = fits.getheader(fn)
    d = np.squeeze(fits.getdata(fn)).astype(float)
    while d.ndim > 2:
        d = d[0]
    s = 3600.0 if h.get("CUNIT1", "deg").strip().lower().startswith("deg") else 1.0
    x = ((np.arange(d.shape[1]) - (h["CRPIX1"] - 1)) * h["CDELT1"] + h["CRVAL1"]) * s
    y = ((np.arange(d.shape[0]) - (h["CRPIX2"] - 1)) * h["CDELT2"] + h["CRVAL2"]) * s
    X, Y = np.meshgrid(x, y)
    off = d[(np.hypot(X, Y) > 2500) & np.isfinite(d)]
    rms = 1.4826 * np.nanmedian(np.abs(off - np.nanmedian(off)))
    pk = np.nanmax(d)
    m = d > 0.5 * pk
    cx, cy = (d[m] * X[m]).sum() / d[m].sum(), (d[m] * Y[m]).sum() / d[m].sum()
    ix, iy = np.flatnonzero(np.abs(x) <= HALF), np.flatnonzero(np.abs(y) <= HALF)
    crop = np.nan_to_num(d[np.ix_(iy, ix)])
    if h["CDELT2"] < 0:
        crop = crop[::-1]
    if h["CDELT1"] < 0:
        crop = crop[:, ::-1]
    nu = next((h[f"CRVAL{k}"] for k in range(1, 5) if str(h.get(f"CTYPE{k}", "")).startswith("FREQ")), np.nan)
    bmaj, bmin = h["BMAJ"] * 3600, h["BMIN"] * 3600
    tb = pk * 1e-26 * (2.998e8 / nu) ** 2 / (2 * 1.380649e-23 * np.pi / (4 * np.log(2)) * bmaj * bmin / 206265 ** 2)
    meta = dict(t=h.get("DATE-OBS", ""), freq_mhz=round(nu / 1e6, 3), peak=float(pk), rms=float(rms),
                snr=float(pk / rms), x=round(float(cx)), y=round(float(cy)), r_rsun=round(float(np.hypot(cx, cy) / 960), 3),
                bmaj=round(bmaj), bmin=round(bmin), bpa=round(float(h.get("BPA", 0)), 1), tb_rj=float(tb))
    extent = [float(min(x[ix])), float(max(x[ix])), float(min(y[iy])), float(max(y[iy]))]
    return meta, crop, extent


def grid_lines(t_obs):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from sunpy.coordinates import frames, get_earth
    earth = get_earth(t_obs)
    hpc = frames.Helioprojective(observer=earth, obstime=t_obs)
    lines = []
    for kind, values in (("lon", np.arange(-90, 91, 15)), ("lat", np.arange(-75, 76, 15))):
        for v in values:
            t = np.linspace(-90, 90, 61)
            lon, lat = (np.full_like(t, v), t) if kind == "lon" else (t, np.full_like(t, v))
            c = SkyCoord(lon * u.deg, lat * u.deg, frame=frames.HeliographicStonyhurst, obstime=t_obs).transform_to(hpc)
            front = np.asarray(c.distance < earth.radius)
            pts = [[round(float(a)), round(float(b))] if f else None
                   for a, b, f in zip(c.Tx.arcsec, c.Ty.arcsec, front)]
            lines.append({"kind": kind, "v": int(v), "pts": pts})
    limb = 959.6 * u.AU.to(u.m) / earth.radius.to(u.m).value
    return {"limb": round(float(limb), 1), "lines": lines}


def channels(sun):
    f = f"{SCR}/mwa/events/{sun}/{sun}.metafits"
    if not os.path.exists(f):
        return []
    v = str(fits.getheader(f).get("CHANNELS", ""))   # long string over CONTINUE cards
    return [int(c) for c in v.split(",") if c.strip().isdigit()]


def lightcurve(sun, ch):
    f = f"{SCR}/mwa/events/{sun}/dynspec_ch{ch}.npz"
    if not os.path.exists(f):
        return None
    d = np.load(f)
    with np.errstate(all="ignore"):
        lc = np.nanmedian(d["amp"] / np.nanmedian(d["amp"], axis=1, keepdims=True), axis=0)
    t = d["unix"]
    return {"t0": float(t[0]), "dt": float(np.median(np.diff(t))),
            "y": [None if not np.isfinite(v) else round(float(v), 2) for v in lc]}


def movie(p, frames, crops, extent, fns):
    """MP4 + peak-frame PNG of a series with more than MAX_FRAMES frames (burst_movie_mwa.py).
    Remade only when the frames changed (count or newest FITS)."""
    os.makedirs(f"{OUT}/movies", exist_ok=True)
    base = f"{OUT}/movies/{p['product']}"
    stamp = f"{len(fns)} {max(os.path.getmtime(f) for f in fns):.0f} perframe-freq"
    if os.path.exists(f"{base}.mp4") and os.path.exists(f"{base}.stamp") and open(f"{base}.stamp").read() == stamp:
        return {"mp4": f"movies/{p['product']}.mp4", "poster": f"movies/{p['product']}_peak.png"}
    n = min(min(c.shape) for c in crops)
    cube = np.stack([c[:n, :n] for c in crops])[:, None]            # (time, freq, y, x)
    times = np.array([re.sub(r"[-T:]", "", fr["t"])[:16] for fr in frames])
    ip = int(np.argmax([fr["peak"] for fr in frames]))
    np.savez_compressed(f"{base}_cube.npz", data=cube, times=times, freqs=np.array([frames[0]["freq_mhz"]]),
                        frame_freqs=np.array([fr["freq_mhz"] for fr in frames]),   # composites change channel
                        extent=np.array(extent))
    fps = float(min(10, max(2, len(frames) / 20)))
    r = subprocess.run([f"{H}/mwa/tools-venv/bin/python", f"{H}/mwa/events/burst_movie_mwa.py", f"{base}_cube.npz",
                        "--out", base, "--no-gif", "--fps", str(fps),
                        "--zoom", str(frames[ip]["x"]), str(frames[ip]["y"]), "600"], capture_output=True, text=True)
    os.remove(f"{base}_cube.npz")
    if r.returncode or not os.path.exists(f"{base}.mp4"):
        print(f"movie for {p['product']} failed: {r.stderr[-500:]}")
        return None
    open(f"{base}.stamp", "w").write(stamp)
    return {"mp4": f"movies/{p['product']}.mp4", "poster": f"movies/{p['product']}_peak.png"}


def grid_movie(p, frames, crops, exts, fns):
    """MP4 + peak PNG with one panel per channel (burst_movie_grid.py), for composites with
    layout "grid" (e.g. every channel of 1449551392). Remade only when the frames changed."""
    os.makedirs(f"{OUT}/movies", exist_ok=True)
    base = f"{OUT}/movies/{p['product']}"
    stamp = f"{len(fns)} {max(os.path.getmtime(f) for f in fns):.0f} grid"
    if os.path.exists(f"{base}.mp4") and os.path.exists(f"{base}.stamp") and open(f"{base}.stamp").read() == stamp:
        return {"mp4": f"movies/{p['product']}.mp4", "poster": f"movies/{p['product']}_peak.png"}
    times = sorted({fr["t"][:21] for fr in frames})
    ti = {t: i for i, t in enumerate(times)}
    freqs = sorted({round(fr["freq_mhz"], 1) for fr in frames})
    arrays = {}
    for k, f in enumerate(freqs):
        idx = [i for i, fr in enumerate(frames) if round(fr["freq_mhz"], 1) == f]
        n = min(min(crops[i].shape) for i in idx)
        cube = np.full((len(times), n, n), np.nan, dtype="f4")
        for i in idx:
            cube[ti[frames[i]["t"][:21]]] = crops[i][:n, :n]
        c = round(f / 1.28)
        arrays[f"data_{c}"] = cube
        arrays[f"extent_{c}"] = np.array(exts[idx[0]])
    chans = np.array([round(f / 1.28) for f in freqs])
    np.savez_compressed(f"{base}_cube.npz", times=np.array(times), freqs=np.array(freqs), chans=chans, **arrays)
    r = subprocess.run([f"{H}/mwa/tools-venv/bin/python", f"{H}/mwa/events/burst_movie_grid.py", f"{base}_cube.npz",
                        "--out", base], capture_output=True, text=True)
    os.remove(f"{base}_cube.npz")
    if r.returncode or not os.path.exists(f"{base}.mp4"):
        print(f"grid movie for {p['product']} failed: {r.stderr[-500:]}")
        return None
    open(f"{base}.stamp", "w").write(stamp)
    return {"mp4": f"movies/{p['product']}.mp4", "poster": f"movies/{p['product']}_peak.png"}


def obs_window(sun):
    """Start and end of the MWA observation (metafits DATE-OBS + EXPOSURE), ISO strings."""
    mf = f"{SCR}/mwa/events/{sun}/{sun}.metafits"
    if not os.path.exists(mf):
        return "", ""
    from astropy.time import Time
    h = fits.getheader(mf)
    t0 = Time(h["DATE-OBS"])
    return t0.isot[:19], (t0 + float(h.get("EXPOSURE", 0)) / 86400).isot[:19]


def goes_flares(t0, t1):
    """GOES flares (HEK, SWPC) overlapping the observation +-10 min: class, start/peak/end, NOAA region."""
    from astropy.time import Time
    from sunpy.net import Fido
    from sunpy.net import attrs as a
    import astropy.units as u
    res = Fido.search(a.Time(Time(t0) - 10 * u.min, Time(t1) + 10 * u.min), a.hek.EventType("FL"),
                      a.hek.OBS.Observatory == "GOES")
    out = []
    for r in res["hek"] if len(res) else []:
        out.append(dict(cls=str(r["fl_goescls"]), start=str(r["event_starttime"])[:19],
                        peak=str(r["event_peaktime"])[:19], end=str(r["event_endtime"])[:19],
                        ar=int(r["ar_noaanum"] or 0)))
    order = "ABCMX"
    return sorted(out, key=lambda f: (order.find(f["cls"][:1]), float(f["cls"][1:] or 0)), reverse=True)


def calibration(p):
    """Calibration of a product: method, calibrator source (metafits CALIBSRC) and obsid, self-cal."""
    src = ""
    for mf in glob.glob(f"{SCR}/paircars/data/{p['cal']}_*/{p['cal']}.metafits"):
        src = str(fits.getheader(mf).get("CALIBSRC", "")).strip()
        if src:
            break
    return dict(method=p.get("method", "P-AIRCARS"), source=src, obsid=p.get("cal", ""),
                selfcal=p.get("selfcal", True))


def full_png(p, fn):
    """Full-resolution figure of one frame (event_figure.py: grid, contours, beam, 160 dpi), cached."""
    out = f"{OUT}/img/{p['product']}_full.png"
    stamp = f"{fn} {os.path.getmtime(fn):.0f}"
    sf = f"{out}.stamp"
    if os.path.exists(out) and os.path.exists(sf) and open(sf).read() == stamp:
        return f"img/{p['product']}_full.png"
    h = fits.getheader(fn)
    title = f"MWA {p['sun']}, ch {p['ch']}, Stokes I, {p.get('tres', '')} s from {h.get('DATE-OBS', '')[11:21]} UTC; {p['label']}"
    marks = sum([["--mark", f"{x},{y},{lab}"] for x, y, lab in EVENTS.get(p["sun"], {}).get("marks", [])], [])
    r = subprocess.run([f"{H}/mwa/tools-venv/bin/python", f"{H}/mwa/events/event_figure.py", fn, out,
                        "--title", title, "--dpi", "160"] + marks, capture_output=True, text=True)
    if r.returncode or not os.path.exists(out):
        print(f"full figure for {p['product']} failed: {r.stderr[-300:]}")
        return None
    open(sf, "w").write(stamp)
    return f"img/{p['product']}_full.png"


def euv(p, fn):
    """MWA contours over AIA 193 A with NOAA regions and PFSS lines (euv_context.py), cached."""
    out = f"{OUT}/img/{p['product']}_euv.png"
    stamp = f"{fn} {os.path.getmtime(fn):.0f}"
    sf = f"{OUT}/img/{p['product']}_euv.stamp"
    if os.path.exists(out) and os.path.exists(sf) and open(sf).read() == stamp:
        return f"img/{p['product']}_euv.png"
    r = subprocess.run([f"{H}/mwa/tools-venv/bin/python", f"{H}/mwa/events/euv_context.py", fn, "--out", out,
                        "--cache", f"{H}/mwa/board_cache/{p['sun']}"], capture_output=True, text=True)
    if r.returncode or not os.path.exists(out):
        print(f"EUV figure for {p['product']} failed: {r.stderr[-400:]}")
        return None
    open(sf, "w").write(stamp)
    return f"img/{p['product']}_euv.png"


def main():
    os.makedirs(f"{OUT}/data", exist_ok=True)
    os.makedirs(f"{OUT}/img", exist_ok=True)
    events = json.load(open(f"{PR}/events.json")) if os.path.exists(f"{PR}/events.json") else {}
    EVENTS.update(events)
    prods = []
    for f in sorted(glob.glob(f"{PR}/*.json")):
        if os.path.basename(f) == "events.json":
            continue
        p = json.load(open(f))
        if p.get("legacy"):
            legacy_state(p)
        elif os.path.exists(f"{PR}/{p['product']}.md"):
            p["log_tail"] = [l for l in open(f"{PR}/{p['product']}.md").read().splitlines() if l.startswith("- ")][-3:]
        if p.get("parts"):   # composite (e.g. images along a burst drift over several channels)
            # a part is a product id, or {"product", "from", "to"} (ISO UTC) to take only that time span
            specs = [q if isinstance(q, dict) else {"product": q} for q in p["parts"]]
            parts, fns = [], []
            for s in specs:
                if not os.path.exists(f"{PR}/{s['product']}.json"):
                    continue
                q = json.load(open(f"{PR}/{s['product']}.json"))
                parts.append(q)
                for fn in glob.glob(f"{image_dir(q)}/*.fits") if image_dir(q) else []:
                    t_img = fits.getheader(fn).get("DATE-OBS", "")
                    if s.get("from", "") <= t_img < s.get("to", "9999"):
                        fns.append(fn)
            fns.sort(key=lambda fn: fits.getheader(fn).get("DATE-OBS", ""))
            states = [q.get("state", "waiting") for q in parts]
            p["state"] = ("done" if parts and all(s == "done" for s in states) else
                          "failed" if "failed" in states else "running" if fns else "waiting")
            p["attempts"] = [a for q in parts for a in q.get("attempts", [])[-1:]]
        else:
            d = image_dir(p)
            fns = sorted(glob.glob(f"{d}/*.fits")) if d else []
        frames, crops, extent, exts = [], [], None, []
        for fn in fns:
            meta, crop, extent = frame(fn)
            frames.append(meta)
            crops.append(crop)
            exts.append(extent)
        p["frames"] = frames
        if p.get("layout") == "grid" and crops:   # all channels side by side, one panel each
            p["movie"] = grid_movie(p, frames, crops, exts, fns)
        elif len(crops) > MAX_FRAMES:   # series: a movie instead of frames drawn by the page
            p["movie"] = movie(p, frames, crops, extent, fns)
            if p.get("state") in (None, "running", "waiting", "imaging") and p.get("legacy"):
                p["state"] = "done"
        elif crops:
            ny, nx = crops[0].shape
            scales = [float(np.abs(c).max() / 32767) or 1.0 for c in crops]
            arr = np.stack([np.round(c / s) for c, s in zip(crops, scales)]).astype("<i2")
            open(f"{OUT}/data/{p['product']}.txt", "w").write(base64.b64encode(arr.tobytes()).decode())
            p["data"] = {"file": f"data/{p['product']}.txt", "nx": nx, "ny": ny, "extent": extent, "scale": scales}
            if p.get("state") in (None, "running", "waiting", "imaging") and p.get("legacy"):
                p["state"] = "done"
        p["lc"] = lightcurve(p["sun"], p["ch"])
        p["calibration"] = calibration(p)
        if fns:   # brightest frame: full-resolution figure and EUV context
            best = fns[int(np.argmax([fr["peak"] for fr in frames]))]
            p["full"] = full_png(p, best)
            p["euv"] = euv(p, best)
        prods.append(p)

    evs = []
    for sun in sorted({p["sun"] for p in prods}):
        e = dict(events.get(sun, {}), sun=sun)
        e["channels"] = channels(sun)
        t = next((fr["t"] for p in prods if p["sun"] == sun for fr in p["frames"]), "")
        if not t:
            mf = f"{SCR}/mwa/events/{sun}/{sun}.metafits"
            if os.path.exists(mf):
                t = fits.getheader(mf).get("DATE-OBS", "")
        # before the metafits is unpacked: date and window from the event table (candidate list)
        e["date"] = t[:10] or e.get("obs_start", "")[:10]
        w = obs_window(sun)
        if w[0]:
            e["obs_start"], e["obs_end"] = w
        e.setdefault("obs_start", ""); e.setdefault("obs_end", "")
        cached = events.get(sun, {})   # an empty list cached without a window was never really queried
        if ("goes" not in cached or (not cached["goes"] and not cached.get("goes_window"))) and e["obs_start"]:
            try:
                events.setdefault(sun, {})["goes"] = goes_flares(e["obs_start"], e["obs_end"])
                events[sun]["goes_window"] = [e["obs_start"], e["obs_end"]]
            except Exception as err:
                print(f"GOES query for {sun} failed: {err}")
        e["goes"] = events.get(sun, {}).get("goes")
        if t:
            e["grid"] = grid_lines(t)
        ctx = e.pop("context", "")
        if ctx and os.path.exists(ctx):
            shutil.copy(ctx, f"{OUT}/img/{os.path.basename(ctx)}")
            e["context_png"] = f"img/{os.path.basename(ctx)}"
        evs.append(e)
    json.dump(events, open(f"{PR}/events.json", "w"), indent=1)    # cached GOES lists
    json.dump({"generated": time.strftime("%Y-%m-%d %H:%M %Z"), "events": evs, "products": prods},
              open(f"{OUT}/board.json", "w"), separators=(",", ":"))
    print(f"{len(evs)} events, {len(prods)} products, {sum(len(p['frames']) for p in prods)} frames -> {OUT}")


if __name__ == "__main__":
    main()
