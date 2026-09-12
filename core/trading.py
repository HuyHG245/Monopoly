class TradingSystem:
    def __init__(self):
        # Lưu trữ trạng thái giao dịch đang mở giữa 2 người chơi
        self.active_trade = None

    def propose_trade(self, sender_id, receiver_id, offer_data):
        """
        Gửi lời đề nghị trao đổi.
        offer_data cấu trúc mẫu: 
        {
            'sender_money': 2000000, 
            'sender_properties': [prop_id_1],
            'receiver_money': 0, 
            'receiver_properties': [prop_id_2, prop_id_3]
        }
        """
        if self.active_trade is not None:
            return False, "Đang có một giao dịch khác diễn ra. Vui lòng đợi."

        self.active_trade = {
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'offer': offer_data,
            'status': 'pending'  # pending, accepted, rejected
        }
        return True, "Đã gửi lời đề nghị trao đổi thành công!"

    def respond_trade(self, responder_id, accept=True):
        """Người nhận phản hồi lời đề nghị (Đồng ý hoặc Từ chối)"""
        if not self.active_trade or self.active_trade['status'] != 'pending':
            return False, "Không tìm thấy lời đề nghị giao dịch nào."

        if responder_id != self.active_trade['receiver_id']:
            return False, "Bạn không phải là người được chỉ định nhận giao dịch này."

        if accept:
            self.active_trade['status'] = 'accepted'
            trade_info = self.active_trade
            self.active_trade = None  # Reset lại trạng thái
            return True, trade_info   # Trả về thông tin để GameManager tiến hành đổi sổ đỏ và tiền
        else:
            self.active_trade['status'] = 'rejected'
            self.active_trade = None
            return False, "Đã từ chối giao dịch."

    def cancel_trade(self, player_id):
        """Người gửi chủ động hủy đề nghị"""
        if self.active_trade and player_id == self.active_trade['sender_id']:
            self.active_trade = None
            return True, "Đã hủy giao dịch."
        return False, "Không thể hủy."