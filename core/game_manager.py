import json
import os
import time

class GameManager:
    def __init__(self):
        self.players = {}          
        self.player_order = []     
        self.game_started = False  
        self.current_turn_index = 0 
        self.settings = {'game_duration': 30, 'special_dice': True, 'unlimited_time': False}
        
        self.global_houses = 32
        self.global_hotels = 12
        
        self.is_paused = False
        self.pause_reason = ""
        self.remaining_time = 0
        self.last_timer_update = 0
        
        self.eliminated_players = []
        
        # Hệ thống phân định lượt
        self.is_initial_rolling = False
        self.initial_roll_history = {}
        self.players_to_roll = []
        
        self.board = self.init_board() 

    def init_board(self):
        board_path = os.path.join('data', 'board_data.json')
        if os.path.exists(board_path):
            try:
                with open(board_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    formatted_board = []
                    for space in data:
                        formatted_board.append({
                            'id': space.get('id', 0),
                            'name': space.get('name', ''),
                            'type': space.get('type', 'Standard'),
                            'price': space.get('price', 0),
                            'rent': space.get('rent', 0),
                            'rent_levels': space.get('rent_levels', []),
                            'color': space.get('color', None),
                            'house_price': space.get('house_price', 0),
                            'mortgage': space.get('mortgage', 0),
                            'unmortgage': space.get('unmortgage', 0),
                            'houses': 0,
                            'hotel': 0,
                            'owner': None,
                            'is_mortgaged': False
                        })
                    return formatted_board
            except Exception as e:
                print(f"Lỗi tải board_data.json: {e}")

        board = []
        for i in range(40):
            board.append({
                'id': i, 'name': f"Ô số {i}", 'type': "Standard", 'price': 0, 
                'rent': 0, 'rent_levels': [], 'color': None, 'house_price': 0,
                'mortgage': 0, 'unmortgage': 0, 'houses': 0, 'hotel': 0, 'owner': None, 'is_mortgaged': False
            })
        return board

    def add_player(self, session_id, name, color):
        if self.game_started: return False, "Trận đấu đã bắt đầu."
        if len(self.players) >= 6: return False, "Phòng đã đầy."
        for p in self.players.values():
            if p.name == name: return False, "Trùng tên nhân vật."
            if p.color == color: return False, "Màu này đã được chọn."

        from models.player import Player
        new_player = Player(session_id, name, color)
        new_player.passed_go = False 
        new_player.pending_mr_m = False
        new_player.is_bankrupt = False
        new_player.disconnected = False
        new_player.is_ready = False # Trạng thái phòng chờ
        
        self.players[session_id] = new_player
        self.player_order.append(session_id)
        return True, f"Chào mừng {name}!"

    def remove_player(self, session_id):
        if session_id in self.players:
            del self.players[session_id]
            if session_id in self.player_order:
                self.player_order.remove(session_id)
            if len(self.players) == 0:
                self.reset_game()
            return True
        return False

    def get_current_player(self):
        if not self.player_order: return None
        if self.current_turn_index >= len(self.player_order):
            self.current_turn_index = 0
        return self.players.get(self.player_order[self.current_turn_index])

    def next_turn(self):
        if not self.player_order: return
        self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)
        loop_guard = 0
        current_p = self.get_current_player()
        while current_p and getattr(current_p, 'is_bankrupt', False) and loop_guard < len(self.player_order):
            self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)
            current_p = self.get_current_player()
            loop_guard += 1

    def check_monopoly(self, player_name, color):
        if not color: return False
        color_group = [s for s in self.board if s['color'] == color]
        return all(s['owner'] == player_name for s in color_group)

    def get_total_assets_value(self, player_name):
        player = next((p for p in self.players.values() if p.name == player_name), None)
        if not player or getattr(player, 'is_bankrupt', False): return 0
        total = player.balance
        for space in self.board:
            if space['owner'] == player_name:
                if not space['is_mortgaged']:
                    total += space['mortgage']
                total += space['houses'] * (space['house_price'] // 2)
                if space['hotel'] == 1:
                    total += (space['house_price'] * 5) // 2
        return total

    def can_sell_house(self, space_id):
        space = self.board[space_id]
        if space['hotel'] == 0 and space['houses'] == 0: return False
        color_group = [s for s in self.board if s['color'] == space['color']]
        current_level = 5 if space['hotel'] == 1 else space['houses']
        
        for s in color_group:
            s_level = 5 if s['hotel'] == 1 else s['houses']
            if s_level > current_level:
                return False 
        return True

    def can_build_structure(self, space_id, target_type):
        space = self.board[space_id]
        if space['owner'] is None: return False
        color_group = [s for s in self.board if s['color'] == space['color']]
        if any(s['is_mortgaged'] for s in color_group): return False

        current_level = 5 if space['hotel'] == 1 else space['houses']
        next_level = current_level + 1
        
        if target_type == 'hotel' and current_level != 4: return False
        if target_type == 'house' and current_level >= 4: return False

        for s in color_group:
            s_level = 5 if s['hotel'] == 1 else s['houses']
            if next_level > s_level + 1:
                return False
        return True

    def get_tradable_properties(self, player_name):
        tradable = []
        for space in self.board:
            if space['owner'] == player_name and space['houses'] == 0 and space['hotel'] == 0:
                tradable.append({
                    'id': space['id'], 'name': space['name'], 'color': space['color'],
                    'price': space['price'], 'is_mortgaged': space['is_mortgaged']
                })
        return tradable

    def reset_game(self):
        self.game_started = False
        self.current_turn_index = 0
        self.is_paused = False
        self.pause_reason = ""
        self.global_houses = 32
        self.global_hotels = 12
        self.eliminated_players = []
        
        self.is_initial_rolling = False
        self.initial_roll_history = {}
        self.players_to_roll = []
        
        if self.settings.get('unlimited_time', False):
            self.remaining_time = -1
        else:
            self.remaining_time = self.settings.get('game_duration', 30) * 60
        self.last_timer_update = time.time()
        
        for p in self.players.values():
            p.position = 0; p.balance = 15000000; p.out_of_jail_free = 0
            p.passed_go = False; p.pending_mr_m = False
            p.is_bankrupt = False; p.disconnected = False
            p.is_ready = False
            
        for space in self.board:
            space['owner'] = None; space['houses'] = 0; space['hotel'] = 0; space['is_mortgaged'] = False
            
    def get_current_remaining_time(self):
        if not self.game_started: return 0
        if self.settings.get('unlimited_time', False): return -1
        if self.is_paused:
            return self.remaining_time
        else:
            elapsed = time.time() - self.last_timer_update
            return max(0, self.remaining_time - elapsed)