class Player:
    # Định nghĩa hằng số tổng số lượng đất của mỗi màu trên bàn cờ thực tế
    COLOR_SETS_TOTAL = {
        "Brown": 2, "LightBlue": 3, "Pink": 3, "Orange": 3,
        "Red": 3, "Yellow": 3, "Green": 3, "DarkBlue": 2
    }

    def __init__(self, player_id, name, color):
        self.id = player_id
        self.name = name
        self.color = color
        self.balance = 15000000  # Vốn khởi điểm 15 triệu
        self.position = 0        # Xuất phát ở ô GO (id 0)
        
        self.properties = []     # Chứa các đối tượng Property, Station, Utility
        
        # Trạng thái nhà tù
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_cards = 0
        
        # Trạng thái phá sản
        self.is_bankrupt = False

    def get_net_worth(self):
        """Tính tổng tài sản cuối game"""
        net_worth = self.balance
        for prop in self.properties:
            if prop.is_mortgaged:
                net_worth += prop.base_price * 0.5
            else:
                net_worth += prop.base_price
                if hasattr(prop, 'houses') and prop.houses > 0:
                    net_worth += prop.houses * prop.house_cost
        return int(net_worth)

    def has_full_color_set(self, color):
        """Kiểm tra xem người chơi đã gom đủ bộ màu chưa"""
        count = sum(1 for p in self.properties if getattr(p, 'color', '') == color)
        return count == self.COLOR_SETS_TOTAL.get(color, 99)

    def get_station_count(self):
        return sum(1 for p in self.properties if p.type == 'station')

    def get_utility_count(self):
        return sum(1 for p in self.properties if p.type == 'utility')