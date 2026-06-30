#!/usr/bin/env bash
# Ship the BAD deploy "v2.3" — swap the image to one that exits immediately.
# busybox's default process exits right away → CrashLoopBackOff → container
# restarts climb + pods go not-ready. That's the incident the SRE agent fixes
# by rolling back to the known-good nginx image.
set -euo pipefail

kubectl set image deployment/checkout-api app=busybox:1.36 --record 2>/dev/null || \
  kubectl set image deployment/checkout-api app=busybox:1.36
kubectl annotate deployment/checkout-api \
  kubernetes.io/change-cause="v2.3 bad build (crash on boot)" --overwrite

echo "Shipped v2.3 (crash-looping). Watch it fail:"
echo "  kubectl get pods -l app=checkout-api -w"
