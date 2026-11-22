# Next noon-list day: 8 December 2015

The catalogue row after 4 December. Not Figure 4 (3 December 03:39) and not
the 4 December noon scan. Four days later; a co-rotating compact feature
should shift several hundred arcsec west if it is the same source.

| | Sun | Cen A |
|---|---|---|
| obs | **1133581016** | **1133571896** |
| UTC | 03:36:39–03:41:35 | 01:04:39–01:06:31 |
| length | 296 s | 112 s |
| native | 0.5 s, 40 kHz | 0.5 s, 40 kHz |
| quality | Good, not deleted | Good, not deleted |
| tiles | 118 / 128 good | 117 / 128 good |
| pointing | RA 254.422°, Dec −19.680° | Cen A |
| Sun elevation | 82.4° | — |
| From cal | −2.53 h | — |

Same 24 coarse channels as Figure 4 (including 84–85, 125–126, 169–170,
187–188). TAP, 22 November 2026.

## Conversion (same as 4 December)

```text
Sun:  output=ms,avg_time_res=0.5,avg_freq_res=160,flag_edge_width=80,no_rfi=true
CenA: output=ms,avg_time_res=4,  avg_freq_res=160,flag_edge_width=80,no_rfi=true
```

No AOFlagger. Phase-only CASA bandpass on Cen A, SuperUniform 0.5 s
frames. Whole-Sun flux from Haslam 1982 **at this pointing**, not Oberoi
2017 Table 1 (that table was used on 4 December and is the wrong sky).

## Jobs

Submitted 22 November 2026 from calculon.

| Observation | ASVO job | Parameters |
|---|---|---|
| Sun `1133581016` | **1125023** | 0.5 s, 160 kHz, `no_rfi` |
| Cen A `1133571896` | **1125024** | 4 s, 160 kHz, `no_rfi` |
