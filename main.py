import socket
from time import sleep

def load(socket, maxsize = 20):
    connection, address = socket.accept()
    buf = connection.recv(14)
    text = buf.decode()
    print(buf)
    if text[-2:] != "\a\b" or len(text) > maxsize:
        raise Exception("Error when loading")
    return text[:-2], connection

if __name__ == "__main__":

    import socket

    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    destination = ('localhost', 3999)
    serversocket.bind(destination)


    serversocket.listen(5) # become a server socket, maximum 5 connections

    username, connection = load(serversocket)
    connection.send("107 KEY REQUEST\a\b".encode())
    exit()
    key_id, connection = load(serversocket)

    while True:
        s = ""

        while True:
            sleep(0.5)
            connection, address = serversocket.accept()

            buf = connection.recv(102)
            if len(buf) > 0:
                print(buf.decode())
                connection.send("107 KEY REQUEST\a\b".encode())