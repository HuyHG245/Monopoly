class AuctionSystem:
    def __init__(self):
        self.active_auction = None

    def start_auction(self, property_space, players_dict):
        """Bắt đầu một phiên đấu giá mới cho mảnh đất"""
        # Trích xuất danh sách ID của tất cả người chơi trong phòng chưa phá sản
        active_participants = [p_id for p_id, p in players_dict.items() if not p.is_bankrupt]
        
        self.active_auction = {
            'property': property_space,
            'participants': active_participants,
            'highest_bid': 10000,  # Giá khởi điểm siêu rẻ để kích thích sự hưng phấn
            'highest_bidder': None,
            'status': 'ongoing'
        }
        return self.active_auction

    def place_bid(self, player_id, bid_amount, player_balance):
        """Xử lý khi có người chơi bấm nút ra giá"""
        if not self.active_auction or self.active_auction['status'] != 'ongoing':
            return False, "Không có phiên đấu giá nào đang diễn ra."
            
        if player_id not in self.active_auction['participants']:
            return False, "Bạn không có quyền tham gia phiên đấu giá này."
            
        if bid_amount <= self.active_auction['highest_bid']:
            return False, "Giá đưa ra phải cao hơn giá hiện tại!"
            
        if bid_amount > player_balance:
            return False, "Bạn không đủ tiền mặt để đưa ra mức giá này!"

        # Cập nhật mức giá mới
        self.active_auction['highest_bid'] = bid_amount
        self.active_auction['highest_bidder'] = player_id
        return True, "Ra giá thành công!"

    def withdraw(self, player_id):
        """Người chơi bấm nút 'Bỏ cuộc' (Fold)"""
        if self.active_auction and player_id in self.active_auction['participants']:
            self.active_auction['participants'].remove(player_id)
            
            # Kiểm tra xem có phải chỉ còn lại 1 người duy nhất trụ lại không
            if len(self.active_auction['participants']) == 1:
                self.active_auction['status'] = 'finished'
                winner_id = self.active_auction['participants'][0]
                
                # Nếu tất cả mọi người đều bỏ cuộc ngay từ đầu, người cuối cùng nghiễm nhiên thắng với giá khởi điểm
                if self.active_auction['highest_bidder'] is None:
                     self.active_auction['highest_bidder'] = winner_id

            # Trường hợp hiếm: Mọi người đều chê, không ai thèm lấy
            elif len(self.active_auction['participants']) == 0:
                self.active_auction['status'] = 'cancelled'
                
        return True
        
    def get_result(self):
        """Trả về toàn bộ thông tin đấu giá để Game Manager xử lý trừ tiền và trao sổ đỏ"""
        return self.active_auction