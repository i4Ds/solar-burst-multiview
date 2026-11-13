# Sharma & Oberoi 2020 Figure 4 pipeline

Forget 2022. This is the 2020 paper (ApJ 903, 126), quiet scan
`1133149192`, 03:39:36–03:44:32 UT.

## What actually wrote the published images

Taken from the last `imager::clean()` in the FITS HISTORY (CASA 5.3.0-143,
15–16 May 2020). Same numbers at 108, 162, 217 and 240 MHz.

| | |
|---|---|
| Task | classic `clean` (`imager::clean`), not `tclean` |
| Grid | 1024², 50″, Stokes I, MFS |
| Weighting | **SuperUniform**, uv cell `[−3, 3]` |
| Deconvolver | multifield **Hogbom** |
| Loop | gain 0.1, **niter 8000**, threshold 0 mJy |
| Phase centre | J2000 16h40m55.28s −19d40m25.38s |
| UV-range | empty (the paper text says per-band UV-range; these files have none) |
| Time / freq | one 0.5 s × 2.56 MHz frame per FITS, 570 frames |

Check any file:

```bash
python scripts/sharma2020_fits_history.py
```

A previous remake used Briggs robust 0 and 2500 iterations. That is **not**
what these FITS are.

## Kelvin (paper §4)

1. Whole-Sun flux `S_⊙` from Oberoi, Sharma & Rogers (2017) on the
   visibilities (short baselines Tile011/021/022/023, Haslam 1982 sky at
   *this* pointing).
2. Each 0.5 s map → Mohan & Oberoi (2017) `F(ν)` at **5σ** of the off-Sun
   RMS → `T_B` with the restoring beam in that FITS.
3. Time-mean of those `T_B` maps.

```bash
python scripts/sharma2020_pipeline.py          # ~few minutes, 4×570 FITS
python scripts/sharma2020_pipeline.py --reuse
```

Writes `figures/sharma2020/fig4_paper.png`. Does not touch `fig4.png`.

## Re-image from visibilities (calculon)

No CASA on the laptop. Same `clean` numbers, one mid-scan 0.5 s first,
then more frames. Output only under `/scratch/$USER/mwa/sharma2020/paper/`.

```bash
scp scripts/calculon/sharma2020_casa_snap.py \
    calculon:~/mwa/sharma2020/sharma2020_casa_snap.py
sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-paper-casa.sbatch
```

All 570 half-second frames (the mean is Figure 4) are being remade on
calculon under `paper/casa_su/{108,162,217,240}MHz_NNNN.fits`. A single
mid-scan frame only checked the settings. Empty timeranges are skipped.
Shape matches his frame `.0306` (correlation 0.999). Blob size:

| MHz | Rohit | Briggs 2500 | SuperUniform 8000 |
|---|---|---|---|
| 108 | 225″×217″ | 291″×278″ | 217″×205″ (close) |
| 162 | 198″×185″ | 226″×207″ | 160″×150″ (too sharp) |
| 217 | 189″×186″ | 158″×146″ | 128″×119″ (too sharp) |
| 240 | 208″×202″ | 223″×210″ | 183″×157″ |

108 MHz moved the right way. 162/217 overshot. Leftover: CASA 6.6 `tclean`
vs his 5.3 `clean`.

## Leftovers versus the letter of the papers (for Rohit)

- FEKO embedded tile patterns were never published. `T_Sky` uses Haslam 1982
  × a 4×4 array-factor beam; `Ω_P`, `T_Rec`, `T_Pick-up` stay on Oberoi 2017
  Table 1.
- `r_N` uses `|V|` (autos were FLAG-blanked; `Re(W)` cancelled).
- One `S_⊙` per band for the scan, not a 0.5 s dynamic spectrum (Fig. 3 is
  featureless, so this should be close).
- Per-band UV-range: not in these FITS.
- Re-imaging is not bit-exact with CASA 5.3.0-143 `clean`.
