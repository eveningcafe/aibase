#!/usr/bin/env bash
# Push the runbook to Kaggle as a GPU script kernel, wait, and fetch output.
#   ./push.sh <your-kaggle-username>
# Needs: kaggle CLI + ~/.kaggle/kaggle.json (see README). Phone-verify your
# Kaggle account first or GPU/Internet stay disabled.
set -euo pipefail
KUSER="${1:?usage: ./push.sh <kaggle-username>}"
SLUG="aibase-models-runbook"
cd "$(dirname "$0")"

command -v kaggle >/dev/null || pip install --quiet kaggle

cat > kernel-metadata.json <<JSON
{
  "id": "${KUSER}/${SLUG}",
  "title": "aibase models runbook",
  "code_file": "run_lab.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": [],
  "competition_sources": [],
  "kernel_sources": []
}
JSON

echo ">> pushing ${KUSER}/${SLUG} ..."
kaggle kernels push -p .

echo ">> polling status (Ctrl-C to stop; the run continues on Kaggle) ..."
for i in $(seq 1 90); do
  sleep 20
  st="$(kaggle kernels status "${KUSER}/${SLUG}" 2>/dev/null || true)"
  echo "[$((i*20))s] $st"
  echo "$st" | grep -qiE "complete|error|cancelAcknowledged" && break
done

echo ">> fetching output ..."
mkdir -p output
kaggle kernels output "${KUSER}/${SLUG}" -p ./output || true
echo ">> done. Look at ./output/ (run log + results.json). Or view at:"
echo "   https://www.kaggle.com/code/${KUSER}/${SLUG}"
