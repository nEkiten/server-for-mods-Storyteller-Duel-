from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import threading

app = Flask(__name__)
CORS(app)

# Хранилище заказов
orders = []

# Хранилище активных игроков: {player_id: last_seen_timestamp}
active_players = {}

# Таймаут неактивности (15 минут)
PLAYER_TIMEOUT_SECONDS = 900  # 15 минут

# Очистка неактивных игроков
def clean_inactive_players():
    while True:
        time.sleep(60)
        current_time = time.time()
        to_remove = [pid for pid, last_seen in active_players.items() 
                    if current_time - last_seen > PLAYER_TIMEOUT_SECONDS]
        for pid in to_remove:
            del active_players[pid]
            print(f"[SERVER] Игрок {pid} удалён за неактивность")

cleanup_thread = threading.Thread(target=clean_inactive_players, daemon=True)
cleanup_thread.start()

# ===== РЕГИСТРАЦИЯ (поддерживаем и GET, и POST) =====
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация игрока и получение списка активных игроков"""
    
    # Получаем playerId из GET параметров или из POST JSON
    player_id = None
    
    if request.method == 'GET':
        player_id = request.args.get('playerId')
    else:
        data = request.get_json()
        if data:
            player_id = data.get('playerId')
    
    # Если playerId не передан, генерируем новый
    if not player_id:
        player_id = str(uuid.uuid4())
        print(f"[SERVER] Сгенерирован новый ID: {player_id}")
    
    # Обновляем время последнего обращения
    active_players[player_id] = time.time()
    
    # Получаем список всех активных игроков (кроме себя)
    current_time = time.time()
    active_list = [pid for pid, last_seen in active_players.items() 
                  if pid != player_id and current_time - last_seen < PLAYER_TIMEOUT_SECONDS]
    
    print(f"[SERVER] Игрок {player_id} зарегистрирован. Активных: {len(active_list)}")
    
    return jsonify({
        "status": "ok",
        "players": active_list,
        "yourId": player_id
    })

@app.route('/players', methods=['GET'])
def get_players():
    """Получение списка всех активных игроков"""
    current_time = time.time()
    active_list = [pid for pid, last_seen in active_players.items() 
                  if current_time - last_seen < PLAYER_TIMEOUT_SECONDS]
    return jsonify({"players": active_list})

@app.route('/order', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data:
        return "Bad request", 400
    
    orders.append({
        "sender": data.get("sender"),
        "receiver": data.get("receiver"),
        "eventId": data.get("eventId"),
        "strength": data.get("strength", 1.0),
        "cost": data.get("cost", 0),
        "timestamp": time.time()
    })
    
    print(f"[SERVER] Заказ от {data.get('sender')} для {data.get('receiver')}: {data.get('eventId')}")
    return jsonify({"status": "ok"}), 200

@app.route('/orders/<player_id>', methods=['GET'])
def get_orders(player_id):
    player_orders = [o for o in orders if o["receiver"] == player_id]
    for o in player_orders:
        orders.remove(o)
    return jsonify(player_orders)

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "active_players": len(active_players),
        "pending_orders": len(orders),
        "players": list(active_players.keys())
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "server": "Storyteller Duel Server",
        "endpoints": {
            "/register": "GET/POST - Register player",
            "/players": "GET - List active players",
            "/order": "POST - Send order",
            "/orders/<id>": "GET - Get orders for player",
            "/status": "GET - Server status"
        }
    })

if __name__ == '__main__':
    print("[SERVER] Storyteller Duel Server запущен на http://0.0.0.0:5000")
    print("[SERVER] Таймаут неактивности игроков: 15 минут")
    app.run(host='0.0.0.0', port=5000, debug=True)