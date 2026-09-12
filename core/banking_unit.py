class BankingUnit:
    def __init__(self):
        # Ngân hàng trong Monopoly có số tiền vô hạn, nên chúng ta không cần biến lưu trữ số dư
        pass

    def pay_bank(self, player, amount):
        """Người chơi trả tiền cho Ngân hàng (mua đất, nộp thuế, nộp phạt...)"""
        if player.balance >= amount:
            player.balance -= amount
            return True
        return False

    def receive_from_bank(self, player, amount):
        """Ngân hàng xuất tiền cho người chơi (đi qua ô GO, trúng thẻ thưởng...)"""
        player.balance += amount
        return True

    def transfer_money(self, payer, payee, amount):
        """Chuyển tiền giữa hai người chơi (trả tiền thuê nhà, mua bán đất...)"""
        if payer.balance >= amount:
            payer.balance -= amount
            payee.balance += amount
            return True
        return False
        
    def check_bankruptcy(self, player, debt_amount):
        """
        Kiểm tra xem người chơi có khả năng thanh toán khoản nợ hay không.
        Trả về True nếu CHÍNH THỨC PHÁ SẢN (Tiền mặt + Tài sản thanh lý < Nợ).
        """
        # Nếu tiền mặt đủ trả thì chắc chắn chưa phá sản
        if player.balance >= debt_amount:
            return False 
            
        # Nếu tiền mặt không đủ, ngân hàng sẽ tính toán tổng giá trị tài sản có thể quy ra tiền
        liquidatable_assets = player.balance
        
        for prop in player.properties:
            if not prop.is_mortgaged:
                # Tiền cầm cố đất = 50% giá trị gốc
                liquidatable_assets += int(prop.base_price * 0.5)
                
                # Tiền bán nhà = 50% giá trị mua nhà (chỉ áp dụng cho Property, không phải Station/Utility)
                if hasattr(prop, 'houses') and prop.houses > 0:
                    liquidatable_assets += int((prop.houses * prop.house_cost) * 0.5)
                    
        # Nếu bán hết nhà cửa và cầm cố mọi sổ đỏ mà vẫn không đủ trả nợ -> Phá sản
        if liquidatable_assets < debt_amount:
            return True
            
        return False