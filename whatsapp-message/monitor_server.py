#!/usr/bin/env python3
"""Independent monitoring dashboard for the WhatsApp notifier service.

Serves an HTML dashboard on port 8080 with collapsible daily event groups.
"""

from __future__ import annotations

import json
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from classify_post import classify

EVENTS_FILE = os.getenv("EVENTS_FILE", "events_log.json")
PID_FILE = EVENTS_FILE.replace(".json", ".pid")
STATE_FILE = os.getenv("STATE_FILE", "seen_posts.json")
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
.day-header{padding:10px 14px;background:#1c2128;border-bottom:1px solid #30363d;
  cursor:pointer;display:flex;justify-content:space-between;align-items:center;
  font-size:0.85em;font-weight:bold;color:#58a6ff;user-select:none}
.day-header:hover{background:#22272e}
.day-header .chevron{color:#8b949e;font-size:0.9em;margin-right:4px}
.day-header .count{color:#8b949e;font-weight:normal;font-size:0.85em}
.day-events{display:block}
.day-events.collapsed{display:none}
.event-expandable{cursor:pointer}
.event-expandable:hover{background:#1c2128}
.event-expand-icon{color:#8b949e;font-size:0.8em;margin-right:4px}
.event-detail{display:none;padding:10px 14px 14px 50px;border-bottom:1px solid #21262d;
  background:#161b22;font-size:0.8em;line-height:1.6}
.event-detail.open{display:block}
.event-detail h4{color:#58a6ff;font-size:0.9em;margin:8px 0 4px;font-weight:bold}
.event-detail h4:first-child{margin-top:0}
.event-detail pre{background:#0d1117;border:1px solid #30363d;border-radius:4px;
  padding:8px;overflow-x:auto;white-space:pre-wrap;word-break:break-word;color:#c9d1d9;
  font-size:0.95em;max-height:200px;overflow-y:auto}
.event-detail .meta-item{color:#8b949e;margin:2px 0}
.event-detail .meta-item span{color:#c9d1d9}
.event-detail .post-block{border-left:2px solid #30363d;padding-left:10px;margin:6px 0}
.tabs{display:flex;gap:0;margin-bottom:16px;border-bottom:1px solid #30363d}
.tab-btn{background:none;border:none;color:#8b949e;font-family:'Courier New',monospace;
  font-size:0.95em;padding:10px 20px;cursor:pointer;border-bottom:2px solid transparent}
.tab-btn:hover{color:#c9d1d9}
.tab-btn.active{color:#58a6ff;border-bottom-color:#58a6ff}
.classify-panel textarea{width:100%;min-height:160px;background:#161b22;color:#c9d1d9;
  border:1px solid #30363d;border-radius:8px;padding:12px;font-family:'Courier New',monospace;
  font-size:0.9em;resize:vertical}
.classify-panel textarea:focus{outline:none;border-color:#58a6ff}
.classify-btn{background:#161b22;color:#58a6ff;border:1px solid #58a6ff;border-radius:6px;
  padding:10px 24px;font-family:'Courier New',monospace;font-size:0.9em;cursor:pointer;
  margin-top:12px}
.classify-btn:hover{background:#58a6ff;color:#0d1117}
.classify-btn:disabled{opacity:0.5;cursor:not-allowed}
.classify-result{margin-top:16px}
.badge{display:inline-block;padding:4px 12px;border-radius:4px;font-size:0.85em;font-weight:bold;margin-bottom:8px}
.badge.success{background:#1a3a2a;color:#3fb950;border:1px solid #3fb950}
.badge.failure{background:#3a1a1a;color:#f85149;border:1px solid #f85149}
</style>
</head>
<body>
<h1>Trump Social Feed Monitor</h1>
<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('dashboard')">Dashboard</button>
  <button class="tab-btn" onclick="switchTab('classify')">Classify</button>
</div>
<div id="tab-dashboard">
<div class="status-bar">
  <div class="status-indicator"><span class="dot" id="processDot"></span><span id="processText">Process: --</span></div>
  <div class="status-indicator"><span class="dot" id="statusDot"></span><span id="statusText">Loading...</span></div>
</div>
<div class="status-bar">
  <div class="stat"><div class="label">Uptime</div><div class="value" id="uptime">--</div></div>
  <div class="stat"><div class="label">Polls (24h)</div><div class="value" id="pollCount">--</div></div>
  <div class="stat"><div class="label">New Posts (24h)</div><div class="value" id="postsFound">--</div></div>
  <div class="stat"><div class="label">Total Seen (24h)</div><div class="value" id="totalSeen">--</div></div>
  <div class="stat"><div class="label">Notifications (24h)</div><div class="value" id="notifCount">--</div></div>
  <div class="stat"><div class="label">Last Notification</div><div class="value" id="lastNotif">--</div></div>
  <div class="stat"><div class="label">Economic (24h)</div><div class="value" id="economicCount">--</div></div>
  <div class="stat"><div class="label">Avg Confidence</div><div class="value" id="avgConfidence">--</div></div>
  <div class="stat"><div class="label">Fallback (24h)</div><div class="value" id="fallbackCount">--</div></div>
  <div class="stat"><div class="label">Success Rate (24h)</div><div class="value" id="successRate">--</div></div>
</div>
<div id="chartContainer" style="background:#d0d0d0;border:1px solid #b0b0b0;border-radius:8px;padding:16px;margin-bottom:16px">
  <div style="font-size:0.85em;color:#000000;margin-bottom:8px;font-weight:bold">Poll Success Rate (24h)</div>
  <svg id="successChart" width="100%" height="200" viewBox="0 0 960 200"></svg>
</div>
<div class="events" id="eventList"></div>
<div class="refresh-note">Auto-refreshes every 30s</div>
</div>
<div id="tab-classify" style="display:none">
<div class="classify-panel">
  <textarea id="postText" placeholder="Paste a Trump post to classify..." rows="8"></textarea>
  <button class="classify-btn" id="classifyBtn" onclick="classifyPost()">Classify</button>
  <div class="classify-result" id="classifyResult"></div>
</div>
</div>
<script>
function switchTab(name){
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>{if(b.textContent.toLowerCase()===name)b.classList.add('active');});
  document.getElementById('tab-dashboard').style.display=name==='dashboard'?'block':'none';
  document.getElementById('tab-classify').style.display=name==='classify'?'block':'none';
}
async function classifyPost(){
  const text=document.getElementById('postText').value.trim();
  const btn=document.getElementById('classifyBtn');
  const result=document.getElementById('classifyResult');
  if(!text){result.innerHTML='<span class="badge failure">Failure</span><pre>Error: Post text cannot be empty</pre>';return;}
  btn.disabled=true;btn.textContent='Classifying...';result.innerHTML='';
  try{
    const r=await fetch('/api/classify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_text:text})});
    const data=await r.json();
    if(data.status==='success'){
      result.innerHTML='<span class="badge success">Success</span><pre>'+escHtml(JSON.stringify(data.result,null,2))+'</pre>';
    }else{
      result.innerHTML='<span class="badge failure">Failure</span><pre>'+escHtml(data.error)+'</pre>';
    }
  }catch(err){
    result.innerHTML='<span class="badge failure">Failure</span><pre>'+escHtml(String(err))+'</pre>';
  }finally{btn.disabled=false;btn.textContent='Classify';}
}
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
function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function eventSummary(e){
  switch(e.event_type){
    case 'poll_start':return e.url||'';
    case 'poll_end':return 'found:'+e.posts_found+' new:'+e.new_posts+' ('+e.duration_ms+'ms)'+(e.source==='fallback'?' [FALLBACK]':'');
    case 'notification_sent':return (e.topics||[]).join(', ')+' ['+((e.relevance_score||0).toFixed(2))+'] '+(e.post_count?e.post_count+' post(s)':'');
    case 'notification_skipped':return e.reason||'';
    case 'error':return (e.error_type||'')+': '+(e.message||'');
    case 'service_stop':return e.reason||'';
    default:return '';
  }
}
function isExpandable(e){return e.event_type==='notification_sent'||e.event_type==='error';}
function eventDetailPanel(e){
  if(e.event_type==='notification_sent'){
    let html='<h4>Classification</h4>';
    html+='<div class="meta-item">Type: <span>'+(e.is_economic?'Economic':'Non-Economic')+'</span></div>';
    html+='<div class="meta-item">Category: <span>'+escHtml(e.primary_category||'--')+'</span></div>';
    if(e.subcategory){html+='<div class="meta-item">Subcategory: <span>'+escHtml(e.subcategory)+'</span></div>';}
    if(e.market_sentiment){html+='<div class="meta-item">Sentiment: <span>'+escHtml(e.market_sentiment)+'</span></div>';}
    if(typeof e.confidence==='number'){html+='<div class="meta-item">Confidence: <span>'+Math.round(e.confidence*100)+'%</span></div>';}
    html+='<h4>Summary</h4>';
    html+='<p>'+escHtml(typeof e.summary==='string'?e.summary:(e.summary||[]).join('; '))+'</p>';
    if(e.original_posts&&e.original_posts.length>0){
      html+='<h4>Original Posts ('+e.original_posts.length+')</h4>';
      e.original_posts.forEach((p,i)=>{
        html+='<div class="post-block">';
        html+='<div class="meta-item">Platform: <span>'+escHtml(p.platform)+'</span></div>';
        html+='<div class="meta-item">Timestamp: <span>'+escHtml(p.timestamp)+'</span></div>';
        html+='<div class="meta-item">ID: <span>'+escHtml((p.post_id||'').substring(0,16))+'...</span></div>';
        if(p.source_url){html+='<div class="meta-item">URL: <span>'+escHtml(p.source_url)+'</span></div>';}
        html+='<pre>'+escHtml(p.content)+'</pre>';
        html+='</div>';
      });
    }
    if(e.formatted_message){
      html+='<h4>Sent Message</h4><pre>'+escHtml(e.formatted_message)+'</pre>';
    }
    html+='<h4>Metadata</h4>';
    html+='<div class="meta-item">SID: <span>'+escHtml(e.sid||'--')+'</span></div>';
    html+='<div class="meta-item">Relevance: <span>'+((e.relevance_score||0)*100).toFixed(0)+'%</span></div>';
    html+='<div class="meta-item">Topics: <span>'+escHtml((e.topics||[]).join(', '))+'</span></div>';
    return html;
  }
  if(e.event_type==='error'){
    let html='<h4>Error Details</h4>';
    html+='<div class="meta-item">Type: <span style="color:#f85149">'+escHtml(e.error_type||'Unknown')+'</span></div>';
    html+='<div class="meta-item">Message: <span>'+escHtml(e.message||'--')+'</span></div>';
    html+='<div class="meta-item">Source: <span>'+escHtml(e.source||'--')+'</span></div>';
    return html;
  }
  return '';
}
function renderChart(data){
  const svg=document.getElementById('successChart');
  const w=960,h=200,padT=20,padB=20,padL=30,padR=10;
  const chartH=h-padT-padB,barW=Math.floor((w-padL-padR)/24)-2;
  let html='';
  // Y-axis labels and grid
  for(let p of [0,50,100]){
    const y=padT+(100-p)/100*chartH;
    html+=`<text x="${padL-4}" y="${y+4}" text-anchor="end" fill="#000000" font-size="10">${p}%</text>`;
    html+=`<line x1="${padL}" y1="${y}" x2="${w-padR}" y2="${y}" stroke="#21262d" stroke-width="1"/>`;
  }
  data.forEach((d,i)=>{
    const x=padL+i*((w-padL-padR)/24)+1;
    const barH=d.rate!==null?d.rate*chartH:0;
    const y=padT+chartH-barH;
    const color=d.rate===null?'#21262d':d.rate>=0.8?'#3fb950':d.rate>=0.5?'#d29922':'#f85149';
    html+=`<rect x="${x}" y="${y}" width="${barW}" height="${barH}" fill="${color}" rx="2"/>`;
    // Fallback overlay (orange portion within the bar)
    if(d.fallback>0&&d.total>0){
      const fbRatio=d.fallback/d.total;
      const fbH=barH*fbRatio;
      html+=`<rect x="${x}" y="${padT+chartH-fbH}" width="${barW}" height="${fbH}" fill="#d29922" rx="2" opacity="0.8"/>`;
    }
    // Rate value above bar
    if(d.rate!==null){
      html+=`<text x="${x+barW/2}" y="${y+barH/2+4}" text-anchor="middle" fill="#000000" font-size="10" font-weight="bold">${Math.round(d.rate*100)}%</text>`;
    }
    // Hour label on x-axis
    const label=new Date(d.hour).toLocaleTimeString([],{hour:'2-digit',hour12:false});
    html+=`<text x="${x+barW/2}" y="${h-2}" text-anchor="middle" fill="#000000" font-size="12" font-weight="bold">${label}</text>`;
  });
  svg.innerHTML=html;
}
async function refresh(){
  try{
    const [r,sr,pr]=await Promise.all([fetch('/api/events?limit=500'),fetch('/api/status'),fetch('/api/poll-success-rate')]);
    const events=await r.json();
    const status=await sr.json();
    const pollData=await pr.json();
    const pDot=document.getElementById('processDot');
    const pTxt=document.getElementById('processText');
    if(status.running){
      let procMsg='Process: Running (PID '+status.pid+')';
      const starts=events.filter(e=>e.event_type==='service_start');
      if(starts.length>0){const st=new Date(starts[0].timestamp);procMsg+=' | Started: '+st.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}
      pDot.className='dot green';pTxt.textContent=procMsg;
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
        dot.className='dot red';txt.textContent='Stopped';txt.title='Last event was service_stop';
      }else if(now-lastTime>900000){
        dot.className='dot red';txt.textContent='Down';txt.title='No events in the last 15 minutes';
      }else if(errorsLastHour>=3){
        dot.className='dot yellow';txt.textContent='Degraded ('+errorsLastHour+' errors/hr)';txt.title='3+ errors in the last hour';
      }else{
        dot.className='dot green';txt.textContent='Online';txt.title='Service is running normally';
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
    const uniqueNewIds=new Set();recent.filter(e=>e.event_type==='poll_end').forEach(e=>(e.new_post_ids||[]).forEach(id=>uniqueNewIds.add(id)));
    document.getElementById('postsFound').textContent=uniqueNewIds.size;
    document.getElementById('totalSeen').textContent=status.total_seen||0;
    const notifs=recent.filter(e=>e.event_type==='notification_sent');
    document.getElementById('notifCount').textContent=notifs.length;
    // Economic posts and avg confidence (24h)
    const econCount=notifs.filter(e=>e.is_economic===true).length;
    document.getElementById('economicCount').textContent=econCount;
    const confs=notifs.filter(e=>typeof e.confidence==='number').map(e=>e.confidence);
    document.getElementById('avgConfidence').textContent=confs.length>0?Math.round(confs.reduce((a,b)=>a+b,0)/confs.length*100)+'%':'--';
    const allNotifs=events.filter(e=>e.event_type==='notification_sent');
    const lastNotifEl=document.getElementById('lastNotif');
    if(allNotifs.length>0){const lt=new Date(allNotifs[0].timestamp);lastNotifEl.textContent=lt.toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});}else{lastNotifEl.textContent='--';}
    // Fallback count
    const totalFallback=pollData.reduce((a,d)=>a+(d.fallback||0),0);
    document.getElementById('fallbackCount').textContent=totalFallback;
    // Success rate
    const totalSuccess=pollData.reduce((a,d)=>a+d.success,0);
    const totalPolls=pollData.reduce((a,d)=>a+d.total,0);
    const srEl=document.getElementById('successRate');
    srEl.textContent=totalPolls>0?Math.round(totalSuccess/totalPolls*100)+'%':'--';
    renderChart(pollData);
    // Event list grouped by day
    const list=document.getElementById('eventList');
    const sliced=events.slice(0,200);
    const groups={};const groupOrder=[];
    const todayStr=new Date().toLocaleDateString([],{year:'numeric',month:'short',day:'numeric'});
    sliced.forEach(e=>{
      const d=new Date(e.timestamp);
      const dayKey=d.toLocaleDateString([],{year:'numeric',month:'short',day:'numeric'});
      if(!groups[dayKey]){groups[dayKey]=[];groupOrder.push(dayKey);}
      groups[dayKey].push(e);
    });
    let html='';
    groupOrder.forEach(day=>{
      const evts=groups[day];
      const isToday=day===todayStr;
      const label=isToday?day+' (Today)':day;
      html+=`<div class="day-header" onclick="this.nextElementSibling.classList.toggle('collapsed');this.querySelector('.chevron').textContent=this.nextElementSibling.classList.contains('collapsed')?'\\u25b8':'\\u25be'">
        <span><span class="chevron">${isToday?'\\u25be':'\\u25b8'}</span> ${label}</span>
        <span class="count">${evts.length} event${evts.length!==1?'s':''}</span>
      </div>`;
      html+=`<div class="day-events${isToday?'':' collapsed'}">`;
      evts.forEach(e=>{
        const expandable=isExpandable(e);
        const eid='evt-'+Math.random().toString(36).substr(2,9);
        html+=`<div class="event${expandable?' event-expandable':''}"${expandable?` onclick="var d=document.getElementById('${eid}');d.classList.toggle('open');this.querySelector('.event-expand-icon').textContent=d.classList.contains('open')?'\\u25be':'\\u25b8'"`:''}>
          <span class="time">${expandable?'<span class=\\'event-expand-icon\\'>\\u25b8</span>':''}${formatTime(e.timestamp)}</span>
          <span class="type type-${e.event_type}">${e.event_type}</span>
          <span class="details">${eventSummary(e)}</span>
        </div>`;
        if(expandable){html+=`<div class="event-detail" id="${eid}">${eventDetailPanel(e)}</div>`;}
      });
      html+=`</div>`;
    });
    list.innerHTML=html;
  }catch(err){console.error('Refresh failed',err);}
}
refresh();
setInterval(refresh,30000);
</script>
</body>
</html>
"""


def read_all_events() -> list[dict]:
    """Read all events from the JSONL file in chronological order."""
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
    return events


def read_events(limit: int = 200) -> list[dict]:
    """Read events from the JSONL file, return newest first."""
    events = read_all_events()
    events.reverse()
    return events[:limit]


def poll_success_rate() -> list[dict]:
    """Compute hourly poll success rates for the last 24 hours."""
    now = datetime.now(timezone.utc)
    # Start of the current hour
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    # Generate 24 hourly slots (oldest first)
    hours = []
    for i in range(23, -1, -1):
        hours.append(current_hour - timedelta(hours=i))

    # Bucket events
    buckets: dict[str, dict] = {}
    for h in hours:
        key = h.isoformat().replace("+00:00", "Z")
        buckets[key] = {"hour": key, "success": 0, "failed": 0, "fallback": 0}

    cutoff = hours[0]
    for event in read_all_events():
        ts_str = event.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if ts < cutoff:
            continue
        event_type = event.get("event_type")
        if event_type not in ("poll_end", "error"):
            continue
        # Find the bucket
        hour_key = ts.replace(minute=0, second=0, microsecond=0)
        key = hour_key.isoformat().replace("+00:00", "Z")
        if key in buckets:
            if event_type == "poll_end":
                buckets[key]["success"] += 1
                if event.get("source") == "fallback":
                    buckets[key]["fallback"] += 1
            else:
                buckets[key]["failed"] += 1

    result = []
    for h in hours:
        key = h.isoformat().replace("+00:00", "Z")
        b = buckets[key]
        total = b["success"] + b["failed"]
        rate = b["success"] / total if total > 0 else None
        result.append({
            "hour": key,
            "success": b["success"],
            "failed": b["failed"],
            "fallback": b["fallback"],
            "total": total,
            "rate": rate,
        })
    return result


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
            total_seen = 0
            try:
                with open(STATE_FILE) as f:
                    total_seen = len(json.loads(f.read()).get("seen_ids", []))
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            data = {"running": running, "pid": pid, "total_seen": total_seen}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        elif parsed.path == "/api/poll-success-rate":
            data = poll_success_rate()
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

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/classify":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body)
                post_text = payload.get("post_text", "").strip()
                if not post_text:
                    raise ValueError("Post text cannot be empty")
                result = classify(post_text)
                response = {"status": "success", "result": result}
            except Exception as e:
                response = {"status": "failure", "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
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
