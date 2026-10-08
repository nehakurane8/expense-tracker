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
</script></body></html>
"""


@app.get("/")
def home():
    return Response(PAGE, mimetype="text/html")


if __name__ == "__main__":
    app.run(debug=True)