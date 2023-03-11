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
    players = {"blue": None, "red": None}  # (ip, port) for TCP
    game = Model.Game()
    isBlueMove = True

    isGameStarted = False
    isGameOver = False

    isSomethingChanged = {"blue": False, "red": False}  # to manage updates for players

    def __init__(self):

        # Create a UDP socket to send Game Data
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.SERVER_IP, self.SERVER_PORT_UDP))
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.settimeout(5)

        # Create a TCP socket to connect between players and server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            server_socket.bind((self.SERVER_IP, self.SERVER_PORT))
            server_socket.listen(2)  # 2 players
            print("Game Server is ready")

            threads = []
            print(f"Listening on {self.SERVER_IP}:{self.SERVER_PORT}")

            # Accept connections from players
            while True:
                client_socket, address = server_socket.accept()

                thread = threading.Thread(target=self.client_handler, args=(client_socket, address))
                thread.start()  # start a new thread for each client connection
                threads.append(thread)

    def add_player(self, address, color):  # save player's address in a dictionary
        self.lock.acquire()
        self.players[color] = address
        print(self.players)
        self.lock.release()

    def client_handler(self, client_socket, address):  # handle client requests
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
        packet = Packet.Packet()  # create a packet object
        packet.deserialize(bpacket)  # deserialize data from client and fill the packet object
        if packet.message == 'connect' and self.game.state == 'not initialized':  # blue player
            print('first player connected')
            self.game.set_state('menu')
            self.game.set_color('blue')
            self.add_player(address, 'blue')
            # self.send_game(client_socket)  # tcp
            self.send_game_rudp()
        elif packet.message == 'connect' and not self.is_server_full():  # red player
            print('second player connected')
            self.game.set_state('wait')
            color = 'red'
            if self.players['blue'] is None:
                color = 'blue'
            self.game.set_color(color)
            self.add_player(address, color)
            # self.send_game(client_socket) # tcp
            self.send_game_rudp()
        elif packet.message == 'options':  # player sent options for the game
            print('options received')
            packet_options = Packet.PacketOptions()  # create a packet object
            packet_options.deserialize(bpacket)  # deserialize data from client and fill the packet object
            self.game.set_field(packet_options.width, packet_options.height)  # set field size
            self.game.set_state('play')  # start the game
            self.isGameStarted = True
            self.isSomethingChanged['blue'] = True  # update blue player when asked
            self.isSomethingChanged['red'] = True  # update red player when asked
        elif packet.message == 'update?':  # player wants to know if he needs to update the game
            print('update? received')
            packet = Packet.Packet()  # create a packet object
            if self.isNeedToUpdate(address):
                print('update request approved')
                packet.message = 'yes'  # send yes if player needs to update
            else:
                print('update request denied')
                packet.message = 'no'  # send no if player doesn't need to update
            client_socket.send(packet.serialize())

        elif packet.message == 'update':  # player wants to update the game
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
            # self.send_game(client_socket)  # tcp
            self.send_game_rudp()
        elif packet.message == 'move':  # player wants to move
            packet_move = Packet.PacketMove()  # create a packet object
            packet_move.deserialize(bpacket)  # deserialize data from client and fill the packet object
            self.game.set_move(packet_move.x, packet_move.y, self.isBlueMove)  # make a move if it is possible
            self.switchPlayer()  # switch player if needed
            self.game.set_visited()  # set visited cells
            self.isGameOver = self.game.is_game_over()  # check if game is over
            self.isSomethingChanged['blue'] = True  # update blue player when asked
            self.isSomethingChanged['red'] = True  # update red player when asked
        elif packet.message == 'exit':  # player exited from the game (only normal exit. will not work if error occurs)
            print('exit received')
            if self.players['blue'] == address:  # delete players from the dictionary
                self.players['blue'] = None
                self.isSomethingChanged['blue'] = True
            elif self.players['red'] == address:
                self.players['red'] = None
                self.isSomethingChanged['red'] = True
            if self.players['blue'] is None and self.players['red'] is None:  # if both players left restart the game
                self.isGameOver = True
                self.restart_game()
        elif packet.message == 'again':  # player wants to play again. return to menu
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
            # self.send_game(client_socket)  # tcp
            self.send_game_rudp()

    def restart_game(self):
        if self.isGameOver:
            print('game restarted')
            self.game = Model.Game()  # initialize game
            self.isGameStarted = False
            self.isGameOver = False

    def send_game(self, client_socket):
        packet_game = Packet.PacketGame(self.game)  # create a packet object with game
        client_socket.sendall(packet_game.serialize())

    def three_way_handshake(self):
        print('Waiting for client to connect...')
        break_count = 0
        while True:
            try:
                message, client_address = self.udp_socket.recvfrom(1024)  # receive message from client to get his address
            except socket.timeout:
                break_count += 1
                if break_count == 10:
                    break
                continue
            if message == b'connect':
                break_count = 0
                self.udp_socket.sendto(b'SYNACK', client_address)
                print('SYNACK sent')
                try:
                    message, client_address = self.udp_socket.recvfrom(1024)  # receive ACK
                except socket.timeout:
                    break_count += 1
                    if break_count == 10:
                        break
                    continue
                if message == b'ACK':
                    print('Client connected')
                    break
        return client_address



    def send_game_rudp(self):
        self.lock.acquire()  # synchronize threads
        client_address = self.three_way_handshake()  # receive message from client to get his address
        if client_address is None:
            self.lock.release()
            return
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
        break_count = 0
        sent_before = 0
        while sent < len(packets):
            if sent_before == sent:
                break_count += 1
                if break_count == 10:
                    self.lock.release()
                    return
            else:
                break_count = 0
                sent_before = sent
            for i in range(sent, sent + window_size):  # send packets in window
                if i >= len(packets):
                    break
                try:
                    last = sent + window_size - 1
                    data = packets[i] + SEPARATOR.encode() + str(i).encode() + SEPARATOR.encode() + str(
                        sent).encode() + SEPARATOR.encode() + str(last).encode()
                    self.udp_socket.sendto(data, client_address)
                    print("Sent packet " + str(i) + " of " + str(len(packets)))
                except socket.error:
                    print("Error sending packet")
                    break
            sent += window_size
            try:
                self.udp_socket.settimeout(1)
                ack = self.udp_socket.recv(1024)
                if ack == b"ACK":  # if packet was received successfully
                    print("Sent " + str(sent) + " packets")
                    print("Window size: " + str(window_size) + " Threshold: " + str(threshold))
                    if window_size * 2 + sent < threshold:  # slow start
                        window_size *= 2
                    elif window_size + sent < threshold:  # congestion avoidance
                        window_size += 1
                else:  # if packet was lost
                    sent = max(sent - window_size, 0)
                    window_size = max(window_size // 2, 1)
                    threshold = max(threshold // 2, 1)
                    print("Packet lost")
                    print(f"Sent {sent} packets, window size: {window_size}, threshold: {threshold}")
            except socket.timeout:
                sent = max(sent - window_size, 0)
                window_size = max(window_size // 2, 1)
                threshold = max(threshold // 2, 1)
            self.udp_socket.settimeout(None)
        break_count = 0
        while True:  # send end of transmission
            self.udp_socket.sendto(b"END", client_address)  # send end of transmission
            self.udp_socket.settimeout(2)
            try:
                ack = self.udp_socket.recv(1024).decode()
            except socket.timeout:
                break_count += 1
                if break_count == 10:
                    break
                continue
            if ack == "ACK":
                break
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
