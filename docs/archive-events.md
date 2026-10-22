# Archive events: one image per burst

Plan: `docs/burst-imaging-plan.md`. Coarse channel 127 (162.5 MHz), 4 s at the
maximum of the MWA short-baseline light curve, P-AIRCARS self-cal, no AOFlagger.
Made with `scripts/calculon/event_image.sh`.

| event (UTC) | MWA obs | phase | calibrator | 4 s image | peak | peak/rms | position (half-max centroid) | T_B (RJ, beam) | status |
|---|---|---|---|---|---|---|---|---|---|
| 2024-12-25 type II | 1419137296 (OA004) | III, 94 of 120 tiles | 1419161128 PKS2356-61 (+6.6 h) | 04:51:45.5–49.5 | 2.69×10⁵ Jy/beam | 144 | (−187″, −572″), 0.63 R☉ projected | 1.3×10⁹ K | done 20 Oct |

## 2024-12-25 type II (1419137296)

![162.5 MHz image](../figures/events/1419137296_ch127_zoom.png)

![MWA light curve at 162.5 MHz](../figures/events/1419137296_ch127_lightcurve.png)

- One compact source, about 2.8 beams above half maximum (beam 110″ × 90″),
  in the south of the disk, projected at about S35–40, 10° east of the central
  meridian (Stonyhurst grid in the figure).
- Flare at the same time (checked 20 Oct in HEK): GOES M4.9, 04:46–04:53 UTC,
  peak 04:49, NOAA AR 13932. HEK has no position for it (SWPC placeholder 0″, 0″).
  AR 13932 at 04:00: HMI SHARP centroid (6″, −188″), S13 W0. The STIX flare list
  (Hayes et al., Earth view and Earth time) has one event 04:16–05:46 UTC, peak
  04:49:06, at (−88″, −297″), in or next to AR 13932; it spans both the GOES M4.9
  and an earlier GOES M2.8 (04:14–04:39, AR 13938 at the NE limb), hence its
  "M6" estimate. The image (04:51:45) is 2.5 min after the flare peak.
- The radio source lies about 290″ south-southeast of the STIX position (about
  20° east of due south) and about 430″ south-southeast of the AR 13932 SHARP
  centroid. This is an observation, not yet an interpretation. (Corrected 22 Oct:
  this line said "south-southwest" and 290″ from both; both positions have a
  larger x than the radio source, i.e. the source is to their east.)
- Off-Sun rms 1.9×10³ Jy/beam (r > 2500″).
- **To check before trusting the brightness:** the light curve at 162.5 MHz has
  three flat-topped maxima at the same level (11–12 × median), at about 110 s,
  200–215 s and 228–235 s after 04:47:58. Equal flat tops could mean clipping in
  the receiver or correlator. Not confirmed. The chain picked the last one
  (228 s), which is only a few percent above the others and 9 s before the end of
  the observation.
- T_B is Rayleigh–Jeans from the restoring beam, not cross-checked against the
  quiet Sun for this observation.

Files on calculon: image
`/scratch/andre_csillaghy/paircars/out/1419137296_ch127/20241225/1419137296_target/imagedir_f_1.28_t_4.0_pol_I_w_briggs_0.0_peak4s/pbcor_hpcs/`,
status `~/mwa/events/1419137296.md`.

## Phase IIIb events, batches 1 and 2 (21–22 Oct): made, not yet reviewed

From the status files `~/mwa/events/<obsid>.md` on calculon (read 22 Oct, 04:00
calculon time). Each has one 4 s P-AIRCARS image in
`/scratch/andre_csillaghy/paircars/out/<obsid>_ch<ch>/<date>/<obsid>_target/imagedir_f_1.28_t_4.0_pol_I_w_briggs_0.0_peak4s/pbcor_hpcs/`.
Peak, position and T_B are not yet in this table (they are in the board export,
`~/mwa/board/board.json`); no verdicts on the board yet.
"LC max" is the MWA short-baseline light curve at the chosen window over its
median: below about 2 the chain picked the highest point of a curve with no
clear burst at this frequency (plan: such bursts are to be marked, not moved).

| obs | 4 s window (UTC) | channel | calibrator (MSs) | LC max / median | status |
|---|---|---|---|---|---|
| 1469325616 | 2026-07-29 02:00:36 | 127 | 1469313488 (24) | 70.1 | image 21 Oct |
| 1446861616 | 2025-11-11 02:00:11 | 127 | 1446843296 (24) | 27.9 | image 21 Oct (rerun) |
| 1451778960 | 2026-01-06 23:56:42 | 128, 163.2–164.3 MHz | 1451768544 (1) | 14.4 | image 21 Oct |
| 1450835520 | 2025-12-27 01:51:55 | 127 | 1450817864 (24) | 11.6 | image 22 Oct |
| 1451801392 | 2026-01-07 06:11:11 | 129, 164.5–165.6 MHz | 1451820360 (1) | 3.7 | image 21 Oct |
| 1446870616 | 2025-11-11 04:31:45 | 127 | 1446893720 (24) | 3.3 | image 21 Oct |
| 1451779192 | 2026-01-06 23:59:49 | 127 | 1451768712 (24) | 3.2 | image 22 Oct |
| 1475301616 | 2026-10-06 06:01:28 | 127 | 1475317992 (24) | 1.6 | image 21 Oct; no clear burst at 162.5 MHz |
| 1449551392 | 2025-12-12 05:11:15 | 132, 168.3–169.4 MHz | 1449573328 (1) | 1.5 | image 22 Oct; no clear burst at 168.9 MHz |
| 1446865216 | 2025-11-11 03:01:32 | 127 | 1446843296 (24) | 1.4 | image 21 Oct; no clear burst at 162.5 MHz |
| 1458877312 | — | 127 | 1458901872 | — | Birli running 22 Oct |

1449551392 ran at channel 132, not 126 as in `configs/events/batch2.txt`: the
calculon list `~/mwa/events/rerun3.txt` says the archive has 12 of its 24
channels. Channels 128, 129 and 132 are not comparable with the channel 127 images.
