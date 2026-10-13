#!/bin/zsh
# launchd 临时任务：launch_job.sh <label> <command...>   日志 logs/launchd-<label>.{out,err}.log
set -u; L=$1; shift; R=/Users/iason/Developer/python-ai-playground/DUAL-MAC-TEST-2026-10; P=$R/launchd/com.iason.$L.plist; mkdir -p $R/launchd $R/logs
{ echo '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict>'
  echo "<key>Label</key><string>com.iason.$L</string><key>RunAtLoad</key><true/><key>KeepAlive</key><false/>"
  echo "<key>EnvironmentVariables</key><dict><key>HOME</key><string>/Users/iason</string><key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string><key>PLAYWRIGHT_BROWSERS_PATH</key><string>/Users/iason/.cache/ms-playwright</string></dict>"
  echo "<key>StandardOutPath</key><string>$R/logs/launchd-$L.out.log</string><key>StandardErrorPath</key><string>$R/logs/launchd-$L.err.log</string>"
  echo "<key>ProgramArguments</key><array>"; for arg in "$@"; do printf '<string>%s</string>' "${arg//&/&amp;}" | sed 's/</\&lt;/g; s/>/\&gt;/g; s/\&lt;string\&gt;/<string>/; s/\&lt;\/string\&gt;/<\/string>/'; echo; done; echo "</array></dict></plist>"; } > "$P"
plutil -lint "$P" >/dev/null || { echo "bad plist"; exit 1; }
launchctl bootout gui/$(id -u)/com.iason.$L 2>/dev/null; launchctl bootstrap gui/$(id -u) "$P" && echo "started com.iason.$L"
