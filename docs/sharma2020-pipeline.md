# Sharma & Oberoi 2020 imaging pipeline (parallel comparison)

Two paths for the 2015-12-03 quiet scan (obsid `1133149192`, Fig. 4).
Neither writes into Rohit’s tree or overwrites `figures/sharma2020/fig4.png`.

| Path | What it is | Scratch / figure |
|---|---|---|
| **A. WSClean comparison** | Re-image `CORRECTED_DATA`, MFS over 4 min, no Oberoi 2017 flux. Jobs `168583_0–3`. | `/scratch/$USER/mwa/sharma2020/fig4/` → `fig4_wsclean.png` |
| **B. Paper method** | Oberoi 2017 `S_⊙` from short baselines, CASA 0.5 s / 2 MHz snapshots, Mohan 2017 `F(ν)` then `T_B`. | `/scratch/$USER/mwa/sharma2020/paper/` → `fig4_paper.png` |

## Paper method (what Sharma & Oberoi 2020 actually did)

From the paper (arXiv:2009.10604 §3) and the two method papers:

1. **Flux, non-imaging.** Oberoi, Sharma & Rogers (2017, Sol Phys 292, 75).
   Normalised correlation on six short baselines
   `r_N = W_ij / sqrt(W_ii W_jj)` (gain-independent). Solve Eq. 16 for
   `T_⊙,P`, then `S_⊙ = 2 k T_⊙,P Ω_P / λ²`. Their example tiles:
   Tile011, 021, 022, 023. Baselines ≲ 10 λ.
2. **Imaging.** CASA, 0.5 s × 2 MHz, 1024², 50″. Hogbom, niter 2500,
   gain 0.1, Briggs (published HISTORY; a trial `clean.last` used
   superuniform). “Different UV-ranges” per band — **unverified**; the
   published FITS for this scan have `uvrange=""`. This pipeline leaves
   UV-range empty until a log turns up.
3. **Transfer onto images.** Mohan & Oberoi (2017, Sol Phys 292, 168)
   Eqs. 2–4: `F(ν) = S_⊙ / ∯_C S' dΩ`, `T_B = S c² / (2 k ν² Ω_beam)`.
   Sharma 2020 takes C at **5σ** of the off-Sun RMS (the method paper used
   6σ). Then the time-mean of the 0.5 s `T_B` maps.

`imaging.tb_scale: 9.48` is a 2022-pickle vs Rayleigh–Jeans fudge. It is
**not** this flux scale. Path B uses `scale=1` after `F(ν)`.

## What is implemented vs still approximate

| Term | Status |
|---|---|
| `r_N` from this MS (DATA, six shortest or named tiles) | implemented (`solarburst.oberoi2017`) |
| `T_Rec`, `T_Pick-up`, `Ω_P` | interpolated from Oberoi 2017 Table 1 (MWA-tile hardware / FEKO beam). Analytic 4×4 `Ω_P` matches Table 1 to ~10 % below 170 MHz. |
| `T_Sky`, `T_b,Sky` | Haslam et al. 1982 unfiltered 408 MHz map (LAMBDA `lambda_haslam408_nofilt.fits`, α = −2.55) × 4×4 tile beam at the 2015-12-03 03:42 UT solar pointing. Not Table 1 (that was 2013-09-03, high Galactic latitude). On this date the Sun is ~17° from the Galactic centre, so `T_Sky` is much higher. |
| CASA 0.5 s snapshots | one mid-scan frame per band. `casacore.getcol("TIME")` segfaults on these 35 GB MS in `paircars_env`; the CASA job uses a fixed timerange instead. WSClean `-interval 285` is the backup imager (`paper/wsclean/`). |
| Autocorrelations | Oberoi `r_N` needs `W_ii`. Some Rohit MS omit autos (108/162/217 first try). JSON then records `n_auto_rows=0` and skips `S_⊙`. |
| Mohan `F(ν)` + Fig. 4 | `scripts/sharma2020_paper_tb.py` on the staged CASA FITS, once flux JSON exists |

The Haslam map is the survey Oberoi 2017 cites, not Remazeilles 2015. Download
(gitignored):

```bash
python scripts/sharma2020_haslam_tsky.py          # 2015 pointing, rewrite flux JSON
python scripts/sharma2020_haslam_tsky.py --check-2013
```

FEKO embedded patterns were never published. `P_N` is a 4×4 array-factor beam
with the same tile geometry; Table 1 `Ω_P` is still used in Eq. 10. On the
2013-09-03 pointing the analytic `T_Sky` matches Table 1 at 240 MHz (133 vs
140 K) and is about 2× high at 103 MHz (sidelobe / element-pattern leftover).

`S_⊙` from the 0.5 s MS (DATA, `|V|`, Tile011/021/022/023) with Haslam `T_Sky`
for this LST. In parentheses: the same `r_N` with Table 1 `T_Sky` (2013
pointing). Oberoi 2017 Table 2 is a *different day*, listed only as a check:

| band | r_N | S_⊙ Haslam (this LST) | S_⊙ Table 1 (2013 sky) | Table 2 nearest |
|---|---|---|---|---|
| 108 MHz | 0.094 | 2.87 SFU | 0.82 SFU | 1.71–2.60 SFU (103–117 MHz) |
| 162 MHz | 0.333 | 6.50 SFU | 2.21 SFU | 5.08 SFU (167 MHz) |
| 217 MHz | 0.521 | 11.72 SFU | 6.31 SFU | 11.3 SFU (213 MHz) |
| 240 MHz | 0.470 | 8.17 SFU | 5.74 SFU | 17.1 SFU (240 MHz) |

## Calculon (do not touch Path A)

Scripts live in `~/mwa/sharma2020/` (copy). Output only under
`/scratch/$USER/mwa/sharma2020/paper/`.

```bash
# Now: flux on the 10 s _Sun_10s_cal.ms (WSClean is not using those).
sbatch -M calc-cpu ~/mwa/sharma2020/sharma2020-paper-flux.sbatch

# After WSClean array 168583: flux on the 0.5 s MS, and one CASA snapshot / band.
sbatch -M calc-cpu --dependency=afterany:168583 --export=ALL,USE_FULL_MS=1 \
  ~/mwa/sharma2020/sharma2020-paper-flux.sbatch
sbatch -M calc-cpu --dependency=afterany:168583 \
  ~/mwa/sharma2020/sharma2020-paper-casa.sbatch
```

Pull JSON to the laptop and build the paper-scale figure:

```bash
rsync -av calculon:/scratch/$USER/mwa/sharma2020/paper/flux/ data/quiet2015/paper_flux/
python scripts/sharma2020_paper_tb.py --flux-dir data/quiet2015/paper_flux
```
