#!/usr/bin/env bash
# Build static/css/build.css, the one stylesheet a page loads, from static/css/tailwind.css:
# app.css in a lower layer, Tailwind's utilities above it (technical addendum A8).
#
#   tools/tailwind.sh           build once
#   tools/tailwind.sh --watch   rebuild on every change while you work on a page
#   tools/tailwind.sh --check   fail if the committed build.css is not what the sources make
#
# The standalone executable needs no Node. It is pinned to one release and checked against
# that release's SHA-256 before it runs; a new release means new sums here, not a new download.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION=4.3.3
case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)  PLATFORM=macos-arm64  SUM=cdf646702987a743464dff4d9c60fd4480d1c1e73dd819a9a67f1078815dce9d ;;
    Darwin-x86_64) PLATFORM=macos-x64    SUM=7922e0953f2110c05976e3bf58f14e643d90427575e766b7d433f5f80cbee7e1 ;;
    Linux-x86_64)  PLATFORM=linux-x64    SUM=dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a ;;
    Linux-aarch64) PLATFORM=linux-arm64  SUM=55fd0b241214eff3de1e8ee4f22796662f2d2e7a49bcfca7477cfd0bac398195 ;;
    *) echo "No pinned Tailwind build for $(uname -s)-$(uname -m)." >&2; exit 1 ;;
esac

BIN="tools/bin/tailwindcss-$VERSION-$PLATFORM"
if [[ ! -x "$BIN" ]]; then
    mkdir -p tools/bin
    curl -fsSL -o "$BIN.part" \
        "https://github.com/tailwindlabs/tailwindcss/releases/download/v$VERSION/tailwindcss-$PLATFORM"
    got=$(shasum -a 256 "$BIN.part" | cut -d' ' -f1)
    if [[ "$got" != "$SUM" ]]; then
        rm -f "$BIN.part"
        echo "tailwindcss-$PLATFORM v$VERSION: SHA-256 $got, expected $SUM. Not run." >&2
        exit 1
    fi
    chmod +x "$BIN.part" && mv "$BIN.part" "$BIN"
fi

IN=static/css/tailwind.css
OUT=static/css/build.css
if [[ "${1:-}" == "--check" ]]; then
    fresh=$(mktemp)
    "$BIN" -i "$IN" -o "$fresh" 2>/dev/null
    if ! cmp -s "$fresh" "$OUT"; then
        rm -f "$fresh"
        echo "$OUT is out of date with its sources: run tools/tailwind.sh and commit it." >&2
        exit 1
    fi
    rm -f "$fresh"
    echo "$OUT is up to date."
else
    "$BIN" -i "$IN" -o "$OUT" "$@"
fi
