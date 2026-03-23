"""
CyberFeed v14 — Clean feed, no reader feature.
Full HTML iframe UI for best appearance.
"""

import streamlit as st
import feedparser
import requests
from datetime import datetime, timezone
import re
import concurrent.futures
import json

st.set_page_config(
    page_title="CyberFeed",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body,.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"]>.main,
section[data-testid="stMain"],
section[data-testid="stMain"]>div,
[data-testid="block-container"],
.main .block-container{
  background:#070A12!important;
  padding:0!important;margin:0!important;
  max-width:100%!important;
}
header[data-testid="stHeader"],
[data-testid="stSidebar"],
#MainMenu,.stDeployButton,footer,
.stStatusWidget,[data-testid="stToolbar"]{display:none!important;}
[data-testid="stVerticalBlock"]{gap:0!important;}
iframe{border:none!important;display:block!important;width:100%!important;}
</style>
""", unsafe_allow_html=True)

# ── FEEDS ─────────────────────────────────────────────────────────────────────
FEEDS = [
    dict(name="The Hacker News",     url="https://feeds.feedburner.com/TheHackersNews",                  cat="Threats",         color="#FF4B6E", icon="📡"),
    dict(name="BleepingComputer",     url="https://www.bleepingcomputer.com/feed/",                       cat="Breaches",        color="#FF8C00", icon="💻"),
    dict(name="Krebs on Security",    url="https://krebsonsecurity.com/feed/",                            cat="Breaches",        color="#9B59B6", icon="🔍"),
    dict(name="Dark Reading",         url="https://www.darkreading.com/rss.xml",                          cat="Threats",         color="#E74C3C", icon="🌑"),
    dict(name="SecurityWeek",         url="https://feeds.feedburner.com/securityweek",                    cat="Threats",         color="#1ABC9C", icon="🗞️"),
    dict(name="SANS ISC",             url="https://isc.sans.edu/rssfeed_full.xml",                        cat="Vulnerabilities",  color="#F39C12", icon="📊"),
    dict(name="Schneier on Security", url="https://www.schneier.com/feed/atom/",                          cat="Analysis",        color="#3498DB", icon="🧠"),
    dict(name="Unit 42",              url="https://unit42.paloaltonetworks.com/feed/",                    cat="Analysis",        color="#27AE60", icon="🔬"),
    dict(name="Google Project Zero",  url="https://googleprojectzero.blogspot.com/feeds/posts/default",   cat="Vulnerabilities",  color="#4285F4", icon="⓪"),
    dict(name="Malwarebytes Labs",     url="https://www.malwarebytes.com/blog/feed/",                      cat="Threats",         color="#D35400", icon="🦠"),
    dict(name="WeLiveSecurity",       url="https://www.welivesecurity.com/feed/",                         cat="Analysis",        color="#16A085", icon="🛡️"),
    dict(name="NIST NVD",             url="https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss-analyzed.xml", cat="CVE",             color="#C0392B", icon="📋"),
    dict(name="Exploit-DB",           url="https://www.exploit-db.com/rss.xml",                           cat="CVE",             color="#922B21", icon="💥"),
    dict(name="Troy Hunt",            url="https://www.troyhunt.com/rss/",                                cat="Breaches",        color="#E91E63", icon="🔓"),
    dict(name="Graham Cluley",        url="https://grahamcluley.com/feed/",                               cat="Breaches",        color="#607D8B", icon="📰"),
    dict(name="Recorded Future",      url="https://www.recordedfuture.com/feed",                          cat="Analysis",        color="#8E44AD", icon="🎯"),
    dict(name="Threatpost",           url="https://threatpost.com/feed/",                                 cat="Threats",         color="#E67E22", icon="⚠️"),
    dict(name="HackerOne",            url="https://hackerone.com/hacktivity.rss",                         cat="CVE",             color="#FF6B35", icon="🏆"),
]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def parse_date(entry):
    for a in ("published_parsed","updated_parsed","created_parsed"):
        v = getattr(entry, a, None)
        if v:
            try: return datetime(*v[:6], tzinfo=timezone.utc)
            except: pass
    return datetime(2000,1,1,tzinfo=timezone.utc)

def time_ago(dt):
    s = max(0,int((datetime.now(timezone.utc)-dt).total_seconds()))
    if s<60:    return f"{s}s ago"
    if s<3600:  return f"{s//60}m ago"
    if s<86400: return f"{s//3600}h ago"
    d=s//86400
    return f"{d}d ago" if d<30 else dt.strftime("%b %d")

def clean(txt):
    txt=re.sub(r'<[^>]+',' ',txt or ''); txt=re.sub(r'\s+',' ',txt).strip()
    return txt[:260]+"…" if len(txt)>260 else txt

def fetch_one(feed):
    try:
        r=requests.get(feed["url"],timeout=8,headers={"User-Agent":"CyberFeed/14.0"})
        r.raise_for_status()
        parsed=feedparser.parse(r.text)
        out=[]
        for e in parsed.entries[:20]:
            dt=parse_date(e)
            out.append(dict(
                title=(e.get("title") or "Untitled").strip(),
                url=e.get("link","#"),
                summary=clean(e.get("summary") or e.get("description") or ""),
                src=feed["name"],cat=feed["cat"],color=feed["color"],icon=feed["icon"],
                ts=int(dt.timestamp()),ago=time_ago(dt),
                fresh=(datetime.now(timezone.utc)-dt).total_seconds()<14400,
            ))
        return out,None
    except Exception as ex:
        return [],f"{feed['name']}: {str(ex)[:60]}"

@st.cache_data(ttl=300,show_spinner=False)
def fetch_all():
    arts,errs=[],[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futs={pool.submit(fetch_one,f):f["name"] for f in FEEDS}
        done,pending=concurrent.futures.wait(futs,timeout=20)
        for f in done:
            items,err=f.result(); arts.extend(items)
            if err: errs.append(err)
        for f in pending:
            errs.append(f"{futs[f]}: timeout"); f.cancel()
    arts.sort(key=lambda x:x["ts"],reverse=True)
    return arts,errs

with st.spinner("Fetching security feeds…"):
    articles, errors = fetch_all()

import streamlit.components.v1 as components

now_str       = datetime.now().strftime("%d %b %Y %H:%M")
articles_json = json.dumps(articles)
errors_json   = json.dumps(errors)
feed_count    = len(FEEDS)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}

:root{{
  --bg:#070A12;--sf:#0D1220;--sf2:#111827;--sf3:#0A0F1E;
  --bd:rgba(255,255,255,0.07);--bdh:rgba(0,194,255,0.4);
  --tx:#D0DCF0;--dim:rgba(208,220,240,0.5);--fnt:rgba(208,220,240,0.28);
  --ac:#00C2FF;--gw:rgba(0,194,255,0.13);
}}
body.obsidian{{--bg:#0A0A0A;--sf:#141414;--sf2:#1C1C1C;--sf3:#111;--bdh:rgba(160,120,255,.4);--tx:#E0D8FF;--dim:rgba(224,216,255,.5);--fnt:rgba(224,216,255,.25);--ac:#A078FF;--gw:rgba(160,120,255,.13);}}
body.terminal{{--bg:#010B01;--sf:#051505;--sf2:#081A08;--sf3:#030D03;--bd:rgba(0,255,65,.1);--bdh:rgba(0,255,65,.4);--tx:#B0FFB8;--dim:rgba(176,255,184,.5);--fnt:rgba(176,255,184,.25);--ac:#00FF41;--gw:rgba(0,255,65,.1);}}
body.crimson{{--bg:#0C0608;--sf:#180B0E;--sf2:#200E12;--sf3:#0E0709;--bdh:rgba(255,60,80,.4);--tx:#FFD0D8;--dim:rgba(255,208,216,.5);--fnt:rgba(255,208,216,.25);--ac:#FF3C50;--gw:rgba(255,60,80,.13);}}
body.arctic{{--bg:#EEF2FA;--sf:#FFF;--sf2:#F5F8FF;--sf3:#E8EEF8;--bd:rgba(0,0,0,.08);--bdh:rgba(0,100,255,.4);--tx:#1A2540;--dim:rgba(26,37,64,.55);--fnt:rgba(26,37,64,.32);--ac:#0064FF;--gw:rgba(0,100,255,.1);}}

body{{
  font-family:'Inter',sans-serif;
  background:var(--bg);color:var(--tx);
  width:100vw;height:100vh;
  display:flex;flex-direction:column;
  overflow:hidden;
}}

/* NAVBAR */
.nav{{
  flex-shrink:0;background:var(--sf);
  border-bottom:1px solid var(--bd);
  height:46px;display:flex;align-items:center;
  padding:0 18px;box-shadow:0 1px 20px rgba(0,0,0,.4);
}}
.logo{{
  font-family:'JetBrains Mono',monospace;font-size:13px;
  font-weight:700;letter-spacing:2px;color:var(--ac);
  display:flex;align-items:center;gap:8px;
  user-select:none;flex-shrink:0;
}}
.dot{{
  width:7px;height:7px;border-radius:50%;
  background:var(--ac);box-shadow:0 0 8px var(--ac);
  animation:blink 2s ease-in-out infinite;
}}
@keyframes blink{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.2;transform:scale(.55)}}}}
.stats{{display:flex;align-items:center;margin-left:18px;flex:1;overflow:hidden;}}
.stat{{display:flex;align-items:baseline;gap:4px;padding:0 11px;border-right:1px solid var(--bd);flex-shrink:0;}}
.sn{{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;color:var(--ac);}}
.sl{{font-family:'Inter',sans-serif;font-size:9px;font-weight:500;color:var(--fnt);text-transform:uppercase;letter-spacing:1px;white-space:nowrap;}}
.c-r{{color:#FF4B6E!important}}.c-a{{color:#FF8C00!important}}.c-g{{color:#00D68F!important}}.c-p{{color:#A78BFA!important}}
.nav-time{{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--fnt);flex-shrink:0;}}

/* TICKER */
.ticker{{
  flex-shrink:0;background:var(--sf3);
  border-bottom:1px solid var(--bd);
  height:26px;display:flex;align-items:center;overflow:hidden;
}}
.t-lbl{{font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;color:var(--ac);letter-spacing:2px;padding:0 11px;flex-shrink:0;border-right:1px solid var(--bd);white-space:nowrap;}}
.t-track{{flex:1;overflow:hidden;}}
.t-inner{{display:inline-block;white-space:nowrap;animation:ticker 100s linear infinite;}}
.t-inner:hover{{animation-play-state:paused;}}
@keyframes ticker{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
.t-item{{font-family:'Inter',sans-serif;font-size:11px;color:var(--dim);margin-right:32px;display:inline;}}
.t-sep{{color:var(--ac);opacity:.2;margin-right:32px;display:inline;}}

/* TOOLBAR */
.toolbar{{
  flex-shrink:0;background:var(--sf2);
  border-bottom:1px solid var(--bd);
  padding:7px 18px;display:flex;align-items:center;gap:8px;
}}
.sw{{flex:1;min-width:0;position:relative;}}
.sw svg{{position:absolute;left:10px;top:50%;transform:translateY(-50%);opacity:.3;pointer-events:none;}}
#si{{
  width:100%;background:var(--sf);border:1px solid var(--bd);border-radius:7px;
  color:var(--tx);font-family:'Inter',sans-serif;font-size:12px;
  padding:7px 10px 7px 32px;height:34px;outline:none;
  transition:border-color .18s,box-shadow .18s;
}}
#si:focus{{border-color:var(--bdh);box-shadow:0 0 0 2px var(--gw);}}
#si::placeholder{{color:var(--fnt);}}
select{{
  background:var(--sf);border:1px solid var(--bd);border-radius:7px;
  color:var(--tx);font-family:'Inter',sans-serif;font-size:11px;
  padding:0 26px 0 10px;height:34px;outline:none;cursor:pointer;
  -webkit-appearance:none;appearance:none;flex-shrink:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='5'%3E%3Cpath d='M0 0l4 5 4-5z' fill='%23666'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 8px center;
  transition:border-color .18s;
}}
select:focus{{border-color:var(--bdh);}}
#cs{{width:130px;}}#th{{width:128px;}}
.btn{{
  background:var(--gw);border:1px solid var(--bdh);border-radius:7px;
  color:var(--ac);font-family:'JetBrains Mono',monospace;
  font-size:10px;font-weight:700;height:34px;padding:0 13px;
  cursor:pointer;transition:all .18s;flex-shrink:0;white-space:nowrap;
}}
.btn:hover{{background:var(--ac);color:var(--bg);box-shadow:0 0 14px var(--gw);}}

/* TABS */
.tabs{{
  flex-shrink:0;background:var(--sf);
  border-bottom:1px solid var(--bd);
  padding:0 18px;display:flex;overflow-x:auto;
}}
.tabs::-webkit-scrollbar{{height:2px;}}
.tab{{
  font-family:'Inter',sans-serif;font-size:11px;font-weight:500;
  padding:9px 14px 7px;color:var(--fnt);
  border-bottom:2px solid transparent;cursor:pointer;
  white-space:nowrap;transition:all .18s;
}}
.tab:hover{{color:var(--dim);background:var(--gw);}}.tab.on{{color:var(--ac);border-bottom-color:var(--ac);background:var(--gw);}}
.tab-n{{font-family:'JetBrains Mono',monospace;font-size:8px;opacity:.35;margin-left:3px;}}

/* SOURCE BAR */
.src-bar{{
  flex-shrink:0;background:var(--bg);
  border-bottom:1px solid var(--bd);
  padding:5px 18px;display:flex;align-items:center;
  gap:5px;overflow-x:auto;white-space:nowrap;
}}
.src-bar::-webkit-scrollbar{{height:2px;}}.src-bar::-webkit-scrollbar-thumb{{background:var(--bdh);}}
.src-lbl{{font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--fnt);letter-spacing:1.5px;text-transform:uppercase;flex-shrink:0;}}
.pill{{font-family:'Inter',sans-serif;font-size:10px;padding:2px 8px;border-radius:20px;border:1px solid var(--bd);color:var(--dim);cursor:pointer;transition:all .18s;flex-shrink:0;}}
.pill:hover{{border-color:var(--bdh);color:var(--tx);}}.pill.on{{border-color:var(--bdh);background:var(--gw);color:var(--ac);}}

/* MAIN */
.main{{flex:1;overflow-y:auto;overflow-x:hidden;padding:12px 18px 20px;}}
.main::-webkit-scrollbar{{width:4px;}}.main::-webkit-scrollbar-thumb{{background:var(--bdh);border-radius:2px;}}
.feed-hdr{{display:flex;align-items:center;margin-bottom:10px;}}
.feed-lbl{{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--fnt);text-transform:uppercase;letter-spacing:2px;display:flex;align-items:center;gap:10px;flex:1;}}
.feed-lbl::after{{content:'';flex:1;height:1px;background:var(--bd);min-width:20px;}}

/* PAGINATION — bottom bar */
.pag-footer{{
  display:flex;align-items:center;justify-content:center;
  gap:4px;padding:16px 0 4px;
}}
.pg-b{{
  font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:600;
  width:28px;height:28px;border-radius:6px;
  border:1px solid var(--bd);background:var(--sf);
  color:var(--dim);cursor:pointer;transition:all .18s;
  display:flex;align-items:center;justify-content:center;
}}
.pg-b:hover:not([disabled]){{border-color:var(--bdh);color:var(--ac);background:var(--gw);}}
.pg-b.on{{border-color:var(--bdh);background:var(--gw);color:var(--ac);}}
.pg-b[disabled]{{opacity:.2;cursor:default;}}
.pg-i{{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--fnt);padding:0 3px;}}

/* GRID */
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}}
@media(max-width:1100px){{.grid{{grid-template-columns:repeat(2,1fr);}}}}
@media(max-width:680px){{.grid{{grid-template-columns:1fr;}}}}

/* CARD */
.card{{
  background:var(--sf);border:1px solid var(--bd);
  border-left:3px solid var(--cc,var(--ac));
  border-radius:9px;padding:14px 15px 13px;
  transition:transform .2s,border-color .2s,box-shadow .2s;
}}
.card:hover{{transform:translateY(-2px);box-shadow:0 8px 28px rgba(0,0,0,.45);border-color:var(--bdh);}}
.c-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px;}}
.badge{{font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:600;padding:2px 8px;border-radius:20px;border:1px solid;white-space:nowrap;flex-shrink:0;}}
.c-ago{{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--fnt);white-space:nowrap;padding-top:2px;}}
.c-title{{
  font-family:'Inter',sans-serif;font-size:13px;font-weight:600;
  color:var(--tx);line-height:1.5;margin-bottom:7px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}}
.new-b{{
  display:inline-block;font-family:'JetBrains Mono',monospace;font-size:7px;
  font-weight:700;letter-spacing:1px;color:#fff;background:#FF3C50;
  padding:2px 5px;border-radius:3px;margin-left:5px;vertical-align:middle;
  animation:nb 1.6s ease-in-out infinite;
}}
@keyframes nb{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.c-sum{{
  font-family:'Inter',sans-serif;font-size:11px;color:var(--dim);
  line-height:1.6;margin-bottom:11px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}}
.c-foot{{display:flex;justify-content:space-between;align-items:center;gap:6px;}}
.cat-p{{font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;padding:2px 7px;border-radius:4px;}}
.open-btn{{
  font-family:'Inter',sans-serif;font-size:10px;font-weight:500;
  color:var(--ac);text-decoration:none;padding:4px 11px;
  border:1px solid var(--bdh);border-radius:5px;background:var(--gw);
  transition:all .15s;
}}
.open-btn:hover{{background:var(--ac);color:var(--bg);}}

/* ERROR PANEL */
.err-panel{{background:rgba(255,75,110,.05);border:1px solid rgba(255,75,110,.18);border-radius:7px;overflow:hidden;margin-bottom:10px;}}
.err-hdr{{font-family:'JetBrains Mono',monospace;font-size:10px;color:#FF4B6E;padding:7px 11px;cursor:pointer;user-select:none;display:flex;align-items:center;gap:8px;}}
.err-body{{padding:0 11px 7px;display:none;}}.err-body.open{{display:block;}}
.err-line{{font-family:'JetBrains Mono',monospace;font-size:9px;color:#FF4B6E;opacity:.7;padding:2px 0;}}

.empty{{grid-column:1/-1;text-align:center;padding:60px 20px;font-family:'JetBrains Mono',monospace;color:var(--fnt);font-size:11px;}}

::-webkit-scrollbar{{width:4px;height:4px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{background:var(--bdh);border-radius:2px;}}
</style>
</head>
<body>

<!-- NAVBAR -->
<nav class="nav">
  <div class="logo"><div class="dot"></div>CYBERFEED</div>
  <div class="stats" id="stats"></div>
  <div class="nav-time" id="navTime">{now_str}</div>
</nav>

<!-- TICKER -->
<div class="ticker">
  <div class="t-lbl">LIVE</div>
  <div class="t-track"><div class="t-inner" id="tInner"></div></div>
</div>

<!-- TOOLBAR -->
<div class="toolbar">
  <div class="sw">
    <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
    <input id="si" type="text" placeholder="Search headlines, CVEs, threat actors, APTs…" autocomplete="off">
  </div>
  <select id="cs">
    <option value="All">All Categories</option>
    <option value="Threats">Threats</option>
    <option value="Vulnerabilities">Vulnerabilities</option>
    <option value="Breaches">Breaches</option>
    <option value="CVE">CVE</option>
    <option value="Analysis">Analysis</option>
  </select>
  <select id="th">
    <option value="">⬤ Midnight</option>
    <option value="obsidian">⬤ Obsidian</option>
    <option value="terminal">⬤ Terminal</option>
    <option value="crimson">⬤ Crimson</option>
    <option value="arctic">⬤ Arctic</option>
  </select>
  <button class="btn" onclick="location.reload()">↻ REFRESH</button>
</div>

<!-- TABS -->
<div class="tabs" id="tabs"></div>

<!-- SOURCE BAR -->
<div class="src-bar" id="srcBar"><span class="src-lbl">Sources</span></div>

<!-- MAIN -->
<div class="main" id="mainArea">
  <div id="errPanel"></div>
  <div class="feed-hdr">
    <div class="feed-lbl" id="feedLbl">Loading…</div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="pag-footer" id="pag"></div>
</div>

<script>
const ALL   = {articles_json};
const ERRS  = {errors_json};
const FCNT  = {feed_count};
const PER   = 15;

const CAT_COLORS={{Threats:'#FF4B6E',Vulnerabilities:'#00C2FF',Breaches:'#FF8C00',CVE:'#E74C3C',Analysis:'#A78BFA'}};
const CAT_ICO={{Threats:'🔴',CVE:'🟠',Breaches:'🟡',Vulnerabilities:'🔵',Analysis:'🟣'}};
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

const S={{search:'',cat:'All',srcs:new Set(),page:0}};

function filtered(){{
  let a=ALL;
  if(S.cat!=='All')a=a.filter(x=>x.cat===S.cat);
  if(S.srcs.size)a=a.filter(x=>S.srcs.has(x.src));
  if(S.search.length>=2){{
    const q=S.search.toLowerCase();
    a=a.filter(x=>x.title.toLowerCase().includes(q)||x.summary.toLowerCase().includes(q));
  }}
  return a;
}}

function renderStats(){{
  const cc={{}};ALL.forEach(a=>cc[a.cat]=(cc[a.cat]||0)+1);
  const fn=ALL.filter(a=>a.fresh).length;
  document.getElementById('stats').innerHTML=`
    <div class="stat"><span class="sn">${{ALL.length}}</span><span class="sl">Articles</span></div>
    <div class="stat"><span class="sn c-g">${{FCNT-ERRS.length}}/${{FCNT}}</span><span class="sl">Feeds</span></div>
    <div class="stat"><span class="sn c-r">${{fn}}</span><span class="sl">New 4h</span></div>
    <div class="stat"><span class="sn c-r">${{cc.Threats||0}}</span><span class="sl">Threats</span></div>
    <div class="stat"><span class="sn">${{cc.Vulnerabilities||0}}</span><span class="sl">Vulns</span></div>
    <div class="stat"><span class="sn c-r">${{cc.CVE||0}}</span><span class="sl">CVE</span></div>
    <div class="stat"><span class="sn c-a">${{cc.Breaches||0}}</span><span class="sl">Breaches</span></div>
    <div class="stat"><span class="sn c-p">${{cc.Analysis||0}}</span><span class="sl">Analysis</span></div>`;
}}

function renderTicker(){{
  const items=ALL.slice(0,24).map(a=>{{
    const t=a.title.length>70?a.title.slice(0,70)+'…':a.title;
    return `<span class="t-item">${{CAT_ICO[a.cat]||'⚪'}} ${{esc(t)}}</span><span class="t-sep">·</span>`;
  }}).join('');
  document.getElementById('tInner').innerHTML=items+items;
}}

function renderErrors(){{
  const el=document.getElementById('errPanel');
  if(!ERRS.length){{el.innerHTML='';return;}}
  el.innerHTML=`<div class="err-panel">
    <div class="err-hdr" onclick="this.nextElementSibling.classList.toggle('open')">
      ⚠ ${{ERRS.length}} feed(s) had errors
      <span style="margin-left:auto;opacity:.5">▾</span>
    </div>
    <div class="err-body">
      ${{ERRS.map(e=>`<div class="err-line">✗ ${{esc(e)}}</div>`).join('')}}
    </div>
  </div>`;
}}

function renderTabs(){{
  const CATS=['All','Threats','Vulnerabilities','Breaches','CVE','Analysis'];
  const cc={{}};ALL.forEach(a=>cc[a.cat]=(cc[a.cat]||0)+1);
  document.getElementById('tabs').innerHTML=CATS.map(c=>
    `<div class="tab ${{S.cat===c?'on':''}}" onclick="setCat('${{c}}')">
      ${{c}}<span class="tab-n">(${{c==='All'?ALL.length:cc[c]||0}})</span>
    </div>`).join('');
}}

function renderSrcBar(){{
  const srcs=[...new Set(ALL.map(a=>a.src))].sort();
  document.getElementById('srcBar').innerHTML='<span class="src-lbl">Sources</span>'+
    srcs.map(s=>`<span class="pill ${{S.srcs.has(s)?'on':''}}" onclick="toggleSrc('${{esc(s)}}')">${{esc(s)}}</span>`).join('');
}}

function cardHTML(a){{
  const c=a.color,cc=CAT_COLORS[a.cat]||'#888';
  const nb=a.fresh?'<span class="new-b">NEW</span>':'';
  return `<div class="card" style="--cc:${{c}}">
  <div class="c-top">
    <div class="badge" style="color:${{c}};border-color:${{c}}44;background:${{c}}14">
      ${{a.icon}} ${{esc(a.src)}}
    </div>
    <div class="c-ago">${{esc(a.ago)}}</div>
  </div>
  <div class="c-title">${{esc(a.title)}}${{nb}}</div>
  <div class="c-sum">${{esc(a.summary)||'No summary.'}}</div>
  <div class="c-foot">
    <span class="cat-p" style="color:${{cc}};background:${{cc}}18">${{a.cat}}</span>
    <a class="open-btn" href="${{esc(a.url)}}" target="_blank" rel="noopener">↗ Open</a>
  </div>
</div>`;
}}

function renderPag(total){{
  const pages=Math.ceil(total/PER);
  const el=document.getElementById('pag');
  if(pages<=1){{el.innerHTML='';return;}}
  let h=`<button class="pg-b" onclick="goPage(${{S.page-1}})" ${{S.page===0?'disabled':''}}>‹</button>`;
  const range=[];
  for(let i=0;i<pages;i++){{
    if(i===0||i===pages-1||Math.abs(i-S.page)<=1)range.push(i);
    else if(range[range.length-1]!=='…')range.push('…');
  }}
  range.forEach(i=>{{
    if(i==='…')h+=`<span class="pg-i">…</span>`;
    else h+=`<button class="pg-b ${{i===S.page?'on':''}}" onclick="goPage(${{i}})">${{i+1}}</button>`;
  }});
  h+=`<button class="pg-b" onclick="goPage(${{S.page+1}})" ${{S.page===pages-1?'disabled':''}}>›</button>`;
  h+=`<span class="pg-i">${{S.page+1}}/${{pages}}</span>`;
  el.innerHTML=h;
}}

function renderGrid(){{
  const arts=filtered();
  let lbl=`${{arts.length}} articles`;
  if(S.search)lbl+=` · "${{esc(S.search)}}"`;
  if(S.cat!=='All')lbl+=` · ${{S.cat}}`;
  if(S.srcs.size)lbl+=` · ${{S.srcs.size}} source(s)`;
  document.getElementById('feedLbl').textContent=lbl;
  renderPag(arts.length);
  const page=arts.slice(S.page*PER,(S.page+1)*PER);
  if(!page.length){{
    document.getElementById('grid').innerHTML='<div class="empty">📡<br><br>No articles match your filters.</div>';
    return;
  }}
  document.getElementById('grid').innerHTML=page.map(cardHTML).join('');
}}

function setCat(c){{S.cat=c;S.page=0;renderTabs();renderGrid();}}
function goPage(p){{
  const arts=filtered();
  S.page=Math.max(0,Math.min(p,Math.ceil(arts.length/PER)-1));
  renderGrid();
  document.getElementById('mainArea').scrollTop=0;
}}
function toggleSrc(s){{
  S.srcs.has(s)?S.srcs.delete(s):S.srcs.add(s);
  S.page=0;renderSrcBar();renderGrid();
}}

document.getElementById('th').addEventListener('change',function(){{
  document.body.className=this.value;
}});
let q_t;
document.getElementById('si').addEventListener('input',function(){{
  clearTimeout(q_t);
  q_t=setTimeout(()=>{{S.search=this.value;S.page=0;renderGrid();}},200);
}});
document.getElementById('cs').addEventListener('change',function(){{
  S.cat=this.value;S.page=0;renderTabs();renderGrid();
}});
setInterval(()=>{{
  const n=new Date();
  document.getElementById('navTime').textContent=
    n.toLocaleDateString('en-GB',{{day:'2-digit',month:'short',year:'numeric'}})+' '+
    n.toLocaleTimeString('en-GB',{{hour:'2-digit',minute:'2-digit'}});
}},15000);

renderStats();renderTicker();renderErrors();renderTabs();renderSrcBar();renderGrid();
</script>
</body>
</html>"""

components.html(HTML, height=900, scrolling=False)
