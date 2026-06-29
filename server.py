"""
🌸 Ayushi Life OS — Backend Server
Flask + SQLite — run with: python server.py
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, json, os, hashlib, hmac, base64, time
from datetime import datetime, timedelta, date

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/api/*": {"origins": "*"}})

DB_PATH = os.path.join(os.path.dirname(__file__), 'ayushi.db')
SECRET  = os.environ.get('SECRET_KEY', 'ayushi-secret-2025-change-in-prod')

# ─────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS days (
            date        TEXT PRIMARY KEY,          -- YYYY-MM-DD
            data        TEXT NOT NULL DEFAULT '{}',-- full JSON blob of all checked items / sliders
            score       INTEGER DEFAULT 0,         -- 0-100 overall
            health_score    INTEGER DEFAULT 0,
            career_score    INTEGER DEFAULT 0,
            learning_score  INTEGER DEFAULT 0,
            creative_score  INTEGER DEFAULT 0,
            xp_earned   INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gym_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            day_name    TEXT NOT NULL,             -- Monday, Tuesday...
            exercise    TEXT NOT NULL,
            weight      REAL,
            sets        INTEGER,
            reps        INTEGER,
            done        INTEGER DEFAULT 0,
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS goals (
            id          TEXT PRIMARY KEY,
            emoji       TEXT,
            title       TEXT NOT NULL,
            category    TEXT,
            current     REAL DEFAULT 0,
            target      REAL DEFAULT 100,
            unit        TEXT DEFAULT '%',
            color       TEXT DEFAULT '#e8649a',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS journal (
            date        TEXT PRIMARY KEY,
            win         TEXT,
            learned     TEXT,
            improve     TEXT,
            gratitude   TEXT,
            tomorrow    TEXT,
            free_write  TEXT,
            mood        TEXT,
            energy      INTEGER,
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS stats (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        -- seed default goals if empty
        INSERT OR IGNORE INTO goals VALUES
          ('g1','🍑','Hourglass Physique','Fitness',0,100,'%','#e8649a',datetime('now'),datetime('now')),
          ('g2','📚','Read 24 Books','Learning',0,24,'books','#9b7ed4',datetime('now'),datetime('now')),
          ('g3','💻','Solve 500 DSA','Learning',0,500,'qs','#6899d4',datetime('now'),datetime('now')),
          ('g4','💰','Learn Finance & Taxes','Learning',0,100,'%','#5bba8a',datetime('now'),datetime('now')),
          ('g5','💃','Dance Mastery','Creative',0,100,'%','#e8944d',datetime('now'),datetime('now')),
          ('g6','🎬','Grow on Social Media','Creative',0,10000,'followers','#c47fa8',datetime('now'),datetime('now')),
          ('g7','💸','Save ₹2,00,000','Finance',0,200000,'₹','#5bba8a',datetime('now'),datetime('now')),
          ('g8','🗣','Fluent English','Learning',0,100,'%','#6899d4',datetime('now'),datetime('now'));
        """)

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def today_str():
    return date.today().isoformat()

def compute_streak(db):
    """Walk backwards from today counting consecutive logged days."""
    rows = db.execute(
        "SELECT date FROM days ORDER BY date DESC"
    ).fetchall()
    dated = [r['date'] for r in rows]
    if not dated:
        return 0
    streak = 0
    check = date.today()
    for d in dated:
        if d == check.isoformat():
            streak += 1
            check -= timedelta(days=1)
        elif d == (check - timedelta(days=1)).isoformat():
            # allow yesterday gap (user hasn't saved today yet)
            check = date.fromisoformat(d)
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak

def compute_scores(data: dict) -> dict:
    """Reproduce the frontend scoring logic server-side."""
    def cb(key, pts):   return pts if data.get(key) else 0
    def rate(key, pts): return pts * int(data.get(key, 0)) / 100

    h = (
        cb('wake',5)+cb('water_m',3)+cb('brush',2)+cb('tongue',2)+cb('tablets',5)+
        cb('facewash',2)+cb('vit_c',3)+cb('moist',2)+cb('sunscreen',3)+cb('bfast',3)+
        cb('meditate',8)+cb('stretch_m',3)+
        cb('nosugar',8)+cb('nocoffee',5)+cb('fruits',3)+cb('veggies',3)+cb('healthy',5)+cb('protein_done',5)+
        cb('gym',20)+cb('warmup',3)+cb('cooldown',3)+cb('cardio',5)+cb('steps_done',8)+
        cb('bath',5)+cb('hairwash',3)+cb('hairol',2)+cb('cond',2)+cb('lotion',2)+
        cb('lipbalm',1)+cb('nightser',3)+cb('nightsk',3)+
        (cb('journal_done',5)+cb('gratitude',3)+cb('plan_tmr',5)+cb('read_bed',5)+cb('sleep11',8)+cb('phone_away',3))/2
    )
    h_max = 5+3+2+2+5+2+3+2+3+3+8+3+8+5+3+3+5+5+20+3+3+5+8+5+3+2+2+2+1+3+3+(5+3+5+5+8+3)/2
    if float(data.get('water', 0)) >= 3:  h += 10; h_max += 10
    if float(data.get('sleep', 0)) >= 7:  h += 10; h_max += 10
    if float(data.get('steps', 0)) >= 10: h += 5;  h_max += 5

    c = sum(rate(k, p) for k,p in [('office',20),('focus',10),('deepwork',10),('tasks',10)])
    c_max = 50

    l = sum(rate(k, p) for k,p in [('dsa',15),('finance',10),('taxes',8),('editing',8),('ai',8),('lang',8),('vocab',5),('reading_rate',10)])
    l_max = 72
    if int(data.get('words', 0)) >= 5: l += 5; l_max += 5

    cr = sum(rate(k, p) for k,p in [('dance',8),('content',8),('drawing',6),('social',4),('family',5)])
    cr_max = 31

    hp  = round(h/h_max*100)   if h_max  else 0
    cp  = round(c/c_max*100)   if c_max  else 0
    lp  = round(l/l_max*100)   if l_max  else 0
    crp = round(cr/cr_max*100) if cr_max else 0
    ov  = round(hp*0.35 + cp*0.25 + lp*0.25 + crp*0.15)

    return dict(overall=ov, health=hp, career=cp, learning=lp, creative=crp)

def compute_xp(data: dict) -> int:
    def cb(k, p): return p*3 if data.get(k) else 0
    def rate(k, p): return round(p * int(data.get(k,0))/100 * 3)
    xp = sum([
        cb('wake',5),cb('water_m',3),cb('brush',2),cb('tongue',2),cb('tablets',5),
        cb('facewash',2),cb('vit_c',3),cb('moist',2),cb('sunscreen',3),cb('bfast',3),
        cb('meditate',8),cb('stretch_m',3),
        cb('nosugar',8),cb('nocoffee',5),cb('fruits',3),cb('veggies',3),cb('healthy',5),cb('protein_done',5),
        cb('gym',20),cb('warmup',3),cb('cooldown',3),cb('cardio',5),cb('steps_done',8),
        cb('bath',5)*2//3,cb('hairwash',3)*2//3,cb('lotion',2)*2//3,cb('nightser',3)*2//3,cb('nightsk',3)*2//3,
        cb('journal_done',5)*2//3,cb('gratitude',3)*2//3,cb('plan_tmr',5)*2//3,cb('sleep11',8)*2//3,
        rate('office',20),rate('focus',10),rate('deepwork',10),rate('tasks',10),
        rate('dsa',15),rate('finance',10),rate('taxes',8),rate('editing',8),rate('ai',8),rate('lang',8),rate('vocab',5),rate('reading_rate',10),
        rate('dance',8)*2//3,rate('content',8)*2//3,rate('drawing',6)*2//3,rate('social',4)*2//3,rate('family',5)*2//3,
    ])
    if float(data.get('water',0)) >= 3:  xp += 100
    if float(data.get('sleep',0)) >= 7:  xp += 100
    if float(data.get('steps',0)) >= 10: xp += 100
    if int(data.get('words',0))   >= 5:  xp += 50
    return xp

def generate_analysis(day_data: dict, scores: dict, history: list) -> dict:
    """Generate AI-style text analysis of the day."""
    ov = scores['overall']
    
    # Rating label
    if ov >= 95:   rating, emoji = "Legendary", "👑"
    elif ov >= 90: rating, emoji = "Excellent", "🔥"
    elif ov >= 80: rating, emoji = "Great",     "😊"
    elif ov >= 70: rating, emoji = "Good",      "🙂"
    elif ov >= 60: rating, emoji = "Average",   "😐"
    else:          rating, emoji = "Getting Started", "💫"

    # Wins — things completed
    wins = []
    if day_data.get('gym'):      wins.append("Hit the gym 💪")
    if day_data.get('meditate'): wins.append("Meditated ✨")
    if float(day_data.get('water',0)) >= 3: wins.append("Drank 3L water 💧")
    if day_data.get('nosugar'):  wins.append("No sugar today 🍬")
    if day_data.get('nocoffee'): wins.append("No coffee ☕")
    if float(day_data.get('sleep',0)) >= 7: wins.append("Got 7+ hrs sleep 😴")
    if int(day_data.get('dsa',0)) > 60:     wins.append("Strong DSA session 💻")
    if int(day_data.get('dance',0)) > 60:   wins.append("Danced it out 💃")
    if day_data.get('journal_done'):         wins.append("Journaled 📖")
    if day_data.get('steps_done'):           wins.append("10k steps crushed 🚶‍♀️")

    # Misses — things not done
    misses = []
    if not day_data.get('gym'):      misses.append("Skipped gym")
    if not day_data.get('meditate'): misses.append("No meditation")
    if float(day_data.get('water',0)) < 2:  misses.append("Low water intake")
    if not day_data.get('nosugar'):          misses.append("Had sugar")
    if float(day_data.get('sleep',0)) < 6:  misses.append("Less than 6hrs sleep")
    if int(day_data.get('dsa',0)) < 20:     misses.append("Minimal DSA")
    if not day_data.get('journal_done'):     misses.append("Skipped journal")
    if not day_data.get('tablets'):          misses.append("Forgot tablets")

    # Trend vs last 7 days
    recent = [r['score'] for r in history[-7:] if r['score'] > 0]
    avg7 = round(sum(recent)/len(recent)) if recent else 0
    trend = "↑ Better than your 7-day average!" if ov > avg7 else ("→ On par with your average." if ov == avg7 else "↓ Below your average — bounce back tomorrow!")

    # Pillar feedback
    pillar_msgs = []
    for k, label, icon in [('health','Health','💚'),('career','Career','💼'),('learning','Learning','📚'),('creative','Creative','🎨')]:
        v = scores[k]
        if v >= 80:   pillar_msgs.append(f"{icon} {label}: {v}% — crushing it!")
        elif v >= 60: pillar_msgs.append(f"{icon} {label}: {v}% — solid effort")
        elif v >= 40: pillar_msgs.append(f"{icon} {label}: {v}% — room to grow")
        else:         pillar_msgs.append(f"{icon} {label}: {v}% — needs attention tomorrow")

    return {
        "rating": rating,
        "emoji": emoji,
        "score": ov,
        "wins": wins[:6],
        "misses": misses[:4],
        "trend": trend,
        "avg7": avg7,
        "pillar_feedback": pillar_msgs,
        "motivation": _motivation(ov, wins, misses),
    }

def _motivation(score, wins, misses):
    if score >= 90:
        return "You are literally unstoppable today. This is who you're becoming. 🌸"
    elif score >= 80:
        return "Really strong day Ayushi. A few more ticks and you'd be legendary. Keep this energy!"
    elif score >= 70:
        return "Good day! You showed up. Tomorrow, let's push those " + (misses[0] if misses else "last few habits") + " too."
    elif score >= 60:
        return "You did okay. Every day you track is a day you're growing. Don't stop now."
    else:
        return "Even logging this is a win. Tomorrow is a fresh 100%. You've got this 💪"

# ─────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────

@app.route('/api/ping')
def ping():
    return jsonify({"status": "ok", "message": "🌸 Ayushi Life OS backend running"})

# ── DAY ──────────────────────────────────

@app.route('/api/day/<date_str>', methods=['GET'])
def get_day(date_str):
    with get_db() as db:
        row = db.execute("SELECT * FROM days WHERE date=?", (date_str,)).fetchone()
        if not row:
            return jsonify({"date": date_str, "data": {}, "score": 0,
                            "health_score":0,"career_score":0,"learning_score":0,"creative_score":0})
        return jsonify({
            "date": row["date"],
            "data": json.loads(row["data"]),
            "score": row["score"],
            "health_score": row["health_score"],
            "career_score": row["career_score"],
            "learning_score": row["learning_score"],
            "creative_score": row["creative_score"],
            "xp_earned": row["xp_earned"],
        })

@app.route('/api/day/<date_str>', methods=['POST'])
def save_day(date_str):
    body = request.get_json(force=True)
    data = body.get('data', {})
    scores = compute_scores(data)
    xp     = compute_xp(data)

    with get_db() as db:
        db.execute("""
            INSERT INTO days (date, data, score, health_score, career_score, learning_score, creative_score, xp_earned, updated_at)
            VALUES (?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(date) DO UPDATE SET
              data=excluded.data, score=excluded.score,
              health_score=excluded.health_score, career_score=excluded.career_score,
              learning_score=excluded.learning_score, creative_score=excluded.creative_score,
              xp_earned=excluded.xp_earned, updated_at=excluded.updated_at
        """, (date_str, json.dumps(data), scores['overall'],
              scores['health'], scores['career'], scores['learning'], scores['creative'], xp))

        # update gym count stat if gym done
        if data.get('gym'):
            cur = db.execute("SELECT value FROM stats WHERE key='gym_count'").fetchone()
            new_val = int(cur['value'] if cur else 0) + 1
            db.execute("INSERT OR REPLACE INTO stats VALUES ('gym_count', ?)", (str(new_val),))

        # update no-sugar days
        if data.get('nosugar'):
            cur = db.execute("SELECT value FROM stats WHERE key='no_sugar_days'").fetchone()
            nv = int(cur['value'] if cur else 0) + 1
            db.execute("INSERT OR REPLACE INTO stats VALUES ('no_sugar_days', ?)", (str(nv),))

        # update water days
        if float(data.get('water', 0)) >= 3:
            cur = db.execute("SELECT value FROM stats WHERE key='water_days'").fetchone()
            nv = int(cur['value'] if cur else 0) + 1
            db.execute("INSERT OR REPLACE INTO stats VALUES ('water_days', ?)", (str(nv),))

        streak = compute_streak(db)
        history = db.execute("SELECT date, score FROM days ORDER BY date DESC LIMIT 30").fetchall()

        return jsonify({
            "saved": True,
            "scores": scores,
            "xp_earned": xp,
            "streak": streak,
            "analysis": generate_analysis(data, scores, [dict(r) for r in history])
        })

# ── ANALYSIS ─────────────────────────────

@app.route('/api/analysis/<date_str>', methods=['GET'])
def get_analysis(date_str):
    with get_db() as db:
        row = db.execute("SELECT * FROM days WHERE date=?", (date_str,)).fetchone()
        if not row:
            return jsonify({"error": "Day not found"}), 404
        data    = json.loads(row['data'])
        scores  = {'overall':row['score'],'health':row['health_score'],
                   'career':row['career_score'],'learning':row['learning_score'],'creative':row['creative_score']}
        history = db.execute("SELECT date, score FROM days ORDER BY date DESC LIMIT 30").fetchall()
        return jsonify(generate_analysis(data, scores, [dict(r) for r in history]))

# ── STATS / DASHBOARD ────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    with get_db() as db:
        streak    = compute_streak(db)
        best      = db.execute("SELECT MAX(score) as m FROM days").fetchone()['m'] or 0
        total_xp  = db.execute("SELECT SUM(xp_earned) as s FROM days").fetchone()['s'] or 0
        total_days= db.execute("SELECT COUNT(*) as c FROM days").fetchone()['c']

        # 7-day average
        week = db.execute(
            "SELECT AVG(score) as a FROM days WHERE date >= date('now','-7 days')"
        ).fetchone()['a'] or 0

        # 30-day average
        month = db.execute(
            "SELECT AVG(score) as a FROM days WHERE date >= date('now','-30 days')"
        ).fetchone()['a'] or 0

        # gym count
        gym_row = db.execute("SELECT value FROM stats WHERE key='gym_count'").fetchone()
        gym_count = int(gym_row['value']) if gym_row else 0

        # water days
        w_row = db.execute("SELECT value FROM stats WHERE key='water_days'").fetchone()
        water_days = int(w_row['value']) if w_row else 0

        # pillar 7-day averages
        pillar_week = db.execute("""
            SELECT AVG(health_score) h, AVG(career_score) c,
                   AVG(learning_score) l, AVG(creative_score) cr
            FROM days WHERE date >= date('now','-7 days')
        """).fetchone()

        return jsonify({
            "streak": streak,
            "best_day": best,
            "total_xp": int(total_xp),
            "total_days": total_days,
            "avg_7day": round(week),
            "avg_30day": round(month),
            "gym_count": gym_count,
            "water_days": water_days,
            "pillars_7day": {
                "health":   round(pillar_week['h'] or 0),
                "career":   round(pillar_week['c'] or 0),
                "learning": round(pillar_week['l'] or 0),
                "creative": round(pillar_week['cr'] or 0),
            }
        })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Return last N days for heatmap + charts."""
    days = int(request.args.get('days', 28))
    with get_db() as db:
        rows = db.execute(
            "SELECT date, score, health_score, career_score, learning_score, creative_score, xp_earned "
            "FROM days WHERE date >= date('now',?) ORDER BY date ASC",
            (f'-{days} days',)
        ).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route('/api/history/all', methods=['GET'])
def get_all_history():
    """Return every day ever logged."""
    with get_db() as db:
        rows = db.execute(
            "SELECT date, score, health_score, career_score, learning_score, creative_score, xp_earned, data "
            "FROM days ORDER BY date DESC"
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d['data'] = json.loads(d['data'])
            out.append(d)
        return jsonify(out)

# ── GYM ──────────────────────────────────

@app.route('/api/gym/<date_str>', methods=['GET'])
def get_gym(date_str):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM gym_log WHERE date=? ORDER BY id ASC", (date_str,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route('/api/gym', methods=['POST'])
def save_gym():
    body = request.get_json(force=True)
    date_str  = body.get('date', today_str())
    day_name  = body.get('day_name')
    exercises = body.get('exercises', [])  # [{exercise, weight, sets, reps, done, notes}]

    with get_db() as db:
        # delete old entries for this date+day
        db.execute("DELETE FROM gym_log WHERE date=? AND day_name=?", (date_str, day_name))
        for ex in exercises:
            db.execute("""
                INSERT INTO gym_log (date, day_name, exercise, weight, sets, reps, done, notes)
                VALUES (?,?,?,?,?,?,?,?)
            """, (date_str, day_name, ex.get('exercise',''),
                  ex.get('weight'), ex.get('sets'), ex.get('reps'),
                  1 if ex.get('done') else 0, ex.get('notes','')))
        
        # Check if any done → mark gym in day tracker
        any_done = any(e.get('done') for e in exercises)
        if any_done:
            row = db.execute("SELECT data FROM days WHERE date=?", (date_str,)).fetchone()
            data = json.loads(row['data']) if row else {}
            data['gym'] = True
            scores = compute_scores(data)
            xp = compute_xp(data)
            db.execute("""
                INSERT INTO days (date, data, score, health_score, career_score, learning_score, creative_score, xp_earned, updated_at)
                VALUES (?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(date) DO UPDATE SET data=excluded.data, score=excluded.score,
                  health_score=excluded.health_score, career_score=excluded.career_score,
                  learning_score=excluded.learning_score, creative_score=excluded.creative_score,
                  xp_earned=excluded.xp_earned, updated_at=excluded.updated_at
            """, (date_str, json.dumps(data), scores['overall'],
                  scores['health'], scores['career'], scores['learning'], scores['creative'], xp))

        return jsonify({"saved": True, "count": len(exercises)})

@app.route('/api/gym/history/<exercise>', methods=['GET'])
def gym_exercise_history(exercise):
    """Return progress history for a specific exercise (for PR tracking)."""
    with get_db() as db:
        rows = db.execute("""
            SELECT date, weight, sets, reps FROM gym_log
            WHERE exercise=? AND done=1 AND weight IS NOT NULL
            ORDER BY date ASC LIMIT 50
        """, (exercise,)).fetchall()
        return jsonify([dict(r) for r in rows])

# ── GOALS ────────────────────────────────

@app.route('/api/goals', methods=['GET'])
def get_goals():
    with get_db() as db:
        rows = db.execute("SELECT * FROM goals ORDER BY created_at ASC").fetchall()
        return jsonify([dict(r) for r in rows])

@app.route('/api/goals', methods=['POST'])
def save_goal():
    body = request.get_json(force=True)
    with get_db() as db:
        gid = body.get('id') or f"g_{int(time.time())}"
        db.execute("""
            INSERT INTO goals (id, emoji, title, category, current, target, unit, color, updated_at)
            VALUES (?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
              emoji=excluded.emoji, title=excluded.title, category=excluded.category,
              current=excluded.current, target=excluded.target, unit=excluded.unit,
              color=excluded.color, updated_at=excluded.updated_at
        """, (gid, body.get('emoji','🎯'), body.get('title','Goal'),
              body.get('category','Personal'), body.get('current',0),
              body.get('target',100), body.get('unit','%'), body.get('color','#e8649a')))
        return jsonify({"saved": True, "id": gid})

@app.route('/api/goals/<gid>', methods=['PATCH'])
def update_goal(gid):
    body = request.get_json(force=True)
    with get_db() as db:
        db.execute(
            "UPDATE goals SET current=?, updated_at=datetime('now') WHERE id=?",
            (body.get('current', 0), gid)
        )
        return jsonify({"saved": True})

@app.route('/api/goals/<gid>', methods=['DELETE'])
def delete_goal(gid):
    with get_db() as db:
        db.execute("DELETE FROM goals WHERE id=?", (gid,))
        return jsonify({"deleted": True})

# ── JOURNAL ──────────────────────────────

@app.route('/api/journal/<date_str>', methods=['GET'])
def get_journal(date_str):
    with get_db() as db:
        row = db.execute("SELECT * FROM journal WHERE date=?", (date_str,)).fetchone()
        return jsonify(dict(row) if row else {})

@app.route('/api/journal/<date_str>', methods=['POST'])
def save_journal(date_str):
    body = request.get_json(force=True)
    with get_db() as db:
        db.execute("""
            INSERT INTO journal (date, win, learned, improve, gratitude, tomorrow, free_write, mood, energy, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(date) DO UPDATE SET
              win=excluded.win, learned=excluded.learned, improve=excluded.improve,
              gratitude=excluded.gratitude, tomorrow=excluded.tomorrow,
              free_write=excluded.free_write, mood=excluded.mood,
              energy=excluded.energy, updated_at=excluded.updated_at
        """, (date_str, body.get('win'), body.get('learned'), body.get('improve'),
              body.get('gratitude'), body.get('tomorrow'), body.get('free_write'),
              body.get('mood'), body.get('energy')))
        # mark journal_done in day
        row = db.execute("SELECT data FROM days WHERE date=?", (date_str,)).fetchone()
        data = json.loads(row['data']) if row else {}
        data['journal_done'] = True
        scores = compute_scores(data)
        xp = compute_xp(data)
        db.execute("""
            INSERT INTO days (date, data, score, health_score, career_score, learning_score, creative_score, xp_earned, updated_at)
            VALUES (?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(date) DO UPDATE SET data=excluded.data, score=excluded.score,
              health_score=excluded.health_score, career_score=excluded.career_score,
              learning_score=excluded.learning_score, creative_score=excluded.creative_score,
              xp_earned=excluded.xp_earned, updated_at=excluded.updated_at
        """, (date_str, json.dumps(data), scores['overall'],
              scores['health'], scores['career'], scores['learning'], scores['creative'], xp))
        return jsonify({"saved": True})

# ── SERVE FRONTEND ────────────────────────

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# ─────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("\n🌸 Ayushi Life OS Backend Starting...")
    print("📦 Database:", DB_PATH)
    print("🌐 Open http://localhost:5000 in your browser")
    print("📱 On iPhone: open http://YOUR_PC_IP:5000 in Safari → Add to Home Screen\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
