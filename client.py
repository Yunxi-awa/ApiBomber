import socket
import sys

class Client:
    def __init__(self, server_address: str, port: int):
        self.server_address = server_address
        self.port = port

    def send_command(self, command: str):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((self.server_address, self.port))
            client_socket.sendall(command.encode('utf-8'))
            response = client_socket.recv(4096)
            print(f"Response from {self.server_address}:{self.port} - {response.decode('utf-8')}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python client.py <server_address> <port> <command>")
        sys.exit(1)

    client = Client(sys.argv[1], int(sys.argv[2]))
    client.send_command(' '.join(sys.argv[3:]))
