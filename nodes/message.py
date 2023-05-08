class Message:
    """

    """
    cnt = 0

    def __init__(self, sender_index: int, receiver_index: int, data: dict):
        Message.cnt += 1
        self.id = Message.cnt
        self.sender_index = sender_index
        self.receiver_index = receiver_index
        self.data = data

    def to_string(self):
        return "Msg-%02d: %s->%s" % (self.id, self.sender, self.receiver)
