import pickle

import Model


class Packet:

    def __init__(self, message=None):
        self.message = message

    def get_message(self):
        return self.message

    def set_message(self, message):
        self.message = message

    def serialize(self):
        return pickle.dumps({'message': self.get_message()})

    def deserialize(self, bpacket):
        packet = pickle.loads(bpacket)
        self.set_message(packet['message'])


class PacketOptions(Packet):
    def __init__(self, width=0, height=0):
        super().__init__('options')
        self.width = width
        self.height = height

    def serialize(self):
        return pickle.dumps({'message': self.get_message(), 'width': self.width, 'height': self.height})

    def deserialize(self, bpacket):
        packet = pickle.loads(bpacket)
        self.set_message(packet['message'])
        self.width = packet['width']
        self.height = packet['height']


class PacketMove(Packet):
    def __init__(self, x=0, y=0):
        super().__init__('move')
        self.x = x
        self.y = y

    def serialize(self):
        return pickle.dumps({'message': self.get_message(), 'x': self.x, 'y': self.y})

    def deserialize(self, bpacket):
        packet = pickle.loads(bpacket)
        self.set_message(packet['message'])
        self.x = packet['x']
        self.y = packet['y']


class PacketGame(Packet):

    def __init__(self, game=Model.Game()):
        super().__init__('game')
        self.game = game

    def serialize(self):
        return pickle.dumps({'message': self.get_message(), 'game': self.game.serialize()})

    def deserialize(self, bpacket):
        packet = pickle.loads(bpacket)
        self.set_message(packet['message'])
        self.game.deserialize(packet['game'])
