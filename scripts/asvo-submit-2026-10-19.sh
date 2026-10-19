#!/bin/bash
# ASVO submissions, one obsid per call; a refused obsid is reported and skipped.
# Needs MWA_ASVO_API_KEY. Paste the final list back so the job ids go into configs/asvo_jobs.csv.
: "${MWA_ASVO_API_KEY:?set MWA_ASVO_API_KEY}"
failed=()
# batch 1: 15 obs, 2.48 TB in the archive (conversions come out smaller)
giant-squid submit-vis 1446861616 || failed+=(1446861616)
giant-squid submit-vis 1446865216 || failed+=(1446865216)
giant-squid submit-vis 1446870616 || failed+=(1446870616)
giant-squid submit-vis 1449551392 || failed+=(1449551392)
giant-squid submit-vis 1450835520 || failed+=(1450835520)
giant-squid submit-vis 1451778960 || failed+=(1451778960)
giant-squid submit-vis 1451779192 || failed+=(1451779192)
giant-squid submit-vis 1451801392 || failed+=(1451801392)
giant-squid submit-vis 1458877312 || failed+=(1458877312)
giant-squid submit-vis 1469325616 || failed+=(1469325616)
giant-squid submit-vis 1475301616 || failed+=(1475301616)
giant-squid submit-conv -p output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1446843296 || failed+=(1446843296)
giant-squid submit-conv -p output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1446893720 || failed+=(1446893720)
giant-squid submit-conv -p output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1469313488 || failed+=(1469313488)
giant-squid submit-conv -p output=ms,avg_time_res=2,avg_freq_res=160,flag_edge_width=80,no_rfi=true 1475317992 || failed+=(1475317992)
echo; echo "not submitted (${#failed[@]}): ${failed[*]:-none}"
giant-squid list
