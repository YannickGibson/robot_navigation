import socketserver, socket
from time import sleep
from threading import Thread
from enum import Enum

TIMEOUT = 1
TIMEOUT_RECHARGING = 5
SERVER_KEYS = [23019, 32037, 18789, 16443, 18189]
CLIENT_KEYS = [32037, 29295, 13603, 29533, 21952]

class DIRECTION(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4
class MessageSyntaxException(Exception):
    pass
class ServerKeyOutOfRangeException(Exception):
    pass
class LoginFailedException(Exception):
    pass

class Client(Thread): # Extend Thread class
    def __init__(self, soc):
        super().__init__()
        soc.listen(TIMEOUT)
        self.connection, _ = soc.accept()
        self.connection.settimeout(TIMEOUT)
        self.name = ""
        self.thread_active = True
        self.prevx = -69
        self.prevy = -69
        self.dir = -69

    def read(self):
        _txt = self.connection.recv(200).decode()
        txt = _txt
        messages = []
        while True:
            prefix, ab, suffix = txt.partition("\a\b")
            if ab != "\a\b":
                raise MessageSyntaxException(f"INVALID ENDING SEQUENCE: '{_txt}',\n Part: '{txt}'")
            messages.append(prefix)
            txt = suffix
            if suffix == "":
                break
        return messages
    
    def send(self, message):
        self.connection.sendall((message + "\a\b").encode())
        print("Sent:", (message + "\a\b"))

    def get_asci_hash(self):
        res = 0
        for c in self.name:
            res += ord(c)

        return res
    
    def initial_act(self):

        max_iter = 3
        i = 0
        while True:
            messages = self.read()
            for msg in messages:
                self._initial_act(msg, order = i)
                i += 1
                if i >= max_iter:
                    break 
            if i >= max_iter:
                    break 
            
        self.send("102 MOVE")

    def _initial_act(self, msg, order):
        if order == 0:
            self.name = msg
            self.send("107 KEY REQUEST")
        if order == 1:
            self.keyid = int(msg)
            if self.keyid < 0 or self.keyid > len(SERVER_KEYS) - 1:
                self.send("303 KEY OUT OF RANGE")
                raise ServerKeyOutOfRangeException()	
            name_hash = self.get_asci_hash()
            mutual_hash = name_hash * 1000 % 65536
            self.server_hash = str((mutual_hash + SERVER_KEYS[self.keyid]) % 65536)
            self.client_hash = str((mutual_hash + CLIENT_KEYS[self.keyid]) % 65536)

            self.send(self.server_hash)
        if order == 2:
            client_sent_hash = msg
            if self.client_hash == client_sent_hash:
                self.send("200 OK")
            else:
                self.send("300 LOGIN FAILED")
                raise LoginFailedException()

    def act(self, msg):
        if msg[:2] == "OK":
            x, y = (int(x) for x in msg[3:].split(" "))
            if x == 0 and y == 0:
                self.send("105 GET MESSAGE")
                self.send("106 LOGOUT")
                self.end()
            elif self.prevx == -69 and self.prevy == -69:
                self.send("102 MOVE")

            elif self.dir == -69: # we had moved previously
                if self.prevx == x and self.prevy == y:
                    pass # obstacle 
                else:
                    if x > self.prevx: 
                        self.dir = DIRECTION.RIGHT
                    elif x < self.prevx:
                        self.dir = DIRECTION.LEFT
                    if x > self.prevy: 
                        self.dir = DIRECTION.UP
                    elif x < self.prevy:
                        self.dir = DIRECTION.DOWN

                self.send("102 MOVE")
            else:
                if self.dir == DIRECTION.DOWN:
                    if abs(y) >= abs(x):
                        self.send("102 MOVE")
                    else:
                        pass

            self.prevx = x
            self.prevy = y
        else:
            pass

    def run(self):
        try:
            self.initial_act()
            while self.thread_active:
                messages = self.read()
                for msg in messages:
                    self.act(msg)

        except socketserver.socket.timeout as e: #Toto se bude hodit později :)
            self.end()
            print("Connection Killed by us: Connection Timeout", e)
        except MessageSyntaxException as e:
            self.end()
            print("MessageSyntaxException")
        except ServerKeyOutOfRangeException:
            self.end()
            print("ServerKeyOutOfRangeException")
        except LoginFailedException:
            self.end()
            print("LoginFailedException")

    def end(self):
        self.connection.close()
        self.thread_active = False

if __name__ == "__main__":

    import socket

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening = ('localhost', 4444)
    server.bind(listening)

    threads = []
    while True:
        c = Client(server)
        c.start()
        threads.append(c)

    for t in threads:
        t.join()

