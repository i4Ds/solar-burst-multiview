# Quiet-Sun selection 2013-2015 (12 Nov 2026)

`quiet_noon_2013_2015.csv`: one Sun observation per day, the one closest to local solar
noon (hour angle `ha_h`, hours), from André's list `data/G0002_2013_2015_good_only.xlsx`
(G0002, Phase I, quality Good; 976 Sun observations on 351 days). Only observations with
archived data and not flagged deleted: 305 days (2013: 42, 2014: 95, 2015: 168).
`sun_alt`: Sun elevation at mid-observation at the MWA (astropy).

Calibrator (`cal_*`): the archived calibrator observation with the same channel set
nearest in time (MWA TAP); `cal_dt_h` in hours. Within 24 h for 238 days; none for the
42 days of 2013. Planned ASVO conversion: 10 s, 160 kHz, no_rfi=true (no AOFlagger).
