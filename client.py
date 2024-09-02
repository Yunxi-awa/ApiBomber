import socket
import sys

def send_command(command: str):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', 9999))
        s.sendall(command.encode('utf-8'))
        response = s.recv(1024)
        print('Received from server:', response.decode('utf-8'))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <command>")
        sys.exit(1)

    command = " ".join(sys.argv[1:])
    send_command(command)
