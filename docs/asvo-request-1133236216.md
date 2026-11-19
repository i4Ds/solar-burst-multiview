# First quiet-Sun control: 4 December 2015, noon scan

Same pipeline as the Figure 4 remake from archive visibilities. One day,
to see that the method holds before the 238 days that have a calibrator.

| | Sun | Cen A |
|---|---|---|
| obs | **1133236216** | **1133236576** |
| UTC | 03:49:59–03:54:55 | 03:55:59–03:57:51 |
| length | **296 s** (same as Figure 4) | 112 s |
| native | 0.5 s, 40 kHz | 0.5 s, 40 kHz |
| quality | Good, not deleted | Good, not deleted |
| tiles | 118 / 128 good | 117 / 128 good |
| pointing | RA 246.589°, Dec −19.863° | Cen A |

The Sun scan ends at 03:54:55; Cen A starts at 03:55:59, **one minute
later**, same 24 coarse channels as Figure 4 (including 84–85, 125–126,
169–170, 187–188). Sun elevation 84.6°. This is the noon pick from
`configs/quiet/quiet_noon_2013_2015.csv` for 4 December 2015. It is not
the Sharma & Oberoi 2020 scan (`1133149192`, 3 December 03:39).

TAP, 19 November 2026 (`mwa.observation`). No tar for either obs on the
NAS that day.

## Conversion (same parameters as the Figure 4 remake on disk)

```text
Sun:  output=ms,avg_time_res=0.5,avg_freq_res=160,flag_edge_width=80,no_rfi=true
CenA: output=ms,avg_time_res=4,  avg_freq_res=160,flag_edge_width=80,no_rfi=true
```

160 kHz matches the measurement sets that produced
`fig4_his_vs_raw_shape.png`. Native 40 kHz is the outstanding Figure 4
request, not this control. No AOFlagger. No `apply_di_cal`.

After download we keep the four Figure 4 pairs only.

## Calibration and imaging (no P-AIRCARS)

1. CASA `bandpass` on Cen A, B Jones, then set |g| ≡ 1 (phase only), as
   in Rohit's `.cal.p` tables.
2. `applycal` on the 0.5 s Sun, `applymode=calonly`, `calwt=False`.
3. SuperUniform, Hogbom, niter 8000, 1024², 50″, one 0.5 s frame, all
   integrations in the 296 s scan. Phase centre is **this** observation's
   pointing, not the 3 December coordinates.
4. Oberoi whole-Sun flux with Haslam 1982 at this pointing; Mohan F(ν) at
   5σ; time mean of the brightness-temperature maps.

## Jobs

Submitted 19 November 2026 from calculon.

| Observation | ASVO job | Parameters |
|---|---|---|
| Sun `1133236216` | **1124591** | 0.5 s, 160 kHz, `no_rfi` |
| Cen A `1133236576` | **1124592** | 4 s, 160 kHz, `no_rfi` |
