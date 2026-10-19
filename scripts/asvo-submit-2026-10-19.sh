#!/bin/bash
# ASVO submissions; needs MWA_ASVO_API_KEY. Record the job ids in configs/asvo_jobs.csv.
set -euo pipefail
: "${MWA_ASVO_API_KEY:?set MWA_ASVO_API_KEY}"
# batch 0: 2 obs, 0.15 TB in the archive (conversions come out smaller)
giant-squid submit-vis 1419137296
giant-squid submit-conv -p output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1419161128
# batch 1: 25 obs, 5.41 TB in the archive (conversions come out smaller)
giant-squid submit-vis 1443154216 1446861616 1446865216 1446870616 1449551392
giant-squid submit-vis 1449626656 1450835520 1451778960 1451779192 1451801392
giant-squid submit-vis 1458877312 1469325616 1471143136 1471233856 1472706736
giant-squid submit-vis 1475301616
giant-squid submit-conv -p output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1443177000 1446843296 1446893720 1449607880 1469313488
giant-squid submit-conv -p output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1471126944 1471213288 1472725200 1475317992
giant-squid list
