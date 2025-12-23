from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
DB_NAME = "food.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS proposals 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  shop_name TEXT, 
                  menu_link TEXT, 
                  deadline TEXT,
                  delivery_time TEXT,
                  category TEXT,
                  initiator TEXT,
                  platform TEXT,
                  threshold INTEGER,
                  remarks TEXT, 
                  status TEXT DEFAULT 'OPEN',
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  proposal_id INTEGER, 
                  user_name TEXT, 
                  item TEXT, 
                  price INTEGER,
                  remarks TEXT, 
                  FOREIGN KEY(proposal_id) REFERENCES proposals(id))''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

def cleanup_old_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
    
    c.execute("SELECT id FROM proposals WHERE status='CLOSED' AND created_at < ?", (two_days_ago,))
    rows = c.fetchall()
    
    if rows:
        target_ids = [row[0] for row in rows]
        c.executemany("DELETE FROM orders WHERE proposal_id=?", [(i,) for i in target_ids])
        c.executemany("DELETE FROM proposals WHERE id=?", [(i,) for i in target_ids])
        
        conn.commit()
        print(f"系統自動清理了 {len(rows)} 筆過期資料")
        
    conn.close()

@app.route('/api/proposals', methods=['GET'])
def get_proposals():
    cleanup_old_data()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM proposals ORDER BY id DESC")
    rows = c.fetchall()
    
    proposals = []
    for row in rows:
        prop_id = row[0]
        c.execute("SELECT SUM(price), COUNT(*) FROM orders WHERE proposal_id=?", (prop_id,))
        result = c.fetchone()
        total_price = result[0] or 0
        order_count = result[1] or 0
        
        proposals.append({
            "id": row[0],
            "shop_name": row[1],
            "menu_link": row[2],
            "deadline": row[3],
            "delivery_time": row[4],
            "category": row[5],
            "initiator": row[6],
            "platform": row[7],
            "threshold": row[8],
            "remarks": row[9],
            "status": row[10],
            "created_at": row[11],
            "current_total": total_price,
            "order_count": order_count
        })
    conn.close()
    return jsonify(proposals)

@app.route('/api/proposals', methods=['POST'])
def add_proposal():
    data = request.json
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    threshold = int(data['threshold']) if data['threshold'] else 0
    c.execute("""INSERT INTO proposals 
                 (shop_name, menu_link, deadline, delivery_time, category, initiator, platform, threshold, remarks, status, created_at) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (data['shop_name'], data['menu_link'], data['deadline'], data['delivery_time'], 
               data['category'], data['initiator'], data['platform'], threshold, 
               data.get('remarks', ''), 'OPEN', datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/proposals/<int:prop_id>/close', methods=['PUT'])
def close_proposal(prop_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE proposals SET status='CLOSED' WHERE id=?", (prop_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/orders/<int:proposal_id>', methods=['GET'])
def get_orders(proposal_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, user_name, item, price, remarks FROM orders WHERE proposal_id=?", (proposal_id,))
    orders = [{"id": row[0], "user_name": row[1], "item": row[2], "price": row[3], "remarks": row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify(orders)

@app.route('/api/orders', methods=['POST'])
def add_order():
    data = request.json
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO orders (proposal_id, user_name, item, price, remarks) VALUES (?, ?, ?, ?, ?)",
              (data['proposal_id'], data['user_name'], data['item'], int(data['price']), data.get('remarks', '')))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    data = request.json
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE orders SET user_name=?, item=?, price=?, remarks=? WHERE id=?",
              (data['user_name'], data['item'], int(data['price']), data.get('remarks', ''), order_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM orders WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    init_db()

    app.run(debug=True, host='0.0.0.0', port=5001)
