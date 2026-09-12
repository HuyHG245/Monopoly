import random
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from core.game_manager import GameManager
from core.dice_system import DiceSystem

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'tsm_monopoly_secret_key'

socketio = SocketIO(app, cors_allowed_origins="*")
game = GameManager()
dice_system = DiceSystem()

player_jail_turns = {} 
player_doubles_count = {} 
pending_debts = {}
pending_bankrupt_inherit = {}
current_trade = None

active_builders = set()
was_paused_before_build = False
pending_build_actions = {}

active_auction = {
    'space_id': None, 'space_name': "", 'current_bid': 100000, 
    'highest_bidder_sid': None, 'highest_bidder_name': "Chưa có", 'active_bidders': [],
    'initiator_sid': None, 'is_double': False, 'version': 0,
    'phase': None, 'votes': {}, 'blind_bids': {}, 'start_time': 0.0
}

CHANCE_CARDS_DECK = [
    {"id": "c1", "action": "move_nearest_rail", "text": "Đi vé hạng nhất đến trạm Monopoly Rail.<br>Nếu đi qua ô BẮT ĐẦU, nhận 2,000,000<s>M</s>."},
    {"id": "c2", "action": "move_nearest_rail", "text": "Tiến đến Trạm Xe Lửa gần nhất.<br>Nếu chưa có chủ, bạn có thể mua.<br>Nếu đã có chủ, trả gấp đôi tiền thuê thông thường.<br>Nếu đi qua ô BẮT ĐẦU, nhận 2,000,000<s>M</s>."},
    {"id": "c3", "action": "move_nearest_rail", "text": "Tiến đến Trạm Xe Lửa gần nhất.<br>Nếu chưa có chủ, bạn có thể mua.<br>Nếu đã có chủ, trả gấp đôi tiền thuê thông thường.<br>Nếu đi qua ô BẮT ĐẦU, nhận 2,000,000<s>M</s>."},
    {"id": "c4", "action": "add_money", "amount": 500000, "text": "Được giảm thuế nhờ lái xe hybrid.<br>Nhận 500,000<s>M</s>."},
    {"id": "c5", "action": "move", "target": 11, "text": "Tự thưởng một chuyến du lịch đến Istanbul.<br>Nếu đi qua ô BẮT ĐẦU, nhận 2,000,000<s>M</s>."},
    {"id": "c6", "action": "back_3", "text": "Bị triệu tập làm bồi thẩm đoàn.<br>Lùi lại 3 ô."},
    {"id": "c7", "action": "pay", "amount": 150000, "text": "Quyên góp cứu trợ thiên tai.<br>Trả 150,000<s>M</s>."},
    {"id": "c8", "action": "pay_one_player", "amount": 500000, "text": "Một người chơi khác khởi kiện bạn.<br>Chọn một người chơi và đền bù cho họ 500,000<s>M</s>."},
    {"id": "c9", "action": "go_jail", "text": "Bị kết tội đánh cắp danh tính.<br>VÀO TÙ. Không đi qua ô BẮT ĐẦU, không nhận 2,000,000<s>M</s>."},
    {"id": "c10", "action": "maintenance", "text": "Thành phố đánh giá lại mức thuế.<br>Trả 250,000<s>M</s> cho mỗi Ngôi Nhà và 1,000,000<s>M</s> cho mỗi Khách Sạn bạn đang sở hữu."},
    {"id": "c11", "action": "move", "target": 24, "text": "Lên máy bay tới London.<br>Nếu đi qua ô BẮT ĐẦU, nhận 2,000,000<s>M</s>."},
    {"id": "c12", "action": "move_nearest_util", "text": "Tiến đến Công ty Tiện ích gần nhất.<br>Nếu chưa có chủ, bạn có thể mua.<br>Nếu đã có chủ, tung xúc xắc và trả gấp 10,000 lần số chấm.<br>Nếu đi qua ô BẮT ĐẦU, nhận 2,000,000<s>M</s>."},
    {"id": "c13", "action": "get_out_jail", "text": "Bạn được trắng án. THẺ RA TÙ MIỄN PHÍ.<br>Có thể giữ thẻ này để dùng sau hoặc đem trao đổi."},
    {"id": "c14", "action": "move", "target": 39, "text": "Ngồi trực thăng tới Montreal.<br>Nếu đi qua ô BẮT ĐẦU, nhận 2,000,000<s>M</s>."},
    {"id": "c15", "action": "add_money", "amount": 1500000, "text": "Nhận chức CEO tại một ngân hàng đầu tư lớn.<br>Nhận tiền thưởng nhậm chức 1,500,000<s>M</s>."},
    {"id": "c16", "action": "move", "target": 0, "text": "Tiến đến ô BẮT ĐẦU.<br>(Nhận 2,000,000<s>M</s>)"}
]

COMMUNITY_CHEST_CARDS_DECK = [
    {"id": "cc1", "action": "pay", "amount": 500000, "text": "Học nhảy cùng huấn luyện viên nổi tiếng.<br>Trả 500,000<s>M</s>."},
    {"id": "cc2", "action": "pay", "amount": 500000, "text": "Bạn nợ thuế chưa thanh toán.<br>Trả 500,000<s>M</s>."},
    {"id": "cc3", "action": "add_money", "amount": 200000, "text": "Bán vé xem thể thao trọn đời của bạn.<br>Nhận 200,000<s>M</s>."},
    {"id": "cc4", "action": "add_money", "amount": 500000, "text": "Quỹ tín thác của bạn đã có thể giải ngân.<br>Nhận 500,000<s>M</s>."},
    {"id": "cc5", "action": "add_money", "amount": 1000000, "text": "Thắng lớn tại sòng bạc.<br>Nhận 1,000,000<s>M</s>."},
    {"id": "cc6", "action": "add_money", "amount": 100000, "text": "Quảng bá sách mới trên bản tin buổi sáng.<br>Nhận 100,000<s>M</s> doanh thu tăng thêm."},
    {"id": "cc7", "action": "collect_all", "amount": 100000, "text": "Tranh cử Thị trưởng.<br>Thu 100,000<s>M</s> từ mỗi người chơi khác để gây quỹ tranh cử."},
    {"id": "cc8", "action": "move", "target": 0, "text": "Tiến đến ô BẮT ĐẦU.<br>(Nhận 2,000,000<s>M</s>)"},
    {"id": "cc9", "action": "add_money", "amount": 2000000, "text": "Thành công vang dội tại Hollywood.<br>Nhận 2,000,000<s>M</s> từ hợp đồng đóng phim."},
    {"id": "cc10", "action": "maintenance", "text": "Cải tạo cảnh quan tại tất cả các khu đất của bạn.<br>Trả 400,000<s>M</s> cho mỗi Ngôi nhà và 1,150,000<s>M</s> cho mỗi Khách sạn."},
    {"id": "cc11", "action": "go_jail", "text": "Bị bắt vì giao dịch nội gián.<br>VÀO TÙ. Không đi qua ô BẮT ĐẦU, không nhận 2,000,000<s>M</s>."},
    {"id": "cc12", "action": "add_money", "amount": 100000, "text": "Đạt giải Á quân trong show truyền hình thực tế.<br>Nhận 100,000<s>M</s>."},
    {"id": "cc13", "action": "add_money", "amount": 1000000, "text": "Trúng xổ số.<br>Nhận 1,000,000<s>M</s>."},
    {"id": "cc14", "action": "add_money", "amount": 250000, "text": "Được chọn làm linh vật cho trận chung kết của đội tại Wembley.<br>Nhận 250,000<s>M</s> thù lao."},
    {"id": "cc15", "action": "pay", "amount": 1000000, "text": "Mạng máy tính của bạn bị nhiễm virus.<br>Trả 1,000,000<s>M</s>."},
    {"id": "cc16", "action": "get_out_jail", "text": "Nhận được lệnh ân xá của Hoàng gia. THẺ RA TÙ MIỄN PHÍ.<br>Có thể giữ thẻ này để dùng sau hoặc đem trao đổi."}
]

chance_deck = []
chest_deck = []

def shuffle_deck(deck_type):
    global chance_deck, chest_deck
    if deck_type == 'chance':
        chance_deck = CHANCE_CARDS_DECK.copy()
        players_jail_cards = sum(getattr(p, 'out_of_jail_free', 0) for p in game.players.values())
        if players_jail_cards > 0:
            chance_deck = [c for c in chance_deck if c['id'] != 'c13']
        random.shuffle(chance_deck)
    else:
        chest_deck = COMMUNITY_CHEST_CARDS_DECK.copy()
        players_jail_cards = sum(getattr(p, 'out_of_jail_free', 0) for p in game.players.values())
        if players_jail_cards > 0:
            chest_deck = [c for c in chest_deck if c['id'] != 'cc16']
        random.shuffle(chest_deck)

def draw_card(deck_type):
    global chance_deck, chest_deck
    if deck_type == 'chance':
        if len(chance_deck) == 0:
            shuffle_deck('chance')
        return chance_deck.pop()
    else:
        if len(chest_deck) == 0:
            shuffle_deck('chest')
        return chest_deck.pop()

def reset_server_states():
    game.reset_game()
    player_jail_turns.clear()
    player_doubles_count.clear()
    pending_debts.clear()
    pending_bankrupt_inherit.clear()
    
    global current_trade, active_builders, pending_build_actions, was_paused_before_build
    active_builders.clear()
    pending_build_actions.clear()
    was_paused_before_build = False
    current_trade = None
    
    shuffle_deck('chance')
    shuffle_deck('chest')
    active_auction.update({
        'space_id': None, 'space_name': "", 'current_bid': 100000, 
        'highest_bidder_sid': None, 'highest_bidder_name': "Chưa có", 'active_bidders': [],
        'initiator_sid': None, 'is_double': False, 'version': active_auction.get('version', 0) + 1,
        'phase': None, 'votes': {}, 'blind_bids': {}, 'start_time': 0.0
    })

def check_initial_roll_completion():
    active_sids = [sid for sid, p in game.players.items() if not getattr(p, 'is_bankrupt', False) and not getattr(p, 'disconnected', False)]
    game.players_to_roll = [sid for sid in game.players_to_roll if sid in active_sids]
    
    if len(game.players_to_roll) == 0:
        history_groups = {}
        for sid in active_sids:
            hist_tuple = tuple(game.initial_roll_history.get(sid, [0]))
            if hist_tuple not in history_groups:
                history_groups[hist_tuple] = []
            history_groups[hist_tuple].append(sid)
        
        tied_sids = []
        for hist_tuple, sids in history_groups.items():
            if len(sids) > 1:
                tied_sids.extend(sids)
                
        if tied_sids:
            game.players_to_roll = tied_sids
            names = [game.players[s].name for s in tied_sids]
            socketio.emit('server_message', {'msg': f"⚠️ Trùng điểm! Yêu cầu {', '.join(names)} tung lại để phân định."})
        else:
            sorted_sids = sorted(active_sids, key=lambda s: game.initial_roll_history.get(s, [0]), reverse=True)
            game.player_order = sorted_sids
            game.current_turn_index = 0
            game.is_initial_rolling = False
            game.is_paused = False
            game.pause_reason = ""
            game.last_timer_update = time.time()
            order_names = [game.players[s].name for s in sorted_sids]
            order_str = " ➔ ".join(order_names)
            socketio.emit('server_message', {'msg': f"✅ Thứ tự lượt đi đã được chốt:<br>{order_str}"})
            socketio.emit('server_message', {'msg': f"🎮 Trận đấu Monopoly chính thức bắt đầu!"})

def end_game_delayed(msg):
    socketio.sleep(10)
    trigger_end_game(msg)

def trigger_end_game(msg="Ván đấu kết thúc!"):
    leaderboard = []
    active_players = [p for p in game.players.values() if not getattr(p, 'is_bankrupt', False)]
    for p in active_players:
        total = game.get_total_assets_value(p.name)
        leaderboard.append({'name': p.name, 'color': p.color, 'total': total, 'balance': p.balance})
    leaderboard.sort(key=lambda x: x['total'], reverse=True)
    
    for ep in reversed(game.eliminated_players):
        leaderboard.append(ep)
        
    sids_to_remove = [sid for sid, p in game.players.items() if getattr(p, 'disconnected', False)]
    for sid in sids_to_remove: 
        game.remove_player(sid)
        
    reset_server_states()
    host_sid = list(game.players.keys())[0] if game.players else None
    player_list = [{'id': s, 'name': p.name, 'color': p.color, 'is_ready': getattr(p, 'is_ready', False)} for s, p in game.players.items()]
    socketio.emit('game_stopped', {'players': player_list, 'host_sid': host_sid, 'leaderboard': leaderboard, 'msg': msg})
    socketio.emit('player_list_updated', {'players': player_list, 'host_sid': host_sid, 'settings': game.settings})

def broadcast_taken_colors():
    socketio.emit('update_taken_colors', [p.color for p in game.players.values()])

def broadcast_game_state(msg=None):
    players_financial_data = [{
        'sid': sid, 'name': p.name, 'color': p.color, 'balance': p.balance, 'position': p.position, 
        'out_of_jail_free': getattr(p, 'out_of_jail_free', 0), 'is_bankrupt': getattr(p, 'is_bankrupt', False), 'in_jail': (sid in player_jail_turns),
        'properties': [{'id': b['id'], 'name': b['name'], 'color': b['color'], 'type': b['type'], 'houses': b['houses'], 'hotel': b['hotel'], 'is_mortgaged': b['is_mortgaged']} for b in game.board if b['owner'] == p.name]
    } for sid, p in game.players.items()]
    
    current_p = game.get_current_player()
    socketio.emit('update_game_state', {
        'players_stats': players_financial_data,
        'global_houses': game.global_houses, 'global_hotels': game.global_hotels,
        'turn_order': [game.players[sid].name for sid in game.player_order if not getattr(game.players[sid], 'is_bankrupt', False)],
        'current_turn_name': current_p.name if current_p else "",
        'current_turn_sid': current_p.id if current_p else None,
        'is_paused': game.is_paused, 'pause_reason': game.pause_reason, 
        'unlimited_time': game.settings.get('unlimited_time', False),
        'remaining_time': game.get_current_remaining_time(), 
        'is_initial_rolling': getattr(game, 'is_initial_rolling', False), 
        'players_to_roll': getattr(game, 'players_to_roll', [])
    })
    if msg:
        socketio.emit('server_message', {'msg': msg})

def remove_bankrupt_player(bankrupt_sid, creditor_name, reason="Không đủ tiền trả nợ"):
    if bankrupt_sid not in game.players: return
    player = game.players[bankrupt_sid]
    if getattr(player, 'is_bankrupt', False): return
    
    total_val = game.get_total_assets_value(player.name)
    game.eliminated_players.append({'name': player.name, 'color': player.color, 'total': total_val, 'balance': player.balance})
    
    player.is_bankrupt = True
    player.balance = 0
    inherited_mortgages = []
    
    for space in game.board:
        if space['owner'] == player.name:
            if creditor_name and creditor_name != "Ngân Hàng":
                space['owner'] = creditor_name
                game.global_houses += space['houses']
                game.global_hotels += space['hotel']
                space['houses'] = 0
                space['hotel'] = 0
                space['is_mortgaged'] = True
                space['unmortgage'] = int(space['mortgage'] * 1.1)
                inherited_mortgages.append(space)
            else:
                space['owner'] = None
                space['is_mortgaged'] = False
                game.global_houses += space['houses']
                game.global_hotels += space['hotel']
                space['houses'] = 0
                space['hotel'] = 0

    socketio.emit('player_bankrupted', {'msg': f"Lý do: {reason}<br>Tổng tài sản chuyển giao: <b style='color:#f1c40f'>{total_val:,}<s>M</s></b>"}, room=bankrupt_sid)
    broadcast_game_state(f"💀 Lệnh Phá Sản: {player.name} đã mất toàn bộ tài sản!")
    
    active_players = [p for p in game.players.values() if not getattr(p, 'is_bankrupt', False)]
    is_game_over = len(active_players) <= 1

    if creditor_name and creditor_name != "Ngân Hàng" and not is_game_over:
        creditor_sid = next((sid for sid, p in game.players.items() if p.name == creditor_name), None)
        if creditor_sid and inherited_mortgages:
            total_fee = sum(int(s['mortgage'] * 0.1) for s in inherited_mortgages)
            creditor = game.players[creditor_sid]
            pending_bankrupt_inherit[creditor_sid] = inherited_mortgages
            if creditor.balance >= total_fee:
                creditor.balance -= total_fee
                socketio.emit('server_message', {'msg': f"⚖️ {creditor_name} bị trừ {total_fee:,}<s>M</s> phí sang tên tài sản cầm cố."})
                socketio.emit('open_inherit_modal', {'properties': [{'id': s['id'], 'name': s['name'], 'unmortgage': s['unmortgage']} for s in inherited_mortgages], 'fee_paid': total_fee}, room=creditor_sid)
            else:
                if game.get_total_assets_value(creditor.name) < total_fee:
                    remove_bankrupt_player(creditor_sid, "Ngân Hàng", f"Không đủ tiền nộp thuế kế thừa tài sản của {player.name}")
                else:
                    pending_debts[creditor_sid] = {'amount': total_fee, 'creditor': "Ngân Hàng", 'reason': f"Phí 10% nhận tài sản thừa kế từ {player.name}", 'popup_data': {'type': 'Inherit', 'properties': inherited_mortgages, 'fee_paid': total_fee}, 'is_double': False}
                    send_liquidation_menu(creditor_sid)

    if is_game_over and game.game_started:
        winner = active_players[0] if active_players else None
        if winner:
            socketio.emit('show_victory', {'winner_name': winner.name, 'total_assets': game.get_total_assets_value(winner.name)})
        socketio.start_background_task(end_game_delayed, f"🎉 Trận đấu kết thúc! {winner.name if winner else 'Không ai'} là người chiến thắng cuối cùng!")
        return

    if game.current_turn_index >= len(game.player_order):
        game.current_turn_index = 0
    broadcast_game_state()

def check_payment(session_id, player, amount, creditor_name, reason, popup_data, is_double):
    if player.balance >= amount:
        player.balance -= amount
        if creditor_name and creditor_name != "Ngân Hàng":
            creditor = next((p for p in game.players.values() if p.name == creditor_name), None)
            if creditor:
                creditor.balance += amount
            socketio.emit('server_message', {'msg': f"💸 {player.name} đã trả {amount:,}<s>M</s> tiền thuê cho {creditor_name}."})
        else:
            socketio.emit('server_message', {'msg': f"💸 {player.name} thanh toán {amount:,}<s>M</s> ({reason})."})
        return True, popup_data
    else:
        if game.get_total_assets_value(player.name) < amount:
            remove_bankrupt_player(session_id, creditor_name, reason)
            return False, None
        else:
            pending_debts[session_id] = {'amount': amount, 'creditor': creditor_name, 'reason': reason, 'popup_data': popup_data, 'is_double': is_double}
            send_liquidation_menu(session_id)
            return False, "LIQUIDATE"

def send_liquidation_menu(session_id):
    player = game.players[session_id]
    debt = pending_debts[session_id]
    properties = []
    for space in game.board:
        if space['owner'] == player.name:
            properties.append({'id': space['id'], 'name': space['name'], 'color': space['color'], 'is_mortgaged': space['is_mortgaged'], 'houses': space['houses'], 'hotel': space['hotel'], 'mortgage_val': space['mortgage'], 'house_val': space['house_price'] // 2, 'can_sell_house': game.can_sell_house(space['id'])})
    can_undo = len(debt.get('actions', [])) > 0
    socketio.emit('open_liquidation_menu', {'debt_amount': debt['amount'], 'current_balance': player.balance, 'properties': properties, 'reason': debt['reason'], 'can_undo': can_undo}, room=session_id)

def apply_card_effect(session_id, player, card, prefix_msg, is_double):
    action = card['action']
    popup_data = {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': prefix_msg}
    socketio.emit('server_message', {'msg': f"🃏 {player.name} bốc thẻ: {card['text'].replace('<br>', ' ')}"})
    clean_text = card['text'].replace('<br>', ' ').replace('<s>', '').replace('</s>', '').strip()
    reason = f"Thẻ Sự Kiện: {clean_text}"

    if action == "move":
        old_pos = player.position
        player.position = card['target']
        socketio.emit('server_message', {'msg': f"🚶‍♂️ {player.name} dịch chuyển đến {game.board[player.position]['name']}."})
        if player.position < old_pos and player.position != 10:
            player.passed_go = True
            player.balance += 2000000
            socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})
        return process_space(session_id, player, player.position, prefix_msg, is_double)
        
    elif action == "move_nearest_rail":
        old_pos = player.position
        if player.position < 5 or player.position >= 35: player.position = 5
        elif player.position < 15: player.position = 15
        elif player.position < 25: player.position = 25
        elif player.position < 35: player.position = 35
        socketio.emit('server_message', {'msg': f"🚶‍♂️ {player.name} tiến đến {game.board[player.position]['name']}."})
        if player.position < old_pos:
            player.passed_go = True
            player.balance += 2000000
            socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})
        return process_space(session_id, player, player.position, prefix_msg, is_double)
        
    elif action == "move_nearest_util":
        old_pos = player.position
        if player.position < 12 or player.position >= 28: player.position = 12
        elif player.position < 28: player.position = 28
        socketio.emit('server_message', {'msg': f"🚶‍♂️ {player.name} tiến đến {game.board[player.position]['name']}."})
        if player.position < old_pos:
            player.passed_go = True
            player.balance += 2000000
            socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})
        return process_space(session_id, player, player.position, prefix_msg, is_double)
        
    elif action == "back_3":
        player.position = (player.position - 3) % 40
        socketio.emit('server_message', {'msg': f"🚶‍♂️ {player.name} bị lùi lại 3 ô, đến {game.board[player.position]['name']}."})
        return process_space(session_id, player, player.position, prefix_msg, is_double)
        
    elif action == "go_jail":
        player.position = 10
        player_jail_turns[session_id] = 0
        player.in_jail = True 
        socketio.emit('server_message', {'msg': f"🚓 {player.name} bị tống vào Tù!"})
        return True, {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': 10, 'price': 0, 'message': prefix_msg}
        
    elif action == "add_money":
        player.balance += card['amount']
        socketio.emit('server_message', {'msg': f"💵 {player.name} nhận {card['amount']:,}<s>M</s>."})
        return True, {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': prefix_msg}
        
    elif action == "pay":
        popup_data = {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': prefix_msg}
        return check_payment(session_id, player, card['amount'], "Ngân Hàng", reason, popup_data, is_double)
        
    elif action == "pay_one_player":
        other_players = [{'sid': sid, 'name': p.name} for sid, p in game.players.items() if sid != session_id and not getattr(p, 'is_bankrupt', False)]
        if other_players:
            socketio.emit('open_player_select', {'amount': card['amount'], 'players': other_players, 'text': card['text']}, room=session_id)
            return False, None
        else:
            socketio.emit('server_message', {'msg': f"🃏 {player.name} bốc thẻ nhưng không có người chơi nào khác để đền bù."})
            return True, {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': prefix_msg}
        
    elif action == "pay_all":
        active_count = sum(1 for p in game.players.values() if not getattr(p, 'is_bankrupt', False))
        return check_payment(session_id, player, card['amount'] * (active_count - 1), "Ngân Hàng", reason, popup_data, is_double)
        
    elif action == "collect_all":
        amount = card['amount']
        for sid, p in game.players.items():
            if sid != session_id and not getattr(p, 'is_bankrupt', False):
                p.balance -= amount
                player.balance += amount
        socketio.emit('server_message', {'msg': f"🎉 {player.name} đã thu tiền từ mọi người."})
        return True, {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': prefix_msg}
        
    elif action == "get_out_jail":
        player.out_of_jail_free = getattr(player, 'out_of_jail_free', 0) + 1
        socketio.emit('server_message', {'msg': f"🎟️ {player.name} nhận Thẻ Ra Tù."})
        return True, {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': prefix_msg}
        
    elif action == "maintenance":
        total_houses = sum(s['houses'] for s in game.board if s['owner'] == player.name)
        total_hotels = sum(s['hotel'] for s in game.board if s['owner'] == player.name)
        cost = (total_houses * 250000 + total_hotels * 1000000) if card['id'] == 'c10' else (total_houses * 400000 + total_hotels * 1150000)
        popup_data = {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': prefix_msg}
        if cost > 0:
            return check_payment(session_id, player, cost, "Ngân Hàng", reason, popup_data, is_double)
        else:
            socketio.emit('server_message', {'msg': f"🔧 {player.name} không có nhà, không mất phí bảo trì."})
            return True, popup_data

    return True, {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': prefix_msg}

@socketio.on('submit_card_target')
def handle_submit_card_target(data):
    session_id = request.sid
    target_sid = data.get('target_sid')
    if session_id not in game.players: return
    player = game.players[session_id]
    target_player = game.players.get(target_sid)
    if not target_player or getattr(target_player, 'is_bankrupt', False): return
    
    amount = 500000
    socketio.emit('close_player_select', room=session_id)
    reason = f"Đền bù do bị khởi kiện cho {target_player.name}"
    success, popup_data = check_payment(session_id, player, amount, target_player.name, reason, None, False)
    
    if success:
        popup_msg = f"Đã trả cho {target_player.name} {amount:,}<s>M</s>."
        socketio.emit('show_action_popup', {'die1': '-', 'die2': '-', 'total': 0, 'special': '', 'jail_msg': "", 'popup': {'title': 'Thẻ Sự Kiện', 'type': 'Event', 'space_id': player.position, 'price': 0, 'message': popup_msg}, 'is_double': False}, room=session_id)
    elif getattr(player, 'is_bankrupt', False):
        end_turn_logic(session_id, False)

def process_space(session_id, player, space_id, prefix_msg="", is_double=False, dice_total=0):
    space = game.board[space_id]
    action_type = space['type']
    
    if action_type == "Chance":
        return apply_card_effect(session_id, player, draw_card('chance'), prefix_msg + f"<br>❓ [CƠ HỘI]: {draw_card('chance')['text']}<br>", is_double)
    elif action_type == "CommunityChest":
        return apply_card_effect(session_id, player, draw_card('chest'), prefix_msg + f"<br>🎁 [KHÍ LỆNH]: {draw_card('chest')['text']}<br>", is_double)
        
    popup_data = {'title': space['name'], 'type': action_type, 'price': space['price'], 'space_id': space_id, 'message': prefix_msg + f"Dừng chân tại {space['name']}."}

    if action_type in ["Property", "Railroad", "Utility"]:
        if space['owner'] is None:
            if player.balance >= space['price']:
                popup_data['type'] = "EmptyProperty"
                popup_data['message'] += f"<br>Giá: {space['price']:,}<s>M</s>. Bạn có thể Mua hoặc Đấu Giá!"
            else:
                popup_data['type'] = "NotEnoughMoney"
                popup_data['message'] += f"<br>Không đủ tiền mua. Bắt buộc Đấu Giá!"
            return True, popup_data
        elif space['owner'] != player.name and not space['is_mortgaged']:
            rent_fee = space['rent']
            if action_type == "Property":
                rl = space['rent_levels']
                if rl:
                    rent_fee = rl[5] if space['hotel'] == 1 else (rl[space['houses']] if space['houses'] > 0 else (rl[0] * 2 if game.check_monopoly(space['owner'], space['color']) else rl[0]))
            elif action_type == "Railroad":
                rc = sum(1 for s in game.board if s['type'] == 'Railroad' and s['owner'] == space['owner'])
                rent_fee = space['rent_levels'][rc - 1] if rc > 0 else 0
            elif action_type == "Utility":
                uc = sum(1 for s in game.board if s['type'] == 'Utility' and s['owner'] == space['owner'])
                u_d1, u_d2 = random.randint(1, 6), random.randint(1, 6)
                u_tot = u_d1 + u_d2
                u_spec = None
                u_spec_str = ""
                
                if game.settings.get('special_dice', True) and getattr(player, 'passed_go', False):
                    u_spec = random.choice([1, 2, 3, 'Bus', 'Bus', 'Mr.Monopoly'])
                    u_spec_str = f", Đặc biệt [{u_spec}]"
                    if isinstance(u_spec, int): u_tot += u_spec
                
                socketio.emit('show_dice_roll', {'die1': u_d1, 'die2': u_d2, 'special_die': u_spec})
                socketio.sleep(1.8)
                
                rent_fee = u_tot * (100000 if uc == 2 else 40000)
                socketio.emit('server_message', {'msg': f"⚡ Định giá Tiện Ích: Đổ {u_d1} và {u_d2}{u_spec_str} (Tổng: {u_tot})."})
                popup_data['message'] += f"<br>🎲 Tung xúc xắc tính phí: {u_tot}."
                
            if rent_fee > 0:
                popup_data['type'] = "PayRent"
                popup_data['message'] += f"<br>Đất của <b>{space['owner']}</b>.<br>Tiền thuê: {rent_fee:,}<s>M</s>."
                return check_payment(session_id, player, rent_fee, space['owner'], f"Trả tiền thuê ô {space['name']} cho {space['owner']}", popup_data, is_double)
        else:
            popup_data['type'] = "OwnedBySelf"
            popup_data['message'] += f"<br>Đây là tài sản của bạn (hoặc đang cầm cố)."
            return True, popup_data
            
    elif action_type in ["IncomeTax", "SuperTax"]:
        tax = 1000000 if action_type == "SuperTax" else 2000000
        popup_data['type'] = "Tax"
        popup_data['message'] += f"<br>Nộp thuế {tax:,}<s>M</s>!"
        return check_payment(session_id, player, tax, "Ngân Hàng", f"Nộp thuế tại {space['name']}", popup_data, is_double)
        
    return True, popup_data

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('update_taken_colors', [p.color for p in game.players.values()])

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    global active_builders, was_paused_before_build
    if sid in game.players:
        player = game.players[sid]
        player.disconnected = True
        if sid in active_builders:
            active_builders.remove(sid)
            if sid in pending_build_actions:
                del pending_build_actions[sid]
            if len(active_builders) == 0:
                if not was_paused_before_build:
                    game.is_paused = False
                    game.pause_reason = ""
                    game.last_timer_update = time.time()
                else:
                    game.pause_reason = "Đã tạm dừng"
        
        if getattr(game, 'is_initial_rolling', False):
            if sid in game.players_to_roll:
                game.players_to_roll.remove(sid)
            if sid in game.initial_roll_history:
                del game.initial_roll_history[sid]
            check_initial_roll_completion()
            broadcast_game_state()
        elif game.game_started:
            if not getattr(player, 'is_bankrupt', False):
                remove_bankrupt_player(sid, "Ngân Hàng", "Mất kết nối")
        else:
            game.remove_player(sid)
            host_sid = list(game.players.keys())[0] if game.players else None
            player_list = [{'id': s, 'name': p.name, 'color': p.color, 'is_ready': getattr(p, 'is_ready', False)} for s, p in game.players.items()]
            socketio.emit('player_list_updated', {'players': player_list, 'host_sid': host_sid, 'settings': game.settings})
        
        broadcast_taken_colors()

@socketio.on('leave_lobby')
def handle_leave_lobby():
    sid = request.sid
    if sid in game.players and not game.game_started:
        game.remove_player(sid)
        host_sid = list(game.players.keys())[0] if game.players else None
        player_list = [{'id': s, 'name': p.name, 'color': p.color, 'is_ready': getattr(p, 'is_ready', False)} for s, p in game.players.items()]
        socketio.emit('player_list_updated', {'players': player_list, 'host_sid': host_sid, 'settings': game.settings})
        broadcast_taken_colors()

@socketio.on('toggle_ready')
def handle_toggle_ready():
    sid = request.sid
    if sid in game.players and not game.game_started:
        player = game.players[sid]
        player.is_ready = not getattr(player, 'is_ready', False)
        host_sid = list(game.players.keys())[0] if game.players else None
        player_list = [{'id': s, 'name': p.name, 'color': p.color, 'is_ready': getattr(p, 'is_ready', False)} for s, p in game.players.items()]
        socketio.emit('player_list_updated', {'players': player_list, 'host_sid': host_sid, 'settings': game.settings})

@socketio.on('request_full_state')
def handle_request_full_state():
    if game.game_started:
        broadcast_game_state()

@socketio.on('join_room')
def handle_join_room(data):
    session_id = request.sid
    success, message = game.add_player(session_id, data.get('name'), data.get('color'))
    if success:
        emit('room_joined', {'status': 'success'})
        host_sid = list(game.players.keys())[0] if game.players else None
        player_list = [{'id': s, 'name': p.name, 'color': p.color, 'is_ready': getattr(p, 'is_ready', False)} for s, p in game.players.items()]
        socketio.emit('player_list_updated', {'players': player_list, 'host_sid': host_sid, 'settings': game.settings})
        broadcast_taken_colors()
    else:
        emit('room_joined', {'status': 'error', 'msg': message})

@socketio.on('update_settings')
def handle_update_settings(data):
    if game.players and request.sid == list(game.players.keys())[0]:
        game.settings['game_duration'] = int(data.get('game_duration', 30))
        game.settings['special_dice'] = bool(data.get('special_dice', True))
        game.settings['unlimited_time'] = bool(data.get('unlimited_time', False))
        socketio.emit('settings_updated', game.settings)

@socketio.on('start_game')
def handle_start_game():
    if game.players and request.sid == list(game.players.keys())[0]:
        if len(game.players) < 2:
            return
        
        host_sid = request.sid
        for sid, p in game.players.items():
            if sid != host_sid and not getattr(p, 'is_ready', False):
                return
                
        reset_server_states()
        game.game_started = True
        game.is_paused = True
        game.pause_reason = "Đang phân định lượt đi..."
        game.is_initial_rolling = True
        game.initial_roll_history = {sid: [] for sid in game.players}
        game.players_to_roll = list(game.players.keys())
        
        socketio.emit('game_started')
        for sid, p in game.players.items():
            socketio.emit('move_token', {'player_id': sid, 'position': p.position, 'color': p.color})
        broadcast_game_state("🎲 Bắt đầu tung xúc xắc phân định thứ tự lượt đi!")

@socketio.on('surrender_game')
def handle_surrender_game():
    sid = request.sid
    if sid in game.players and game.game_started:
        if getattr(game, 'is_initial_rolling', False):
            if sid in game.players_to_roll:
                game.players_to_roll.remove(sid)
            if sid in game.initial_roll_history:
                del game.initial_roll_history[sid]
            check_initial_roll_completion()
        
        current_p = game.get_current_player()
        remove_bankrupt_player(sid, "Ngân Hàng", "Bỏ cuộc (Nhận thua)")
        if current_p and current_p.id == sid and not getattr(game, 'is_initial_rolling', False):
            end_turn_logic(sid, False)

@socketio.on('stop_game')
def handle_stop_game():
    if game.players and request.sid == list(game.players.keys())[0]:
        trigger_end_game("Host đã kết thúc ván đấu! Đang tổng kết bảng xếp hạng...")

@socketio.on('pay_jail_fine')
def handle_pay_jail_fine():
    session_id = request.sid
    current_player = game.get_current_player()
    if not current_player or current_player.id != session_id:
        return
        
    player = game.players[session_id]
    if player.position == 10 and session_id in player_jail_turns:
        success, _ = check_payment(session_id, player, 500000, "Ngân Hàng", "Nộp phạt 500,000M để thoát tù", {'type': 'JailFineManual'}, False)
        if success:
            player_jail_turns.pop(session_id, None)
            player.in_jail = False
            socketio.emit('server_message', {'msg': f"⚖️ {player.name} đã nộp phạt 500,000<s>M</s> để ra tù và sẵn sàng tung xúc xắc!"})
            broadcast_game_state()
            socketio.emit('unlock_roll_after_jail_exit', room=session_id)

@socketio.on('use_jail_card')
def handle_use_jail_card():
    session_id = request.sid
    current_player = game.get_current_player()
    if not current_player or current_player.id != session_id:
        return
        
    player = game.players[session_id]
    if player.position == 10 and session_id in player_jail_turns and getattr(player, 'out_of_jail_free', 0) > 0:
        player.out_of_jail_free -= 1
        player_jail_turns.pop(session_id, None)
        player.in_jail = False
        socketio.emit('server_message', {'msg': f"🎟️ {player.name} dùng Thẻ Ra Tù miễn phí và sẵn sàng tung xúc xắc!"})
        broadcast_game_state()
        socketio.emit('unlock_roll_after_jail_exit', room=session_id)

@socketio.on('toggle_pause')
def handle_toggle_pause():
    if getattr(game, 'is_initial_rolling', False): return
    session_id = request.sid
    if session_id in game.players:
        player = game.players[session_id]
        if not game.is_paused:
            game.remaining_time = game.get_current_remaining_time()
            game.is_paused = True
            game.pause_reason = f"{player.name} đã tạm dừng trận đấu."
            broadcast_game_state(f"⏸️ Trận đấu bị tạm dừng bởi {player.name}.")
        else:
            game.is_paused = False
            game.last_timer_update = time.time()
            game.pause_reason = ""
            broadcast_game_state(f"▶️ Trận đấu được tiếp tục.")

@socketio.on('roll_dice')
def handle_roll_dice():
    if game.is_paused and not getattr(game, 'is_initial_rolling', False): return
    session_id = request.sid
    
    if getattr(game, 'is_initial_rolling', False):
        if session_id not in game.players_to_roll: return
        game.players_to_roll.remove(session_id) 
        
        player = game.players[session_id]
        die1, die2 = random.randint(1, 6), random.randint(1, 6)
        total = die1 + die2
        
        socketio.emit('show_dice_roll', {'die1': die1, 'die2': die2, 'special_die': None})
        socketio.sleep(1.8)
        
        if session_id not in game.initial_roll_history:
            game.initial_roll_history[session_id] = []
        game.initial_roll_history[session_id].append(total)
        
        socketio.emit('server_message', {'msg': f"🎲 {player.name} tung được [{die1}] và [{die2}] (Tổng: {total})."})
        check_initial_roll_completion()
        broadcast_game_state()
        return

    current_player = game.get_current_player()
    if not current_player or current_player.id != session_id: return
    
    player = game.players[session_id]
    if getattr(player, 'has_rolled', False): return
    player.has_rolled = True
    
    die1, die2 = random.randint(1, 6), random.randint(1, 6)
    is_double = (die1 == die2)
    special_die = None
    
    if game.settings.get('special_dice', True) and getattr(player, 'passed_go', False):
        special_die = random.choice([1, 2, 3, 'Bus', 'Bus', 'Mr.Monopoly'])
    
    socketio.emit('show_dice_roll', {'die1': die1, 'die2': die2, 'special_die': special_die})
    socketio.sleep(1.8)

    socketio.emit('server_message', {'msg': f"🎲 {player.name} tung: [{die1}] và [{die2}]{f' (Đặc biệt: {special_die})' if special_die else ''}."})
    
    total = die1 + die2
    if isinstance(special_die, int):
        total += special_die
        
    if session_id not in player_doubles_count:
        player_doubles_count[session_id] = 0
        
    jail_msg = ""
    success = False
    popup_data = None

    if player.position == 10 and getattr(player, 'out_of_jail_free', 0) > 0 and session_id in player_jail_turns:
        player.out_of_jail_free -= 1
        player_jail_turns.pop(session_id, None)
        player.in_jail = False
        jail_msg = " 🎟️ Dùng Thẻ Ra Tù!<br>"
        socketio.emit('server_message', {'msg': f"🎟️ {player.name} dùng Thẻ Ra Tù."})

    if player.position == 10 and session_id in player_jail_turns:
        player_jail_turns[session_id] += 1
        actually_rolled_double = is_double
        is_double = False 
        
        if actually_rolled_double:
            player_jail_turns.pop(session_id, None)
            player.in_jail = False
            player_doubles_count[session_id] = 0
            jail_msg += f" 🎉 Đổ đôi thoát Tù!"
            socketio.emit('server_message', {'msg': f"🎉 {player.name} đổ ra đôi và thoát tù (Mất lượt đi tiếp)!"})
            
            if special_die == 'Bus':
                total = die1 + die2
                
            old_position = player.position
            player.position = (player.position + total) % 40
            
            if player.position < old_position:
                player.passed_go = True
                player.balance += 2000000
                socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})
                
            success, popup_data = process_space(session_id, player, player.position, is_double=False, dice_total=die1+die2)
            broadcast_game_state()
            
            if getattr(player, 'is_bankrupt', False):
                end_turn_logic(session_id, False)
            elif success and popup_data:
                socketio.emit('show_action_popup', {'die1': die1, 'die2': die2, 'total': total, 'special': special_die, 'jail_msg': jail_msg, 'popup': popup_data, 'is_double': False}, room=session_id)
                
        elif player_jail_turns[session_id] >= 3:
            player_jail_turns.pop(session_id, None)
            player.in_jail = False
            success, _ = check_payment(session_id, player, 500000, "Ngân Hàng", "Nộp phạt 500,000M để thoát tù (Bắt buộc ở lượt 3)", {'type': 'JailFineMove', 'die1': die1, 'die2': die2, 'special': special_die}, False)
            
            if success:
                if special_die == 'Bus':
                    total = die1 + die2
                old_position = player.position
                player.position = (player.position + total) % 40
                
                if player.position < old_position:
                    player.passed_go = True
                    player.balance += 2000000
                    socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})
                    
                jail_msg += f" ⚖️ Nộp phạt 500k ra Tù!"
                socketio.emit('server_message', {'msg': f"⚖️ {player.name} đã nộp phạt 500,000<s>M</s> để ra tù."})
                
                success_space, popup_data_space = process_space(session_id, player, player.position, is_double=False, dice_total=die1+die2)
                broadcast_game_state()
                
                if getattr(player, 'is_bankrupt', False):
                    end_turn_logic(session_id, False)
                elif success_space and popup_data_space:
                    socketio.emit('show_action_popup', {'die1': die1, 'die2': die2, 'total': total, 'special': special_die, 'jail_msg': jail_msg, 'popup': popup_data_space, 'is_double': False}, room=session_id)
            else:
                return 
        else:
            socketio.emit('show_action_popup', {'die1': die1, 'die2': die2, 'total': 0, 'special': special_die, 'jail_msg': f"🔒 Lượt {player_jail_turns[session_id]}/3.", 'popup': {'type': 'Event', 'title': 'Trong Tù', 'message': 'Chưa ra đôi (Mất lượt).'}, 'is_double': False}, room=session_id)
            socketio.emit('move_token', {'player_id': session_id, 'position': player.position, 'color': player.color})
            return

    else:
        if is_double:
            player_doubles_count[session_id] += 1
            if player_doubles_count[session_id] >= 3:
                player.position = 10
                player.in_jail = True
                player_jail_turns[session_id] = 0
                player_doubles_count[session_id] = 0
                player.pending_mr_m = False
                socketio.emit('server_message', {'msg': f"🚨 {player.name} đổ đôi 3 lần liên tiếp và vào Tù!"})
                socketio.emit('show_action_popup', {'die1': die1, 'die2': die2, 'total': total, 'special': special_die, 'jail_msg': "🚨 Vào Tù do đổ đôi quá tốc độ!", 'popup': {'type': 'Event', 'title': 'Vào Tù', 'message': 'Mất lượt.'}, 'is_double': False}, room=session_id)
                broadcast_game_state()
                return
        else:
            player_doubles_count[session_id] = 0

        if special_die == 'Bus':
            pos1 = (player.position + die1) % 40
            pos2 = (player.position + die2) % 40
            pos3 = (player.position + die1 + die2) % 40
            
            def peek_name(pid):
                sp = game.board[pid]
                if sp['type'] in ['Property', 'Railroad', 'Utility']:
                    return f"{sp['name']} (Trống)" if sp['owner'] is None else (f"{sp['name']} (Bạn)" if sp['owner'] == player.name else f"{sp['name']} ({sp['owner']})")
                return sp['name']
                
            socketio.emit('show_bus_menu', {'die1': die1, 'die2': die2, 'p1': peek_name(pos1), 'p2': peek_name(pos2), 'p3': peek_name(pos3), 'is_double': is_double}, room=session_id)
            return

        player.pending_mr_m = (special_die == 'Mr.Monopoly')
        old_position = player.position
        player.position = (player.position + total) % 40
        socketio.emit('server_message', {'msg': f"🚶‍♂️ {player.name} di chuyển đến {game.board[player.position]['name']}."})
        
        if player.position < old_position:
            player.passed_go = True
            player.balance += 2000000
            socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})

        if player.position == 30: 
            player.position = 10
            player.in_jail = True
            player_jail_turns[session_id] = 0
            is_double = False
            player.pending_mr_m = False
            socketio.emit('server_message', {'msg': f"🚨 {player.name} bị cảnh sát bắt vào tù!"})
            popup_data = {'type': 'Event', 'title': 'Vào Tù', 'price': 0, 'space_id': 10, 'message': 'Kết thúc lượt lập tức!'}
            success = True
        else:
            success, popup_data = process_space(session_id, player, player.position, is_double=is_double, dice_total=die1+die2)
            if player.position == 10 and session_id in player_jail_turns:
                is_double = False
                player.pending_mr_m = False 

    broadcast_game_state()
    if getattr(player, 'is_bankrupt', False):
        end_turn_logic(session_id, False)
    elif success and popup_data:
        socketio.emit('show_action_popup', {'die1': die1, 'die2': die2, 'total': total, 'special': special_die, 'jail_msg': jail_msg, 'popup': popup_data, 'is_double': is_double}, room=session_id)

@socketio.on('bus_choice')
def handle_bus_choice(data):
    session_id = request.sid
    player = game.players[session_id]
    choice = data['choice']
    die1 = data['die1']
    die2 = data['die2']
    is_double = data['is_double']
    
    total = die1 if choice == 1 else (die2 if choice == 2 else die1 + die2)
    old_position = player.position
    player.position = (player.position + total) % 40
    
    if player.position < old_position:
        player.passed_go = True
        player.balance += 2000000
        socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})
        
    success, popup_data = process_space(session_id, player, player.position, is_double=is_double, dice_total=die1+die2)
    if player.position == 10 and session_id in player_jail_turns:
        is_double = False
        
    broadcast_game_state()
    
    if getattr(player, 'is_bankrupt', False):
        end_turn_logic(session_id, False)
    elif success and popup_data:
        socketio.emit('show_action_popup', {'die1': die1, 'die2': die2, 'total': total, 'special': 'Bus', 'jail_msg': "", 'popup': popup_data, 'is_double': is_double}, room=session_id)

@socketio.on('confirm_turn_end')
def handle_confirm_turn_end(data):
    session_id = request.sid
    current_player = game.get_current_player()
    if not current_player or current_player.id != session_id: return
    
    player = game.players[session_id]
    is_double = data.get('is_double', False)

    if getattr(player, 'pending_mr_m', False):
        player.pending_mr_m = False
        pos = player.position
        target_pos = None
        
        for i in range(1, 41):
            check_pos = (pos + i) % 40
            space = game.board[check_pos]
            if space['type'] in ['Property', 'Railroad', 'Utility'] and space['owner'] is None:
                target_pos = check_pos
                break
                
        if target_pos is None:
            for i in range(1, 41):
                check_pos = (pos + i) % 40
                space = game.board[check_pos]
                if space['type'] in ['Property', 'Railroad', 'Utility'] and space['owner'] is not None and space['owner'] != player.name:
                    target_pos = check_pos
                    break
                    
        if target_pos is not None:
            old_pos_mr = player.position
            player.position = target_pos
            if target_pos < old_pos_mr:
                player.passed_go = True
                player.balance += 2000000
                socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})
                
            socketio.emit('server_message', {'msg': f"🎩 Mr. Monopoly đưa {player.name} đến {game.board[player.position]['name']}!"})
            success, popup_data = process_space(session_id, player, player.position, is_double=is_double, dice_total=0)
            
            if player.position == 10 and session_id in player_jail_turns:
                is_double = False
                
            broadcast_game_state()
            if getattr(player, 'is_bankrupt', False):
                end_turn_logic(session_id, False)
            elif success and popup_data:
                socketio.emit('show_action_popup', {'die1': '-', 'die2': '-', 'total': 0, 'special': 'Mr.M Move', 'jail_msg': "", 'popup': popup_data, 'is_double': is_double}, room=session_id)
            return
            
    end_turn_logic(session_id, is_double)

def end_turn_logic(session_id, is_double):
    if session_id in game.players:
        game.players[session_id].has_rolled = False
    if not is_double:
        game.next_turn()
    else:
        if session_id in game.players:
            socketio.emit('server_message', {'msg': f"🎲 {game.players[session_id].name} đi tiếp do đổ đôi!"})
    broadcast_game_state()

@socketio.on('liquidate_action')
def handle_liquidate_action(data):
    session_id = request.sid
    if session_id not in pending_debts: return
    
    player = game.players[session_id]
    space = game.board[data['space_id']]
    action = data['action']
    debt_info = pending_debts[session_id]
    
    if 'actions' not in debt_info:
        debt_info['actions'] = []
        
    if action == 'sell_house' and space['owner'] == player.name:
        if space['hotel'] == 1:
            space['hotel'] = 0
            space['houses'] = 4
            player.balance += (space['house_price'] * 5) // 2
            game.global_hotels += 1
            game.global_houses -= 4
            debt_info['actions'].append({'type': 'sell_hotel', 'space_id': space['id']})
            socketio.emit('server_message', {'msg': f"📉 {player.name} bán Khách Sạn tại {space['name']}."})
        elif space['houses'] > 0 and game.can_sell_house(space['id']):
            space['houses'] -= 1
            player.balance += space['house_price'] // 2
            game.global_houses += 1
            debt_info['actions'].append({'type': 'sell_house', 'space_id': space['id']})
            socketio.emit('server_message', {'msg': f"📉 {player.name} bán Nhà tại {space['name']}."})
    elif action == 'mortgage' and space['owner'] == player.name and space['houses'] == 0 and space['hotel'] == 0 and not space['is_mortgaged']:
        space['is_mortgaged'] = True
        player.balance += space['mortgage']
        debt_info['actions'].append({'type': 'mortgage', 'space_id': space['id']})
        socketio.emit('server_message', {'msg': f"🏦 {player.name} cầm cố {space['name']}."})
        
    broadcast_game_state()
    send_liquidation_menu(session_id)

@socketio.on('undo_liquidation')
def handle_undo_liquidation():
    session_id = request.sid
    if session_id not in pending_debts: return
    debt_info = pending_debts[session_id]
    if 'actions' not in debt_info or not debt_info['actions']: return
    
    last_action = debt_info['actions'].pop()
    player = game.players[session_id]
    space = game.board[last_action['space_id']]
    
    if last_action['type'] == 'mortgage':
        space['is_mortgaged'] = False
        player.balance -= space['mortgage']
        socketio.emit('server_message', {'msg': f"🔄 {player.name} hủy cầm cố {space['name']}."})
    elif last_action['type'] == 'sell_house':
        space['houses'] += 1
        player.balance -= space['house_price'] // 2
        game.global_houses -= 1
        socketio.emit('server_message', {'msg': f"🔄 {player.name} hủy bán Nhà tại {space['name']}."})
    elif last_action['type'] == 'sell_hotel':
        space['hotel'] = 1
        space['houses'] = 0
        player.balance -= space['house_price'] // 2
        game.global_hotels -= 1
        game.global_houses += 4
        socketio.emit('server_message', {'msg': f"🔄 {player.name} hủy bán Khách Sạn tại {space['name']}."})
        
    broadcast_game_state()
    send_liquidation_menu(session_id)

@socketio.on('confirm_debt_paid')
def handle_confirm_debt():
    session_id = request.sid
    if session_id not in pending_debts: return
    player = game.players[session_id]
    debt = pending_debts[session_id]
    
    if player.balance >= debt['amount']:
        player.balance -= debt['amount']
        socketio.emit('server_message', {'msg': f"💸 {player.name} đã thanh toán khoản nợ {debt['amount']:,}<s>M</s>."})
        if debt['creditor'] and debt['creditor'] != "Ngân Hàng":
            creditor = next((p for p in game.players.values() if p.name == debt['creditor']), None)
            if creditor:
                creditor.balance += debt['amount']
                
        popup_data = debt['popup_data']
        is_double = debt['is_double']
        del pending_debts[session_id]
        socketio.emit('close_liquidation_menu', room=session_id)
        
        if popup_data and popup_data.get('type') == 'Inherit':
            socketio.emit('open_inherit_modal', {'properties': [{'id': s['id'], 'name': s['name'], 'unmortgage': s['unmortgage']} for s in popup_data['properties']], 'fee_paid': popup_data['fee_paid']}, room=session_id)
        elif popup_data and popup_data.get('type') == 'JailFineManual':
            player_jail_turns.pop(session_id, None)
            player.in_jail = False
            socketio.emit('server_message', {'msg': f"⚖️ {player.name} đã nộp phạt 500,000<s>M</s> (sau thanh lý) để ra tù."})
            broadcast_game_state()
            socketio.emit('unlock_roll_after_jail_exit', room=session_id)
        elif popup_data and popup_data.get('type') == 'JailFineMove':
            player_jail_turns.pop(session_id, None)
            player.in_jail = False
            die1 = popup_data['die1']
            die2 = popup_data['die2']
            special_die = popup_data['special']
            total = die1 + die2
            
            if special_die == 'Bus':
                pos1 = (player.position + die1) % 40
                pos2 = (player.position + die2) % 40
                pos3 = (player.position + die1 + die2) % 40
                def peek_name(pid):
                    sp = game.board[pid]
                    return f"{sp['name']} (Trống)" if sp['owner'] is None else (f"{sp['name']} (Bạn)" if sp['owner'] == player.name else f"{sp['name']} ({sp['owner']})")
                socketio.emit('show_bus_menu', {'die1': die1, 'die2': die2, 'p1': peek_name(pos1), 'p2': peek_name(pos2), 'p3': peek_name(pos3), 'is_double': False}, room=session_id)
                return
                
            if isinstance(special_die, int):
                total += special_die
                
            player.pending_mr_m = (special_die == 'Mr.Monopoly')
            old_position = player.position
            player.position = (player.position + total) % 40
            socketio.emit('server_message', {'msg': f"⚖️ {player.name} đã nộp phạt 500,000<s>M</s> (sau thanh lý) để ra tù."})
            socketio.emit('server_message', {'msg': f"🚶‍♂️ {player.name} di chuyển đến {game.board[player.position]['name']}."})
            
            if player.position < old_position:
                player.passed_go = True
                player.balance += 2000000
                socketio.emit('server_message', {'msg': f"💰 {player.name} đi qua GO, nhận 2,000,000<s>M</s>."})
                
            if player.position == 30: 
                player.position = 10
                player.in_jail = True
                player_jail_turns[session_id] = 0
                player.pending_mr_m = False
                socketio.emit('server_message', {'msg': f"🚨 {player.name} bị cảnh sát bắt vào tù!"})
                success_space = True
                popup_data_space = {'type': 'Event', 'title': 'Vào Tù', 'price': 0, 'space_id': 10, 'message': 'Kết thúc lượt lập tức!'}
            else:
                success_space, popup_data_space = process_space(session_id, player, player.position, is_double=False, dice_total=die1+die2)
                if player.position == 10 and session_id in player_jail_turns:
                    player.pending_mr_m = False 
                    
            broadcast_game_state()
            if getattr(player, 'is_bankrupt', False):
                end_turn_logic(session_id, False)
            elif success_space and popup_data_space:
                socketio.emit('show_action_popup', {'die1': die1, 'die2': die2, 'total': total, 'special': special_die, 'jail_msg': "", 'popup': popup_data_space, 'is_double': False}, room=session_id)
        elif popup_data:
            socketio.emit('show_action_popup', {'die1': '-', 'die2': '-', 'total': 0, 'special': '', 'jail_msg': "Đã thanh toán nợ!<br>", 'popup': popup_data, 'is_double': is_double}, room=session_id)
        else:
            end_turn_logic(session_id, is_double)

@socketio.on('resolve_inherit')
def handle_resolve_inherit(data):
    session_id = request.sid
    if session_id not in pending_bankrupt_inherit: return
    player = game.players[session_id]
    unmortgage_ids = data.get('unmortgage_ids', [])
    for space in pending_bankrupt_inherit[session_id]:
        if space['id'] in unmortgage_ids and player.balance >= space['unmortgage']:
            player.balance -= space['unmortgage']
            space['is_mortgaged'] = False
            socketio.emit('server_message', {'msg': f"📜 {player.name} đã chuộc lại {space['name']}."})
    del pending_bankrupt_inherit[session_id]
    broadcast_game_state()

@socketio.on('buy_property')
def handle_buy_property(data):
    session_id = request.sid
    player = game.players[session_id]
    space = game.board[data.get('space_id')]
    if space['owner'] is None and player.balance >= space['price']:
        player.balance -= space['price']
        space['owner'] = player.name
        socketio.emit('server_message', {'msg': f"🏠 {player.name} đã chi {space['price']:,}<s>M</s> để mua {space['name']}."})
        broadcast_game_state()
    end_turn_logic(session_id, data.get('is_double', False))

def auction_timer_thread(version, phase):
    count = 15 if phase == 'blind' else 10
    while count > 0:
        socketio.sleep(1)
        if active_auction['space_id'] is None or active_auction['version'] != version or active_auction['phase'] != phase: return 
        if game.is_paused and not getattr(game, 'is_initial_rolling', False): continue
        count -= 1
        socketio.emit('update_auction_timer', {'time': count, 'phase': phase})
        
    if active_auction['space_id'] is not None and active_auction['version'] == version and active_auction['phase'] == phase:
        if phase == 'voting':
            resolve_auction_vote()
        elif phase == 'normal':
            socketio.emit('server_message', {'msg': "⏳ Hết thời gian đấu giá!"})
            handle_close_auction_internal()
        elif phase == 'blind':
            socketio.emit('server_message', {'msg': "⏳ Hết thời gian đấu giá mù!"})
            for sid in active_auction['active_bidders']:
                if sid not in active_auction['blind_bids']:
                    active_auction['blind_bids'][sid] = {'amount': 0, 'time': time.time()}
            resolve_blind_auction()

@socketio.on('start_auction')
def handle_start_auction(data):
    initiator_sid = request.sid
    space = game.board[data.get('space_id')]
    active_auction.update({
        'space_id': data.get('space_id'),
        'initiator_sid': initiator_sid,
        'is_double': data.get('is_double', False),
        'current_bid': 100000,
        'highest_bidder_sid': None,
        'highest_bidder_name': "Chưa có",
        'active_bidders': [sid for sid, p in game.players.items() if not getattr(p, 'is_bankrupt', False) and not getattr(p, 'disconnected', False)],
        'version': active_auction['version'] + 1,
        'phase': 'voting',
        'votes': {},
        'blind_bids': {}
    })
    socketio.emit('open_auction_vote_popup', {'space_name': space['name'], 'time': 10})
    socketio.emit('server_message', {'msg': f"📢 {space['name']} được đưa lên đấu giá. Đang biểu quyết..."})
    socketio.start_background_task(auction_timer_thread, active_auction['version'], 'voting')

@socketio.on('submit_auction_vote')
def handle_auction_vote(data):
    sid = request.sid
    if active_auction['phase'] != 'voting' or sid not in active_auction['active_bidders']: return
    vote = data.get('vote')
    if vote in ['normal', 'blind']:
        active_auction['votes'][sid] = vote
    if len(active_auction['votes']) == len(active_auction['active_bidders']):
        resolve_auction_vote()

def resolve_auction_vote():
    if active_auction['phase'] != 'voting': return
    active_auction['version'] += 1 
    normal_votes = sum(1 for v in active_auction['votes'].values() if v == 'normal')
    blind_votes = sum(1 for v in active_auction['votes'].values() if v == 'blind')
    chosen_phase = 'normal' if normal_votes > blind_votes else ('blind' if blind_votes > normal_votes else random.choice(['normal', 'blind']))
    
    active_auction['phase'] = chosen_phase
    active_auction['start_time'] = time.time()
    space = game.board[active_auction['space_id']]
    
    if chosen_phase == 'normal':
        socketio.emit('server_message', {'msg': f"⚖️ Kết quả biểu quyết: <b>ĐẤU GIÁ THƯỜNG</b>."})
        socketio.emit('start_actual_auction', {'phase': 'normal', 'space_name': space['name'], 'current_bid': 100000, 'highest_bidder': "Chưa có", 'active_bidders': active_auction['active_bidders'], 'time': 10})
    else:
        socketio.emit('server_message', {'msg': f"⚖️ Kết quả biểu quyết: <b>ĐẤU GIÁ MÙ</b>."})
        socketio.emit('start_actual_auction', {'phase': 'blind', 'space_name': space['name'], 'active_bidders': active_auction['active_bidders'], 'time': 15})
        
    socketio.start_background_task(auction_timer_thread, active_auction['version'], chosen_phase)

@socketio.on('place_bid')
def handle_place_bid(data):
    session_id = request.sid
    if active_auction['phase'] != 'normal' or session_id not in active_auction['active_bidders']: return
    player = game.players[session_id]
    
    if 'exact_bid' in data:
        new_bid = int(data['exact_bid'])
        if new_bid < active_auction['current_bid'] + 10000:
            socketio.emit('server_message', {'msg': f"❌ Giá đưa ra ({new_bid:,}<s>M</s>) không hợp lệ! Phải cao hơn giá hiện tại tối thiểu 10,000<s>M</s>."}, room=session_id)
            return
    else:
        new_bid = active_auction['current_bid'] + int(data.get('increment', 10000))
        
    if player.balance >= new_bid:
        active_auction['current_bid'] = new_bid
        active_auction['highest_bidder_sid'] = session_id
        active_auction['highest_bidder_name'] = player.name
        active_auction['version'] += 1
        socketio.emit('server_message', {'msg': f"📢 {player.name} đã nâng giá lên {new_bid:,}<s>M</s>!"})
        socketio.emit('update_auction_ui', {'current_bid': new_bid, 'highest_bidder': player.name, 'time': 10})
        socketio.start_background_task(auction_timer_thread, active_auction['version'], 'normal')
    else:
        socketio.emit('server_message', {'msg': f"❌ {player.name} không đủ tiền trả {new_bid:,}<s>M</s>!"}, room=session_id)

@socketio.on('submit_blind_bid')
def handle_blind_bid(data):
    sid = request.sid
    if active_auction['phase'] != 'blind' or sid not in active_auction['active_bidders'] or sid in active_auction['blind_bids']: return
    player = game.players[sid]
    
    try:
        amount = int(data.get('amount', 0))
    except:
        amount = 0
        
    if amount > player.balance:
        socketio.emit('server_message', {'msg': f"❌ Bạn không đủ tiền để ra giá {amount:,}<s>M</s>!"}, room=sid)
        socketio.emit('blind_bid_error', room=sid)
        return
        
    active_auction['blind_bids'][sid] = {'amount': amount, 'time': time.time()}
    socketio.emit('server_message', {'msg': f"✅ Đã chốt giá, đang chờ đối thủ..."}, room=sid)
    if len(active_auction['blind_bids']) == len(active_auction['active_bidders']):
        resolve_blind_auction()

def resolve_blind_auction():
    active_auction['version'] += 1
    valid_bids = {sid: b for sid, b in active_auction['blind_bids'].items() if b['amount'] > 0}
    
    if not valid_bids:
        socketio.emit('server_message', {'msg': f"⚠️ Hủy đấu giá do không ai ra giá."})
        socketio.emit('close_auction_popup')
        end_turn_logic(active_auction['initiator_sid'], active_auction['is_double'])
        active_auction['space_id'] = None
        return
        
    max_amount = max(b['amount'] for b in valid_bids.values())
    tied_sids = [sid for sid, b in valid_bids.items() if b['amount'] == max_amount]
    space = game.board[active_auction['space_id']]
    
    if len(tied_sids) == 1:
        winner = game.players[tied_sids[0]]
        winner.balance -= max_amount
        space['owner'] = winner.name
        socketio.emit('server_message', {'msg': f"🏆 {winner.name} thắng đấu giá mù {space['name']} với giá {max_amount:,}<s>M</s>!"})
    else:
        tied_sids.sort(key=lambda s: valid_bids[s]['time'])
        winner = game.players[tied_sids[0]]
        loser = game.players[tied_sids[1]]
        t1 = round(valid_bids[tied_sids[0]]['time'] - active_auction['start_time'], 2)
        t2 = round(valid_bids[tied_sids[1]]['time'] - active_auction['start_time'], 2)
        winner.balance -= max_amount
        space['owner'] = winner.name
        socketio.emit('server_message', {'msg': f"⚡ HÒA GIÁ {max_amount:,}<s>M</s>!<br>🏆 {winner.name} (Chốt lúc {t1}s) đã nhanh tay thắng {loser.name} ({t2}s)!"})
        
    broadcast_game_state()
    socketio.emit('close_auction_popup')
    end_turn_logic(active_auction['initiator_sid'], active_auction['is_double'])
    active_auction['space_id'] = None

@socketio.on('fold_auction')
def handle_fold_auction():
    sid = request.sid
    if sid not in active_auction['active_bidders']: return
    if active_auction['phase'] == 'normal':
        active_auction['active_bidders'].remove(sid)
        player_name = game.players[sid].name if sid in game.players else "Người chơi"
        socketio.emit('server_message', {'msg': f"🏳️ {player_name} đã bỏ cuộc khỏi đấu giá."})
        
        if len(active_auction['active_bidders']) == 1:
            winner_sid = active_auction['active_bidders'][0]
            active_auction['highest_bidder_sid'] = winner_sid
            if active_auction['highest_bidder_name'] == "Chưa có" and winner_sid in game.players:
                active_auction['highest_bidder_name'] = game.players[winner_sid].name
            active_auction['version'] += 1
            handle_close_auction_internal()
        elif len(active_auction['active_bidders']) == 0:
            active_auction['version'] += 1
            socketio.emit('server_message', {'msg': f"⚠️ Hủy đấu giá do tất cả đã bỏ cuộc."})
            socketio.emit('close_auction_popup')
            end_turn_logic(active_auction['initiator_sid'], active_auction['is_double'])
            active_auction['space_id'] = None
        else:
            socketio.emit('close_single_auction_modal', room=sid)
    elif active_auction['phase'] == 'blind':
        active_auction['blind_bids'][sid] = {'amount': 0, 'time': time.time()}
        socketio.emit('server_message', {'msg': f"🏳️ {game.players[sid].name} đã bỏ cuộc."}, room=sid)
        socketio.emit('close_single_auction_modal', room=sid)
        if len(active_auction['blind_bids']) == len(active_auction['active_bidders']):
            resolve_blind_auction()

def handle_close_auction_internal():
    winner_sid = active_auction['highest_bidder_sid']
    space_id = active_auction['space_id']
    
    if winner_sid and space_id is not None:
        winner = game.players.get(winner_sid)
        space = game.board[space_id]
        if winner and winner.balance >= active_auction['current_bid']:
            winner.balance -= active_auction['current_bid']
            space['owner'] = winner.name
            socketio.emit('server_message', {'msg': f"🏆 {winner.name} thắng đấu giá {space['name']} với giá {active_auction['current_bid']:,}<s>M</s>!"})
            broadcast_game_state()
        else:
            socketio.emit('server_message', {'msg': f"⚠️ Người thắng không đủ tiền trả giá đấu, hủy đấu giá."})
            
    socketio.emit('close_auction_popup')
    if active_auction['space_id'] is not None:
        end_turn_logic(active_auction['initiator_sid'], active_auction['is_double'])
    active_auction['space_id'] = None

def send_build_menu(session_id):
    player = game.players[session_id]
    eligible_spaces = []
    for space in game.board:
        if space['owner'] == player.name:
            s_copy = space.copy()
            s_copy['unmortgage_cost'] = int(space['mortgage'] * 1.1)
            if space['is_mortgaged']:
                s_copy['can_unmortgage'] = True
                s_copy['can_build_house'] = False
                s_copy['can_build_hotel'] = False
                eligible_spaces.append(s_copy)
            elif space['type'] == 'Property' and game.check_monopoly(player.name, space['color']):
                s_copy['can_unmortgage'] = False
                s_copy['can_build_house'] = game.can_build_structure(space['id'], 'house')
                s_copy['can_build_hotel'] = game.can_build_structure(space['id'], 'hotel')
                eligible_spaces.append(s_copy)
    socketio.emit('open_build_menu', {'spaces': eligible_spaces, 'global_houses': game.global_houses, 'global_hotels': game.global_hotels, 'can_undo': len(pending_build_actions.get(session_id, [])) > 0}, room=session_id)

@socketio.on('request_build_menu')
def handle_request_build_menu():
    session_id = request.sid
    global active_builders, was_paused_before_build
    if len(active_builders) == 0:
        was_paused_before_build = game.is_paused
        if not game.is_paused:
            game.remaining_time = game.get_current_remaining_time()
            game.is_paused = True
    active_builders.add(session_id)
    pending_build_actions[session_id] = []
    names = [game.players[sid].name for sid in active_builders if sid in game.players]
    game.pause_reason = f"Đang chờ quy hoạch: {', '.join(names)}"
    broadcast_game_state()
    send_build_menu(session_id)

@socketio.on('unmortgage_property')
def handle_unmortgage_property(data):
    session_id = request.sid
    player = game.players[session_id]
    space = game.board[data['space_id']]
    cost = int(space['mortgage'] * 1.1)
    
    if player.balance >= cost and space['is_mortgaged'] and space['owner'] == player.name:
        player.balance -= cost
        space['is_mortgaged'] = False
        pending_build_actions.setdefault(session_id, []).append({'type': 'unmortgage', 'space_id': space['id'], 'cost': cost})
        socketio.emit('server_message', {'msg': f"📜 {player.name} đã chuộc lại {space['name']} với giá {cost:,}<s>M</s>."})
        broadcast_game_state()
        send_build_menu(session_id)

@socketio.on('buy_building')
def handle_buy_building(data):
    session_id = request.sid
    player = game.players[session_id]
    space = game.board[data['space_id']]
    cost = space['house_price'] * 5 if data['type'] == 'hotel' else space['house_price']
    
    if player.balance >= cost:
        if data['type'] == 'house' and space['houses'] < 4 and game.global_houses > 0 and game.can_build_structure(space['id'], 'house'):
            player.balance -= cost
            space['houses'] += 1
            game.global_houses -= 1
            pending_build_actions.setdefault(session_id, []).append({'type': 'house', 'space_id': space['id'], 'cost': cost})
            socketio.emit('server_message', {'msg': f"🏗️ {player.name} xây 1 Nhà tại {space['name']}."})
            broadcast_game_state()
            send_build_menu(session_id)
        elif data['type'] == 'hotel' and space['houses'] == 4 and game.global_hotels > 0 and game.can_build_structure(space['id'], 'hotel'):
            player.balance -= cost
            space['houses'] = 0
            space['hotel'] = 1
            game.global_houses += 4
            game.global_hotels -= 1
            pending_build_actions.setdefault(session_id, []).append({'type': 'hotel', 'space_id': space['id'], 'cost': cost})
            socketio.emit('server_message', {'msg': f"🏨 {player.name} lên Khách Sạn tại {space['name']}!"})
            broadcast_game_state()
            send_build_menu(session_id)

@socketio.on('undo_build_action')
def handle_undo_build_action():
    session_id = request.sid
    if session_id not in pending_build_actions or not pending_build_actions[session_id]: return
    
    last_action = pending_build_actions[session_id].pop()
    player = game.players[session_id]
    space = game.board[last_action['space_id']]
    
    if last_action['type'] == 'house':
        space['houses'] -= 1
        game.global_houses += 1
        player.balance += last_action['cost']
        socketio.emit('server_message', {'msg': f"🔄 {player.name} hoàn tác xây Nhà tại {space['name']}."})
    elif last_action['type'] == 'hotel':
        space['hotel'] = 0
        space['houses'] = 4
        game.global_hotels += 1
        game.global_houses -= 4
        player.balance += last_action['cost']
        socketio.emit('server_message', {'msg': f"🔄 {player.name} hoàn tác lên Khách Sạn tại {space['name']}."})
    elif last_action['type'] == 'unmortgage':
        space['is_mortgaged'] = True
        player.balance += last_action['cost']
        socketio.emit('server_message', {'msg': f"🔄 {player.name} hoàn tác chuộc {space['name']}."})
        
    broadcast_game_state()
    send_build_menu(session_id)

@socketio.on('close_build_menu')
def handle_close_build_menu():
    session_id = request.sid
    global active_builders, was_paused_before_build
    if session_id in active_builders:
        active_builders.remove(session_id)
        if session_id in pending_build_actions:
            del pending_build_actions[session_id]
        if len(active_builders) == 0:
            if not was_paused_before_build:
                game.is_paused = False
                game.pause_reason = ""
                game.last_timer_update = time.time()
            else:
                game.pause_reason = "Đã tạm dừng"
        else:
            names = [game.players[sid].name for sid in active_builders if sid in game.players]
            game.pause_reason = f"Đang chờ quy hoạch: {', '.join(names)}"
        broadcast_game_state()

@socketio.on('request_trade_players')
def handle_request_trade_players():
    session_id = request.sid
    if game.is_paused:
        socketio.emit('server_message', {'msg': "⚠️ Không thể khởi tạo trao đổi lúc này!"}, room=session_id)
        return
    other_players = [{'id': sid, 'name': p.name} for sid, p in game.players.items() if sid != session_id and not getattr(p, 'is_bankrupt', False)]
    socketio.emit('show_trade_player_select', {'players': other_players}, room=session_id)

@socketio.on('initiate_trade')
def handle_initiate_trade(data):
    global current_trade
    session_id = request.sid
    target_sid = data.get('target_sid')
    if target_sid not in game.players: return
    
    p1 = game.players[session_id]
    p2 = game.players[target_sid]
    was_paused = game.is_paused
    
    if not game.is_paused:
        game.remaining_time = game.get_current_remaining_time()
        game.is_paused = True
        
    game.pause_reason = f"{p1.name} đang đàm phán trực tiếp với {p2.name}."
    broadcast_game_state(f"🤝 Bàn đàm phán mở giữa {p1.name} và {p2.name}.")
    
    current_trade = {
        'p1_sid': session_id, 'p2_sid': target_sid, 'p1_name': p1.name, 'p2_name': p2.name,
        'p1_props': [], 'p2_props': [], 'p1_money': 0, 'p2_money': 0, 'p1_locked': False, 'p2_locked': False, 'was_paused': was_paused
    }
    
    p1_inventory = game.get_tradable_properties(p1.name)
    p2_inventory = game.get_tradable_properties(p2.name)
    
    for sid in [session_id, target_sid]:
        socketio.emit('open_live_trade', {'p1_sid': session_id, 'p2_sid': target_sid, 'p1_name': p1.name, 'p2_name': p2.name, 'p1_inventory': p1_inventory, 'p2_inventory': p2_inventory}, room=sid)

@socketio.on('live_trade_update')
def handle_live_trade_update(data):
    global current_trade
    if not current_trade: return
    role = data.get('role')
    if role not in ['p1', 'p2']: return
    
    current_trade[f"{role}_props"] = data.get('props', [])
    current_trade[f"{role}_money"] = data.get('money', 0)
    current_trade[f"{role}_locked"] = data.get('locked', False)
    
    other_role = 'p2' if role == 'p1' else 'p1'
    if not current_trade[f"{role}_locked"]:
        current_trade[f"{other_role}_locked"] = False
        
    state = {
        'p1_props': current_trade['p1_props'], 'p2_props': current_trade['p2_props'],
        'p1_money': current_trade['p1_money'], 'p2_money': current_trade['p2_money'],
        'p1_locked': current_trade['p1_locked'], 'p2_locked': current_trade['p2_locked']
    }
    
    socketio.emit('sync_live_trade', state, room=current_trade['p1_sid'])
    socketio.emit('sync_live_trade', state, room=current_trade['p2_sid'])
    
    if current_trade['p1_locked'] and current_trade['p2_locked']:
        execute_trade()

def execute_trade():
    global current_trade
    if not current_trade: return
    
    p1 = game.players.get(current_trade['p1_sid'])
    p2 = game.players.get(current_trade['p2_sid'])
    m1 = current_trade['p1_money']
    m2 = current_trade['p2_money']
    
    if p1.balance < m1 or p2.balance < m2:
        socketio.emit('server_message', {'msg': f"❌ Giao dịch thất bại: Không đủ tiền mặt."})
    else:
        p1.balance -= m1
        p2.balance += m1
        p2.balance -= m2
        p1.balance += m2
        for pid in current_trade['p1_props']:
            game.board[pid]['owner'] = p2.name
        for pid in current_trade['p2_props']:
            game.board[pid]['owner'] = p1.name
        socketio.emit('server_message', {'msg': f"✅ {p1.name} và {p2.name} đã hoàn tất trao đổi!"})
    
    socketio.emit('close_live_trade', room=current_trade['p1_sid'])
    socketio.emit('close_live_trade', room=current_trade['p2_sid'])
    
    was_paused = current_trade.get('was_paused', False)
    current_trade = None
    
    if not was_paused:
        game.is_paused = False
        game.pause_reason = ""
        game.last_timer_update = time.time()
    else:
        game.pause_reason = "Đã tạm dừng"
        
    broadcast_game_state()

@socketio.on('cancel_live_trade')
def handle_cancel_live_trade():
    global current_trade
    if not current_trade: return
    socketio.emit('server_message', {'msg': f"❌ Giao dịch đã bị hủy."})
    socketio.emit('close_live_trade', room=current_trade['p1_sid'])
    socketio.emit('close_live_trade', room=current_trade['p2_sid'])
    
    was_paused = current_trade.get('was_paused', False)
    current_trade = None
    
    if not was_paused:
        game.is_paused = False
        game.pause_reason = ""
        game.last_timer_update = time.time()
    else:
        game.pause_reason = "Đã tạm dừng"
        
    broadcast_game_state()

@socketio.on('time_out_reached')
def handle_time_out_reached():
    session_id = request.sid
    if game.players and session_id == list(game.players.keys())[0]:
        game.is_paused = True
        game.pause_reason = "Hết giờ! Đang chờ Host quyết định..."
        game.remaining_time = 0
        broadcast_game_state()
        emit('show_timeout_decision', room=session_id)

@socketio.on('add_extra_time')
def handle_add_extra_time(data):
    session_id = request.sid
    if game.players and session_id == list(game.players.keys())[0]:
        extra_minutes = int(data.get('minutes', 5))
        game.remaining_time += extra_minutes * 60
        game.is_paused = False
        game.pause_reason = ""
        game.last_timer_update = time.time()
        socketio.emit('server_message', {'msg': f"⏳ Host đã gia hạn thêm {extra_minutes} phút!"})
        broadcast_game_state()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)