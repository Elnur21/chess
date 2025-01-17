import socket
import threading

class ChessServer:
    def __init__(self, host, port):
        self.HOST = host
        self.PORT = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.HOST, self.PORT))
        self.server_socket.listen(2)
        self.clients = []
        self.colors = ['white', 'black']

    def broadcast(self, message, client_socket):
        for client in self.clients:
            if client != client_socket:
                try:
                    client.send(message)
                except:
                    self.remove(client)

    def remove(self, client_socket):
        if client_socket in self.clients:
            self.clients.remove(client_socket)

    def handle_client(self, client_socket):
        try:
            color = self.colors.pop(0)
            self.clients.append(client_socket)
            client_socket.send(color.encode())

            while True:
                message = client_socket.recv(1024)
                print(message)
                if message:
                    self.broadcast(message, client_socket)
                else:
                    self.remove(client_socket)
                    break
        except:
            pass

    def start(self):
        print("Server is running...")
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Connected with {addr}")
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()

if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 8080
    chess_server = ChessServer(HOST, PORT)
    chess_server.start()
