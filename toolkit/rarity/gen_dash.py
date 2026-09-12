#!/usr/bin/env python3
"""Generate an interactive the rarity-test collection rarity dashboard (single-file HTML)."""
import json, os

BASE = os.path.expanduser("~/.hermes/rarity/raritytest")
scores = json.load(open(os.path.join(BASE,"scores.json")))
traits = json.load(open(os.path.join(BASE,"traits.json")))
# Token ids you hold (optional) — powers `mine` / the dashboard highlight.
# Provide comma-separated: HELD="12,44,91" python3 <script>.py ...
HELD = [int(x) for x in os.environ.get("HELD", "").split(",") if x.strip()]
OUT = os.environ.get("OUT") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "dashboard_out.html")
N = 5000

held_sorted = sorted(HELD, key=lambda t: scores[str(t)]["rank"])

bins = [0,50,100,200,500,1000,2000,3000,4000,5001]
labels = ["Top 50","51-100","101-200","201-500","501-1k","1k-2k","2k-3k","3k-4k","4k+"]
hist = [0]*len(labels); held_hist=[0]*len(labels)
for t,s in scores.items():
    r=s["rank"]
    for i in range(len(bins)-1):
        if bins[i] <= r < bins[i+1]: hist[i]+=1; break
for t in held_sorted:
    r=scores[str(t)]["rank"]
    for i in range(len(bins)-1):
        if bins[i] <= r < bins[i+1]: held_hist[i]+=1; break

def badge(r):
    cls = "r-top" if r<=50 else ("r-high" if r<=500 else ("r-mid" if r<=2000 else "r-low"))
    return f'<span class="rank-badge {cls}">#{r}</span>'

rows=[]
for t in held_sorted:
    s=scores[str(t)]
    tr=traits.get(str(t),[])
    hl=sorted(s.get("trait_items",[]), key=lambda x:x[2])[:3]
    tags=" ".join(f'<span class="tag">{a}: {v}</span>' for a,v,c,_ in hl)
    rows.append(f'<tr><td class="tok">#{t}</td><td>{badge(s["rank"])}</td><td>top {s["pct"]:.1f}%</td><td>{s["score"]:.0f}</td><td>{tags}</td></tr>')

bars=[]
mxh=max(held_hist) if max(held_hist)>0 else 1
for lab,ac,hc in zip(labels,hist,held_hist):
    aw=ac/N*100
    hw=(hc/mxh*100) if hc>0 else 0
    bars.append(f'<div class="b-row"><div class="b-label">{lab}</div><div class="b-track"><div class="b-all" style="width:{aw:.1f}%"></div><div class="b-held" style="width:{hw:.0f}%"></div></div><div class="b-nums">{ac} total · {hc} yours</div></div>')

if not held_sorted:
    raise SystemExit('No HELD token ids given. Usage: HELD="12,44,91" python3 gen_dash.py')
best=held_sorted[0]
best_rank=scores[str(best)]["rank"]
avg=sum(scores[str(t)]["rank"] for t in held_sorted)/len(held_sorted)
mythic=sum(1 for t in scores if any(it.get("value")=="1/1" for it in traits.get(str(t),[])))

bars_html="\n".join(bars)
rows_html="\n".join(rows)

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>the rarity-test collection Rarity — Your Holdings</title>
<style>
:root{{--bg:#0d0f14;--card:#161a22;--line:#232a36;--txt:#e8ecf3;--mut:#9aa6b8;--accent:#7c5cff;--gold:#f5b942}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:24px;max-width:1100px;margin:0 auto}}
h1{{font-size:26px;margin-bottom:4px}} h2{{font-size:18px;margin:28px 0 12px}}
.sub{{color:var(--mut);font-size:14px;margin-bottom:20px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}}
.card .k{{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}}
.card .v{{font-size:22px;font-weight:700}} .card .v.gold{{color:var(--gold)}}
.bar-wrap{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px}}
.b-row{{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px}}
.b-label{{width:100px;color:var(--mut);text-align:right;flex-shrink:0}}
.b-track{{flex:1;background:var(--line);height:18px;border-radius:4px;overflow:hidden;position:relative}}
.b-all{{position:absolute;top:0;bottom:0;left:0;background:#2a3242}}
.b-held{{position:absolute;top:0;bottom:0;left:0;background:var(--accent);opacity:.95}}
.b-nums{{width:120px;color:var(--mut);font-size:12px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
th,td{{padding:10px 12px;text-align:left;font-size:13px;border-bottom:1px solid var(--line)}}
th{{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.3px}}
tr:last-child td{{border-bottom:none}} .tok{{font-weight:700}}
.rank-badge{{display:inline-block;min-width:52px;text-align:center;padding:2px 8px;border-radius:20px;font-weight:700;font-size:12px}}
.r-top{{background:#7c2d12;color:#fdba74}}.r-high{{background:#1e3a2f;color:#6ee7b7}}
.r-mid{{background:#3b2f0f;color:#fcd34d}}.r-low{{background:#1f2430;color:#94a3b8}}
.tag{{display:inline-block;padding:2px 7px;border-radius:5px;background:var(--line);color:var(--mut);font-size:11px;margin:1px 2px}}
.legend{{color:var(--mut);font-size:12px;margin-top:8px}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:2px;vertical-align:middle;margin:0 4px 0 8px}}
</style></head><body>
<h1>the rarity-test collection (raritytest-888) Rarity</h1>
<div class="sub">Robinhood Chain · ERC721 · 5,000 supply · Traits revealed · Mint wallet 0x1111…1111</div>
<div class="cards">
  <div class="card"><div class="k">Your Tokens</div><div class="v">29</div></div>
  <div class="card"><div class="k">Best Rank</div><div class="v gold">#{best_rank}</div></div>
  <div class="card"><div class="k">Rarest Token</div><div class="v">ID {best}</div></div>
  <div class="card"><div class="k">Avg Rank</div><div class="v">{avg:.0f}</div></div>
  <div class="card"><div class="k">1/1 Mythics</div><div class="v gold">{mythic} total</div></div>
</div>
<h2>Rarity distribution — your 29 vs the full 5,000</h2>
<div class="bar-wrap">
{bars_html}
<div class="legend"><span class="dot" style="background:#2a3242"></span>all 5,000&nbsp;<span class="dot" style="background:var(--accent)"></span>your 29 holdings</div>
</div>
<h2>Your 29 holdings, rarest first</h2>
<table><tr><th>Token</th><th>Rank</th><th>Percentile</th><th>Rarity score</th><th>Rarest traits</th></tr>
{rows_html}
</table>
<div class="sub" style="margin-top:16px">Rarity = trait-frequency statistical score (rarity.tools method), computed from the same revealed metadata before OpenSea's rarity ranking populated. Lower rank = rarer token.</div>
</body></html>"""
open(OUT,"w").write(html)
print("Wrote", OUT, len(html), "bytes")

