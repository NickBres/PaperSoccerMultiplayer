import pickle
import socket
import threading
import Model
from threading import Lock
import Packet


class Server:
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 5000
    SERVER_PORT_UDP = 5001

    lock = Lock()
    players = {"blue": None, "red": None}
    players_udp = {"blue": None, "red": None}
    game = Model.Game()
    isBlueMove = True

    isGameStarted = False
    isGameOver = False

    isSomethingChanged = {"blue": False, "red": False}

    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.SERVER_IP, self.SERVER_PORT_UDP))
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.settimeout(1)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            server_socket.bind((self.SERVER_IP, self.SERVER_PORT))
            server_socket.listen(2)
            print("Game Server is ready")

            threads = []
            print(f"Listening on {self.SERVER_IP}:{self.SERVER_PORT}")

            while True:
                client_socket, address = server_socket.accept()

                thread = threading.Thread(target=self.client_handler, args=(client_socket, address))
                thread.start()
                threads.append(thread)

    def add_player(self, address, color):
        self.lock.acquire()
        self.players[color] = address
        print(self.players)
        self.lock.release()

    def client_handler(self, client_socket, address):
        client_addr = f"{address[0]}:{address[1]}"
        client_prefix = f"{{{client_addr}}}"
        with client_socket:
            print(f"Conection established with {client_addr}")
            while True:
                bpacket = client_socket.recv(8192)
                if not bpacket:
                    break
                self.process_request(address, client_socket, bpacket)

    def process_request(self, address, client_socket, bpacket):
        packet = Packet.Packet()
        packet.deserialize(bpacket)
        if packet.message == 'connect' and self.game.state == 'not initialized':  # blue player
            print('first player connected')
            self.game.set_state('menu')
            self.game.set_color('blue')
            self.add_player(address, 'blue')
            # self.send_game(client_socket)
            self.send_game_rudp()
        elif packet.message == 'connect' and not self.is_server_full():  # red player
            print('second player connected')
            self.game.set_state('wait')
            color = 'red'
            if self.players['blue'] is None:
                color = 'blue'
            self.game.set_color(color)
            self.add_player(address, color)
            # self.send_game(client_socket)
            self.send_game_rudp()
        elif packet.message == 'options':
            print('options received')
            packet_options = Packet.PacketOptions()
            packet_options.deserialize(bpacket)
            self.game.set_field(packet_options.width, packet_options.height)
            self.game.set_state('play')
            self.isGameStarted = True
            self.isSomethingChanged['blue'] = True
            self.isSomethingChanged['red'] = True
        elif packet.message == 'update?':
            print('update? received')
            packet = Packet.Packet()
            if self.isNeedToUpdate(address):
                print('update request approved')
                packet.message = 'yes'
            else:
                print('update request denied')
                packet.message = 'no'
            client_socket.send(packet.serialize())

        elif packet.message == 'update':
            if self.isGameStarted:
                if self.players['blue'] == address:  # blue player
                    print('blue player update request received')
                    self.game.set_color('blue')
                    if self.isBlueMove:
                        self.game.isYourTurn = True
                        if not self.isGameOver:
                            self.game.set_state('play')
                    else:
                        self.game.isYourTurn = False
                        if not self.isGameOver:
                            self.game.set_state('wait move')
                elif self.players['red'] == address:  # red player
                    print('red player update request received')
                    self.game.set_color('red')
                    if self.isBlueMove:
                        self.game.isYourTurn = False
                        if not self.isGameOver:
                            self.game.set_state('wait move')
                    else:
                        self.game.isYourTurn = True
                        if not self.isGameOver:
                            self.game.set_state('play')
            # self.send_game(client_socket)
            self.send_game_rudp()
        elif packet.message == 'move':
            packet_move = Packet.PacketMove()
            packet_move.deserialize(bpacket)
            self.game.set_move(packet_move.x, packet_move.y, self.isBlueMove)
            self.switchPlayer()
            self.game.set_visited()
            self.isGameOver = self.game.is_game_over()
            self.isSomethingChanged['blue'] = True
            self.isSomethingChanged['red'] = True
        elif packet.message == 'exit':
            print('exit received')
            if self.players['blue'] == address:
                self.players['blue'] = None
            elif self.players['red'] == address:
                self.players['red'] = None
            if self.players['blue'] is None and self.players['red'] is None:
                self.isGameOver = True
                self.restart_game()
        elif packet.message == 'again':
            self.restart_game()
            if self.players['blue'] == address:
                print('blue player again request received')
                self.game.set_color('blue')
                self.game.set_state('menu')
                self.isSomethingChanged['blue'] = True
            elif self.players['red'] == address:
                print('red player again request received')
                self.game.set_color('red')
                self.game.set_state('wait')
                self.isSomethingChanged['red'] = True
            # self.send_game(client_socket)
            self.send_game_rudp()

    def restart_game(self):
        if self.isGameOver:
            self.game = Model.Game()
            self.isGameStarted = False
            self.isGameOver = False

    def send_game(self, client_socket):
        packet_game = Packet.PacketGame(self.game)
        client_socket.sendall(packet_game.serialize())

    def send_game_rudp(self):
        self.lock.acquire()  # synchronize threads
        message, client_address = self.udp_socket.recvfrom(1024)  # receive message from client to get his address
        print('Sending game using rudp to: ', client_address)
        packet_game = Packet.PacketGame(self.game)
        data = packet_game.serialize()
        SEPARATOR = "<BARAK>"
        sent = 0
        window_size = 1
        packet_size = 1024
        packets = []
        for i in range(0, len(data), packet_size):  # split data into packets
            packets.append(data[i:i + packet_size])

        threshold = len(packets)  # threshold for congestion control
        while sent < len(packets):
            for i in range(sent, sent + window_size):  # send packets in window
                if i >= len(packets):
                    break
                try:
                    data = packets[i] + SEPARATOR.encode() + str(i).encode() + SEPARATOR.encode() + str(
                        window_size).encode()
                    self.udp_socket.sendto(data, client_address)
                except socket.error:
                    print("Error sending packet")
                    break
            sent += window_size
            try:
                self.udp_socket.settimeout(1)
                ack = self.udp_socket.recv(1024).decode()
                if ack == "ACK":
                    if window_size * 2 < threshold:
                        window_size *= 2
                    else:
                        window_size += 1
                elif ack == "TIMEOUT":
                    window_size = max(window_size // 2, 1)
                    threshold = window_size
                elif ack == "WRONG_SEQ":
                    window_size = max(window_size // 2, 1)
                    threshold = window_size
            except socket.timeout:
                window_size = max(window_size // 2, 1)
            self.udp_socket.settimeout(None)
        self.udp_socket.sendto("END".encode(), client_address)
        print("Game sent successfully")
        self.lock.release()

    def isNeedToUpdate(self, address):
        self.lock.acquire()
        if self.players['blue'] == address and self.isSomethingChanged['blue']:
            self.isSomethingChanged['blue'] = False
            self.lock.release()
            return True
        elif self.players['red'] == address and self.isSomethingChanged['red']:
            self.isSomethingChanged['red'] = False
            self.lock.release()
            return True
        self.lock.release()
        return False

    def switchPlayer(self):
        ballX = self.game.field.ball.x
        ballY = self.game.field.ball.y
        if not self.game.field.points[ballY][ballX].isVisited:
            self.isBlueMove = not self.isBlueMove

    def is_server_full(self):
        return self.players['blue'] is not None and self.players['red'] is not None


if __name__ == "__main__":
    server = Server()
