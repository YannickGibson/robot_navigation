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
        self.x = -69
        self.y = -69
        self.messages = []

    def move(self):
        print("Moving")
        self.send("102 MOVE")
    def read(self):
        _txt = ""
        while _txt[-2:] != "\a\b":
            _txt += self.connection.recv(200).decode()
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
        self.messages = self.messages + messages
        return messages
    
    def send(self, message):
        self.connection.sendall((message + "\a\b").encode())
        #print("Sent:", (message + "\a\b"))

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
            print(self.messages)
            while len(self.messages) > 0:
                msg = self.messages.pop(0)
                self._initial_act(msg, order = i)
                i += 1
                if i >= max_iter:
                    break 
            if i >= max_iter:
                    break 
            
        self.move()

    def _initial_act(self, msg, order):
        if order == 0:
            if len(msg) > 20 - 2: raise MessageSyntaxException()
            self.name = msg
            self.send("107 KEY REQUEST")
        if order == 1:
            try:
                self.keyid = int(msg)
            except ValueError:
                raise MessageSyntaxException("Keyid couldn't be converted to int")

            if self.keyid < 0 or self.keyid > len(SERVER_KEYS) - 1:
                print(self.keyid)
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
                
                # Are all characters numbers?
                for c in client_sent_hash:
                    if c < '0' or c > '9':
                        raise MessageSyntaxException()
                    
                raise LoginFailedException()

    
    def act(self, msg):
        if msg[:2] == "OK":
            try:
                x, y = (int(x) for x in msg[3:].split(" "))
            except ValueError:
                raise MessageSyntaxException("Problem loading coordinates")

            self.x = x
            self.y = y
            print(">>", x,y, self.dir)

            if x == 0 and y == 0:
                print("ending messages:", self.messages)
                self.send("105 GET MESSAGE")
                if len(self.messages) == 0:
                    self.read()
                msg = self.messages.pop(0)
                print("secret:", msg)
                self.send("106 LOGOUT")
                self.end()
            elif self.prevx == -69 and self.prevy == -69:
                self.move()

            else:
                if self.dir == -69: # we had moved previously
                    if self.prevx == x and self.prevy == y:
                        print("Initial OBSTACLE!!!")
                        self.turn_right()
                        self.move()
                        return
                       
                    else:
                        if x > self.prevx: 
                            self.dir = DIRECTION.RIGHT
                        elif x < self.prevx:
                            self.dir = DIRECTION.LEFT
                        if y > self.prevy: 
                            self.dir = DIRECTION.UP
                        elif y < self.prevy:
                            self.dir = DIRECTION.DOWN
                
                        print("direction sellected", self.dir) 
                if self.prevx == x and self.prevy == y:
                    print("OBSTACLE!!!")
                    if self.dir == DIRECTION.RIGHT:
                        if  y > 0:
                            self.turn_to(DIRECTION.DOWN)
                        else:
                            self.turn_to(DIRECTION.UP)
                    elif self.dir == DIRECTION.LEFT:
                        if  y > 0:
                            self.turn_to(DIRECTION.DOWN)
                        else:
                            self.turn_to(DIRECTION.UP)
                    elif self.dir == DIRECTION.UP:
                        if  x > 0:
                            self.turn_to(DIRECTION.LEFT)
                        else:
                            self.turn_to(DIRECTION.RIGHT)
                    elif self.dir == DIRECTION.DOWN:
                        if  x > 0:
                            self.turn_to(DIRECTION.LEFT)
                        else:
                            self.turn_to(DIRECTION.RIGHT)
                                

                elif self.dir == DIRECTION.DOWN:
                    if y >= abs(x):
                        if y > 0:
                            self.move()
                        else:
                            self.turn_to(DIRECTION.UP)
                    else:
                        if x < 0:
                            self.turn_to(DIRECTION.RIGHT)
                        else:
                            self.turn_to(DIRECTION.LEFT)
                elif self.dir == DIRECTION.UP:
                    if -y >= abs(x):
                        if y < 0:
                            self.move()
                        else:
                            self.turn_to(DIRECTION.DOWN)
                    else:
                        if x < 0:
                            self.turn_to(DIRECTION.RIGHT)
                        else:
                            self.turn_to(DIRECTION.LEFT)
                elif self.dir == DIRECTION.LEFT:
                    if x >= abs(y):
                        if x > 0:
                            self.move()
                        else:
                            self.turn_to(DIRECTION.RIGHT)
                    else:
                        if y < 0:
                            self.turn_to(DIRECTION.UP)
                        else:
                            self.turn_to(DIRECTION.DOWN)
                elif self.dir == DIRECTION.RIGHT:
                    if -x >= abs(y):
                        if x < 0:
                            self.move()
                        else:
                            self.turn_to(DIRECTION.LEFT)
                    else:
                        if y < 0:
                            self.turn_to(DIRECTION.UP)
                        else:
                            print("turn me down")
                            self.turn_to(DIRECTION.DOWN)

            self.prevx = x
            self.prevy = y
        else:
            # other actions
            pass

    def turn_right(self):
        print("Turning Right")
        self.send("104 TURN RIGHT")        
        if self.dir == DIRECTION.UP:
            self.dir = DIRECTION.RIGHT
        elif self.dir == DIRECTION.DOWN:
            self.dir = DIRECTION.LEFT
        elif self.dir == DIRECTION.LEFT:
            self.dir = DIRECTION.UP
        elif self.dir == DIRECTION.RIGHT:
            self.dir = DIRECTION.DOWN
        # redundant info about position
        if len(self.messages) == 0:
            self.read() # read ok statement
        self.messages.pop(0) # don't need it its the same info
        
    def turn_to(self, direction): # CONTINUAL ROTATION TO THE RIGHT
        if direction == self.dir:
            print("turned correctly: ", self.dir)
            # adding last essages for us to work on, because client aint goint to send us anything
            self.move()
            #self.messages = [f'OK {self.x} {self.y}'] + self.messages

            #print(self.messages)
            #self.act(f'OK {self.x} {self.y}')
            return
        
        print("( To:", direction, ")", end=" ")
        self.turn_right()
        

        self.turn_to(direction) #RECURSIVE CALLING
            

            
    def run(self):
        try:
            self.initial_act()
            while self.thread_active:
                if len(self.messages) == 0:
                    messages = self.read()
                while len(self.messages) > 0:
                    msg = self.messages.pop(0)
                    self.act(msg)

        except socketserver.socket.timeout as e: #Toto se bude hodit později :)
            self.end()
            print("Connection Killed by us: Connection Timeout", e)
        except MessageSyntaxException as e:
            self.send("301 SYNTAX ERROR")
            self.end()
            print("MessageSyntaxException")
        except ServerKeyOutOfRangeException:
            self.send("303 KEY OUT OF RANGE")
            self.end()
            print("ServerKeyOutOfRangeException")
        except LoginFailedException:
            self.send("300 LOGIN FAILED")
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
    for i in range(888888):
        c = Client(server)
        c.start()
        threads.append(c)

    for t in threads:
        t.join()

