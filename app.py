from datetime import date
from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expenses_v2.db"
db = SQLAlchemy(app)


# ---------- DATABASE MODEL (table ka structure) ----------
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), default="Other")
    spent_on = db.Column(db.Date, default=date.today)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "amount": self.amount,
                "category": self.category, "date": self.spent_on.isoformat()}


with app.app_context():
    db.create_all()


# ---------- REST APIs ----------
@app.get("/api/expenses")
def list_expenses():
    rows = Expense.query.order_by(Expense.spent_on.desc(), Expense.id.desc())
    return jsonify([e.to_dict() for e in rows])


@app.post("/api/expenses")
def add_expense():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        amount = 0
    if not title or amount <= 0:
        return jsonify({"error": "Title and a positive amount are required"}), 400
    try:
        spent_on = date.fromisoformat(data.get("date")) if data.get("date") else date.today()
    except ValueError:
        return jsonify({"error": "Invalid date"}), 400
    e = Expense(title=title, amount=amount,
                category=data.get("category") or "Other", spent_on=spent_on)
    db.session.add(e)
    db.session.commit()
    return jsonify(e.to_dict()), 201


@app.delete("/api/expenses/<int:eid>")
def delete_expense(eid):
    e = db.get_or_404(Expense, eid)
    db.session.delete(e)
    db.session.commit()
    return jsonify({"deleted": eid})


@app.get("/api/summary")
def summary():
    today = date.today()
    all_rows = Expense.query.all()
    month_total = sum(e.amount for e in all_rows
                      if e.spent_on.year == today.year and e.spent_on.month == today.month)
    by_cat = db.session.query(Expense.category, func.sum(Expense.amount)) \
        .group_by(Expense.category).all()
    return jsonify({
        "total": round(sum(e.amount for e in all_rows), 2),
        "month_total": round(month_total, 2),
        "count": len(all_rows),
        "by_category": {c: round(t, 2) for c, t in by_cat},
    })


# ---------- FRONTEND ----------
PAGE = """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PaisaTrack - Expense Tracker</title>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#6a11cb">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="PaisaTrack">
<link rel="apple-touch-icon" href="/icon-192.png">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
 *{box-sizing:border-box}
 body{margin:0;font-family:'Segoe UI',Arial,sans-serif;color:#1f2540;
  background:linear-gradient(135deg,#6a11cb 0%,#2575fc 100%);min-height:100vh;padding:24px 14px}
 .wrap{max-width:980px;margin:auto}
 h1{color:#fff;margin:0 0 4px;font-size:2rem}
 .sub{color:#e3e9ff;margin:0 0 22px}
 .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:18px}
 .stat{border-radius:16px;padding:18px;color:#fff;box-shadow:0 8px 20px rgba(0,0,0,.18)}
 .stat small{opacity:.9;font-size:.85rem}
 .stat b{display:block;font-size:1.7rem;margin-top:4px}
 .s1{background:linear-gradient(135deg,#ff512f,#f09819)}
 .s2{background:linear-gradient(135deg,#11998e,#38ef7d)}
 .s3{background:linear-gradient(135deg,#ec008c,#fc6767)}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
 @media(max-width:760px){.grid{grid-template-columns:1fr}}
 .card{background:#fff;border-radius:18px;padding:20px;box-shadow:0 8px 24px rgba(0,0,0,.15)}
 .card h3{margin:0 0 12px}
 input,select{width:100%;padding:11px;margin:5px 0;border:2px solid #e3e7f5;border-radius:10px;font-size:1rem}
 input:focus,select:focus{outline:none;border-color:#6a11cb}
 button.add{width:100%;padding:12px;margin-top:8px;border:0;border-radius:10px;font-size:1rem;
  color:#fff;cursor:pointer;background:linear-gradient(135deg,#6a11cb,#2575fc)}
 button.add:hover{filter:brightness(1.1)}
 .err{color:#d62839;min-height:20px;font-size:.9rem}
 .row{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #eef0f8}
 .ico{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:1.3rem;color:#fff}
 .info{flex:1}.info b{display:block}.info small{color:#7a82a6}
 .amt{font-weight:700}
 .del{border:0;background:#ffe3e6;color:#d62839;border-radius:8px;width:30px;height:30px;cursor:pointer}
 .del:hover{background:#d62839;color:#fff}
 .empty{color:#7a82a6;text-align:center;padding:20px 0}
 .full{grid-column:1/-1}
 #list{max-height:340px;overflow-y:auto}
</style></head>
<body><div class="wrap">
 <h1>PaisaTrack</h1>
 <p class="sub">Apna kharcha track karo, paisa bachao</p>

 <div class="stats">
  <div class="stat s1"><small>Total spent</small><b id="total">0</b></div>
  <div class="stat s2"><small>This month</small><b id="month">0</b></div>
  <div class="stat s3"><small>Transactions</small><b id="count">0</b></div>
 </div>

 <div class="grid">
  <div class="card">
   <h3>Add expense</h3>
   <input id="t" placeholder="What did you spend on? (e.g. Lunch)">
   <input id="a" type="number" min="1" placeholder="Amount in rupees">
   <select id="c">
    <option>Food</option><option>Travel</option><option>Shopping</option>
    <option>Bills</option><option>Health</option><option>Entertainment</option><option>Other</option>
   </select>
   <input id="d" type="date">
   <div class="err" id="err"></div>
   <button class="add" onclick="add()">Add expense</button>
  </div>
  <div class="card">
   <h3>Spending by category</h3>
   <canvas id="chart" height="220"></canvas>
  </div>
  <div class="card full">
   <h3>Recent expenses</h3>
   <div id="list"></div>
  </div>
 </div>
</div>

<script>
const COL={Food:'#ff7043',Travel:'#29b6f6',Shopping:'#ab47bc',Bills:'#fbc02d',
 Health:'#43a047',Entertainment:'#ec407a',Other:'#78909c'};
const ICO={Food:'🍔',Travel:'🚌',Shopping:'🛍️',Bills:'💡',Health:'💊',Entertainment:'🎬',Other:'📦'};
const $=id=>document.getElementById(id);
const inr=n=>'₹'+Number(n).toLocaleString('en-IN');
const esc=s=>String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
let chart;

async function load(){
  const [ex,sm]=await Promise.all([
    fetch('/api/expenses').then(r=>r.json()),
    fetch('/api/summary').then(r=>r.json())]);
  $('total').textContent=inr(sm.total);
  $('month').textContent=inr(sm.month_total);
  $('count').textContent=sm.count;
  $('list').innerHTML=ex.length?ex.map(e=>`
    <div class="row">
      <div class="ico" style="background:${COL[e.category]||'#78909c'}">${ICO[e.category]||'📦'}</div>
      <div class="info"><b>${esc(e.title)}</b><small>${esc(e.category)} • ${e.date}</small></div>
      <div class="amt">${inr(e.amount)}</div>
      <button class="del" onclick="del(${e.id})" title="Delete">✕</button>
    </div>`).join(''):'<div class="empty">No expenses yet. Add your first one!</div>';
  const labels=Object.keys(sm.by_category);
  const cfg={labels,datasets:[{data:Object.values(sm.by_category),
    backgroundColor:labels.map(l=>COL[l]||'#78909c'),borderWidth:2}]};
  if(chart){chart.data=cfg;chart.update();}
  else chart=new Chart($('chart'),{type:'doughnut',data:cfg,options:{plugins:{legend:{position:'bottom'}}}});
}

async function add(){
  $('err').textContent='';
  const r=await fetch('/api/expenses',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({title:$('t').value,amount:$('a').value,category:$('c').value,date:$('d').value})});
  if(!r.ok){$('err').textContent=(await r.json()).error;return;}
  $('t').value='';$('a').value='';load();
}
async function del(id){await fetch('/api/expenses/'+id,{method:'DELETE'});load();}

$('d').valueAsDate=new Date();
load();
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/sw.js').catch(()=>{});
}
</script></body></html>
"""


@app.get("/")
def home():
    return Response(PAGE, mimetype="text/html")



# ---------- PWA (phone par app ki tarah install hone ke liye) ----------
import base64

ICON_192 = "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"
ICON_512 = "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"

MANIFEST = {
    "name": "PaisaTrack - Expense Tracker",
    "short_name": "PaisaTrack",
    "description": "Apna kharcha track karo, paisa bachao",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#6a11cb",
    "theme_color": "#6a11cb",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}

SERVICE_WORKER = """
const CACHE = 'paisatrack-v1';
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(['/'])));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api/')) return;
  e.respondWith(
    fetch(e.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return r;
    }).catch(() => caches.match(e.request))
  );
});
"""


@app.get("/manifest.json")
def manifest():
    return jsonify(MANIFEST)


@app.get("/sw.js")
def service_worker():
    return Response(SERVICE_WORKER, mimetype="application/javascript",
                    headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})


@app.get("/icon-192.png")
def icon192():
    return Response(base64.b64decode(ICON_192), mimetype="image/png")


@app.get("/icon-512.png")
def icon512():
    return Response(base64.b64decode(ICON_512), mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True)