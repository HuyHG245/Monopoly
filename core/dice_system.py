import random

class DiceSystem:
    def __init__(self):
        # Biến đếm số lần đổ đôi (Double) liên tiếp của người chơi hiện tại
        self.consecutive_doubles = 0

    def roll(self):
        """
        Thực hiện tung 2 viên xúc xắc.
        Trả về: (die1, die2, tổng, có_phải_đổ_đôi, bị_phạt_vào_tù_không)
        """
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        is_double = (die1 == die2)
        total = die1 + die2
        
        go_to_jail = False

        if is_double:
            self.consecutive_doubles += 1
            # Luật Monopoly: Đổ đôi 3 lần liên tiếp -> Bắn tốc độ, vào tù ngay lập tức
            if self.consecutive_doubles == 3:
                go_to_jail = True
                self.consecutive_doubles = 0  # Reset lại bộ đếm để dùng cho người tiếp theo
        else:
            # Nếu không đổ đôi, ngắt chuỗi và reset bộ đếm
            self.consecutive_doubles = 0

        return die1, die2, total, is_double, go_to_jail
        
    def reset_doubles_count(self):
        """Được Game Manager gọi để dọn dẹp biến số khi chuyển sang lượt của người khác"""
        self.consecutive_doubles = 0