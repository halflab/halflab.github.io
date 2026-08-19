#!/bin/bash
# ============================================================
#  Serve the offline preview to your phone.
#
#  Double-click this file in Finder, or run it from Terminal.
#  It starts a small web server on your Mac and prints the
#  address to type into Safari on your phone.
#
#  Both devices must be on the same Wi-Fi network.
#  Press Ctrl-C in this window to stop the server.
# ============================================================

PORT=8000
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$HERE/preview"

if [ ! -d "$DIR" ]; then
  echo "No preview folder at:"
  echo "  $DIR"
  echo
  echo "Ask Claude to rebuild the preview, then run this again."
  read -r -p "Press return to close. "
  exit 1
fi

# The Mac's address on the local network. Wi-Fi is usually en0, but on some
# machines it is en1, so try both before giving up.
IP=""
for IFACE in en0 en1 en2; do
  CANDIDATE="$(ipconfig getifaddr "$IFACE" 2>/dev/null)"
  if [ -n "$CANDIDATE" ]; then IP="$CANDIDATE"; break; fi
done

if [ -z "$IP" ]; then
  echo "Could not work out this Mac's Wi-Fi address."
  echo "Check you are connected to Wi-Fi, then look it up by hand:"
  echo "  System Settings > Wi-Fi > Details > IP Address"
  echo
  IP="YOUR-MACS-ADDRESS"
fi

echo
echo "============================================================"
echo "  On your phone, open Safari and go to:"
echo
echo "      http://$IP:$PORT"
echo
echo "  Serving: $DIR"
echo "  Stop the server with Ctrl-C."
echo "============================================================"
echo
echo "  If the phone cannot reach it:"
echo "   - both devices on the same Wi-Fi?"
echo "   - macOS may ask Terminal for permission to find devices on"
echo "     the local network the first time. Allow it."
echo "     (System Settings > Privacy & Security > Local Network)"
echo "   - a VPN on either device will usually break this."
echo

cd "$DIR" || exit 1
python3 -m http.server "$PORT"
