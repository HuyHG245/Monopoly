class Space:
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']
        self.type = data['type']

class Property(Space):
    def __init__(self, data):
        super().__init__(data)
        self.color = data['color']
        self.base_price = data['base_price']
        self.house_cost = data['house_cost']
        self.rent_levels = data['rent_levels']
        
        self.owner = None
        self.houses = 0  # 0: Đất trống, 1-4: Nhà, 5: Khách sạn
        self.is_mortgaged = False

    def calculate_rent(self, owner_player):
        if self.is_mortgaged:
            return 0
            
        if self.houses > 0:
            return self.rent_levels[self.houses]
            
        # Nếu là đất trống, kiểm tra xem chủ đất có đủ bộ màu chưa
        base_rent = self.rent_levels[0]
        if owner_player.has_full_color_set(self.color):
            return base_rent * 2
            
        return base_rent

class Station(Space):
    def __init__(self, data):
        super().__init__(data)
        self.base_price = data['base_price']
        self.owner = None
        self.is_mortgaged = False

    def calculate_rent(self, station_count):
        if self.is_mortgaged:
            return 0
        # Tính tiền dựa trên số trạm sở hữu: 1 trạm=250k, 2 trạm=500k, 3 trạm=1M, 4 trạm=2M
        rents = {1: 250000, 2: 500000, 3: 1000000, 4: 2000000}
        return rents.get(station_count, 0)

class Utility(Space):
    def __init__(self, data):
        super().__init__(data)
        self.base_price = data['base_price']
        self.owner = None
        self.is_mortgaged = False

    def calculate_rent(self, utility_count, dice_roll):
        if self.is_mortgaged:
            return 0
        # 1 tiện ích x 40k, 2 tiện ích x 100k
        multiplier = 40000 if utility_count == 1 else 100000
        return dice_roll * multiplier

class Tax(Space):
    def __init__(self, data):
        super().__init__(data)
        self.tax_amount = data['tax_amount']