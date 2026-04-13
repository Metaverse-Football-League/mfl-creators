#!/bin/bash
cd "$(dirname "$0")"
python3 build.py
open index.html
osascript -e 'tell application "Terminal" to close (every window whose name contains "open-dashboard")' &
