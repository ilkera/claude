#!/usr/bin/env python3
"""Independent monitoring dashboard for the WhatsApp notifier service."""

from __future__ import annotations

import json
import os
import signal
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

EVENTS_FILE = os.getenv("EVENTS_FILE", "events_log.json")
PID_FILE = EVENTS_FILE.replace(".json", ".pid")
MONITOR_PORT = int(os.getenv("MONITOR_PORT", "8080"))


def is_service_running() -> bool:
    """Check if the main service process is alive via its PID file."""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # signal 0 = check if process exists
        return True
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        return False

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitor Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Courier New',monospace;background:#0d1117;color:#c9d1d9;padding:20px}
h1{font-size:1.4em;margin-bottom:16px;color:#58a6ff}
.status-bar{display:flex;gap:24px;align-items:center;padding:16px;background:#161b22;
  border:1px solid #30363d;border-radius:8px;margin-bottom:16px;flex-wrap:wrap}
.status-indicator{display:flex;align-items:center;gap:8px;font-size:1.1em;font-weight:bold}
.dot{width:14px;height:14px;border-radius:50%;display:inline-block}
.dot.green{background:#3fb950;box-shadow:0 0 8px #3fb950}
.dot.yellow{background:#d29922;box-shadow:0 0 8px #d29922}
.dot.red{background:#f85149;box-shadow:0 0 8px #f85149}
.stat{text-align:center}
.stat .label{font-size:0.75em;color:#8b949e;text-transform:uppercase}
.stat .value{font-size:1.3em;color:#f0f6fc;font-weight:bold}
.events{max-height:70vh;overflow-y:auto;border:1px solid #30363d;border-radius:8px}
.event{padding:10px 14px;border-bottom:1px solid #21262d;display:flex;gap:12px;
  align-items:flex-start;font-size:0.85em}
.event:last-child{border-bottom:none}
.event:hover{background:#161b22}
.event .time{color:#8b949e;white-space:nowrap;min-width:80px}
.event .type{font-weight:bold;min-width:140px;white-space:nowrap}
.event .details{color:#8b949e;overflow:hidden;text-overflow:ellipsis}
.type-service_start{color:#3fb950}.type-service_stop{color:#f85149}
.type-poll_start{color:#58a6ff}.type-poll_end{color:#58a6ff}
.type-notification_sent{color:#d2a8ff}.type-notification_skipped{color:#8b949e}
.type-error{color:#f85149}
.refresh-note{text-align:center;color:#484f58;font-size:0.75em;margin-top:8px}
</style>
</head>
<body>
<h1>Trump Social Feed Monitor</h1>
<div class="status-bar">
  <div class="status-indicator"><span class="dot" id="statusDot"></span><span id="statusText">Loading...</span></div>
  <div class="status-indicator"><span class="dot" id="processDot"></span><span id="processText">Process: --</span></div>
  <div class="stat"><div class="label">Uptime</div><div class="value" id="uptime">--</div></div>
  <div class="stat"><div class="label">Polls (24h)</div><div class="value" id="pollCount">--</div></div>
  <div class="stat"><div class="label">Posts Found (24h)</div><div class="value" id="postsFound">--</div></div>
  <div class="stat"><div class="label">Notifications (24h)</div><div class="value" id="notifCount">--</div></div>
</div>
<div class="events" id="eventList"></div>
<div class="refresh-note">Auto-refreshes every 30s</div>
<script>
function formatTime(iso){
  const d=new Date(iso);
  return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
function formatDuration(ms){
  const s=Math.floor(ms/1000);
  if(s<60)return s+'s';
  const m=Math.floor(s/60);const h=Math.floor(m/60);
  if(h>0)return h+'h '+m%60+'m';
  return m+'m '+s%60+'s';
}
function eventDetails(e){
  switch(e.event_type){
    case 'poll_end':return 'found:'+e.posts_found+' new:'+e.new_posts+' ('+e.duration_ms+'ms)';
    case 'notification_sent':return (e.topics||[]).join(', ')+' ['+((e.relevance_score||0).toFixed(2))+']';
    case 'notification_skipped':return e.reason||'';
    case 'error':return (e.error_type||'')+': '+(e.message||'');
    case 'service_stop':return e.reason||'';
    default:return '';
  }
}
async function refresh(){
  try{
    const [r,sr]=await Promise.all([fetch('/api/events?limit=500'),fetch('/api/status')]);
    const events=await r.json();
    const status=await sr.json();
    const pDot=document.getElementById('processDot');
    const pTxt=document.getElementById('processText');
    if(status.running){
      pDot.className='dot green';pTxt.textContent='Process: Running (PID '+status.pid+')';
    }else{
      pDot.className='dot red';pTxt.textContent='Process: Not Running';
    }
    const now=Date.now();
    const h24=now-86400000;
    const h1=now-3600000;
    // Status
    const dot=document.getElementById('statusDot');
    const txt=document.getElementById('statusText');
    if(events.length===0){
      dot.className='dot red';txt.textContent='No Data';
    }else{
      const last=events[0];
      const lastTime=new Date(last.timestamp).getTime();
      const errorsLastHour=events.filter(e=>e.event_type==='error'&&new Date(e.timestamp).getTime()>h1).length;
      if(last.event_type==='service_stop'){
        dot.className='dot red';txt.textContent='Stopped';
      }else if(now-lastTime>900000){
        dot.className='dot red';txt.textContent='Down';
      }else if(errorsLastHour>=3){
        dot.className='dot yellow';txt.textContent='Degraded';
      }else{
        dot.className='dot green';txt.textContent='Online';
      }
    }
    // Uptime
    const starts=events.filter(e=>e.event_type==='service_start');
    const uptimeEl=document.getElementById('uptime');
    if(starts.length>0){
      uptimeEl.textContent=formatDuration(now-new Date(starts[0].timestamp).getTime());
    }else{uptimeEl.textContent='--';}
    // 24h stats
    const recent=events.filter(e=>new Date(e.timestamp).getTime()>h24);
    document.getElementById('pollCount').textContent=recent.filter(e=>e.event_type==='poll_end').length;
    document.getElementById('postsFound').textContent=recent.filter(e=>e.event_type==='poll_end').reduce((a,e)=>a+(e.posts_found||0),0);
    document.getElementById('notifCount').textContent=recent.filter(e=>e.event_type==='notification_sent').length;
    // Event list
    const list=document.getElementById('eventList');
    list.innerHTML=events.slice(0,200).map(e=>`<div class="event">
      <span class="time">${formatTime(e.timestamp)}</span>
      <span class="type type-${e.event_type}">${e.event_type}</span>
      <span class="details">${eventDetails(e)}</span>
    </div>`).join('');
  }catch(err){console.error('Refresh failed',err);}
}
refresh();
setInterval(refresh,30000);
</script>
</body>
</html>
"""


def read_events(limit: int = 200) -> list[dict]:
    """Read events from the JSONL file, return newest first."""
    if not os.path.exists(EVENTS_FILE):
        return []
    events = []
    with open(EVENTS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    events.reverse()
    return events[:limit]


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        elif parsed.path == "/api/status":
            running = is_service_running()
            pid = None
            if running:
                try:
                    with open(PID_FILE) as f:
                        pid = int(f.read().strip())
                except (ValueError, FileNotFoundError):
                    pass
            data = {"running": running, "pid": pid}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        elif parsed.path == "/api/events":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", ["200"])[0])
            limit = max(1, min(limit, 1000))
            events = read_events(limit)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(events).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        print(f"[dashboard] {args[0]}")


def main() -> None:
    server = HTTPServer(("", MONITOR_PORT), DashboardHandler)
    print(f"Dashboard running at http://localhost:{MONITOR_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard")
        server.shutdown()


if __name__ == "__main__":
    main()
