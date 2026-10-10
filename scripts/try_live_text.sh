#!/bin/bash
# One-off trial: does photocraft add a LIVE text layer to one of our PSDs, and how does it describe the layers?
# Writes ~/craft-try/text-test.psd and prints what it finds. Safe: reads one PSD, writes only into ~/craft-try.
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate
PSD=$(ls out/products/*wall_art/product/Editable-files/vector/design-01.psd 2>/dev/null | tail -1)
[ -z "$PSD" ] && { echo "No design-01.psd found. Run: moneyhub export craft <wall art id> --kinds vectors"; exit 1; }
mkdir -p ~/craft-try
echo "Using: $PSD"
echo "=== type.create"
moneyhub craft photocraft run "$PSD" --cmd type.create \
  --params '{"text":"Live text test","x":120,"y":300,"name":"TestText","font":"Poppins","weight":700,"size":64,"color":"#ff0000"}' \
  --out ~/craft-try/text-test.psd 2>&1 | cut -c1-500
echo "=== info (first 2500 characters)"
moneyhub craft photocraft info ~/craft-try/text-test.psd --compact 2>&1 | cut -c1-2500
echo "=== live text blocks in the file (0 means no live text)"
python3 -c "import os; b=open(os.path.expanduser('~/craft-try/text-test.psd'),'rb').read(); print(b.count(b'TySh'))"
echo "=== fonts photocraft can see (Poppins / DM Sans)"
moneyhub craft photocraft run --new '{"width":100,"height":100}' --cmd type.fonts 2>&1 | grep -i -E "poppins|dm ?sans" | head -8 | cut -c1-200
