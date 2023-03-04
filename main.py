import socketserver, socket
from time import sleep
from threading import Thread
from enum import Enum

# My Constants
SOCKET_TIMEOUT = 5

# Validation Constants
SERVER_KEYS = [23019, 32037, 18789, 16443, 18189]
CLIENT_KEYS = [32037, 29295, 13603, 29533, 21952]
TIMEOUT = 1
CLIENT_OK = 12
CLIENT_USERNAME = 20
CLIENT_MESSAGE = 100
TIMEOUT_RECHARGING = 5

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
class LogicException(Exception):
    pass

class Client(Thread): # Extend Thread class
    def __init__(self, soc, verbose = True):
        super().__init__()
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
        self.auth_process = 0
        self.charging = False
        self.turning = False
        self.verbose = verbose

    def print(self, *args, **kwargs):
        if self.verbose == True:
            print(*args, **kwargs)
    def move(self):
        self.print("Moving")
        self.send("102 MOVE")
    def read(self):
        _txt = ""
        while _txt[-2:] != "\a\b":
            _txt += self.connection.recv(200).decode()
            if self.auth_process == 0: # username
                if _txt.count("\a\b") == 0 and len(_txt) > CLIENT_USERNAME - 2:
                    raise MessageSyntaxException("Username too short")
                self.auth_process += 1

            elif self.auth_process == 5: # Moving (client_ok)
                # It is only going to be position commands, they cannot precache "secret" answer
                individual_pos = _txt.split("\a\b")
                for pos in individual_pos:
                    if len(pos) > CLIENT_OK - 2:
                        raise MessageSyntaxException("Max move length")

            elif self.auth_process == 10: # Secret
                if _txt.count("\a\b") == 0 and len(_txt) > CLIENT_MESSAGE - 2:
                    raise MessageSyntaxException("Secret length")
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
        #self.print("Sent:", (message + "\a\b"))

    def get_asci_hash(self):
        res = 0
        for c in self.name:
            res += ord(c)
        return res
    
    def initial_act(self):

        max_iter = 3
        i = 0
        while True:
            self.read()
            self.print(self.messages)
            while len(self.messages) > 0:
                msg = self.messages.pop(0)
                i = self._initial_act(msg, order = i)
                if i >= max_iter:
                    break 
            if i >= max_iter:
                    break 
            
        self.move()

    def _initial_act(self, msg, order):

        if msg == "RECHARGING":
            self.print("Charging...")
            self.connection.settimeout(TIMEOUT_RECHARGING)
            self.charging = True
            return order
            
        elif msg == "FULL POWER":
            if self.charging == False:
                raise LogicException("Robot said hes fully charged without telling he needs to be recharged")
            self.print("Fully Charged!")
            self.connection.settimeout(TIMEOUT)
            self.charging = False
            return order
        elif order == 0:
            if len(msg) > 20 - 2: raise MessageSyntaxException()
            self.name = msg
            self.send("107 KEY REQUEST")
        elif order == 1:
            try:
                self.keyid = int(msg)
            except ValueError:
                raise MessageSyntaxException("Keyid couldn't be converted to int")

            if self.keyid < 0 or self.keyid > len(SERVER_KEYS) - 1:
                self.print(self.keyid)
                raise ServerKeyOutOfRangeException()	
            name_hash = self.get_asci_hash()
            mutual_hash = name_hash * 1000 % 65536
            self.server_hash = str((mutual_hash + SERVER_KEYS[self.keyid]) % 65536)
            self.client_hash = str((mutual_hash + CLIENT_KEYS[self.keyid]) % 65536)

            self.send(self.server_hash)
        elif order == 2:
            client_sent_hash = msg
            if self.client_hash == client_sent_hash:
                self.send("200 OK")
                self.auth_process = 5
            else:
                # Are all characters numbers?
                for c in client_sent_hash:
                    if c < '0' or c > '9':
                        raise MessageSyntaxException("sent hash is not a number")
                
                if int(client_sent_hash) > 65536: raise MessageSyntaxException("Client hash too big")

                # 
                raise LoginFailedException()

        return order + 1
    def act(self, msg):
        if msg == "RECHARGING":
            self.print("Charging...")
            self.connection.settimeout(TIMEOUT_RECHARGING)
            self.charging = True
        elif msg == "FULL POWER":
            self.print("Fully Charged!")
            self.connection.settimeout(TIMEOUT)
            self.charging = False
        elif msg[:2] == "OK":
            try:
                x, y = (int(x) for x in msg[3:].split(" "))
            except ValueError:
                raise MessageSyntaxException("Problem loading coordinates")

            self.x = x
            self.y = y
            self.print(">>", x,y, self.dir, self.messages)

            if x == 0 and y == 0:
                #self.print("ending messages:", self.messages)
                self.send("105 GET MESSAGE")
                self.auth_process = 10
                if len(self.messages) == 0:
                    self.read()
                msg = self.messages.pop(0)
                if msg == "RECHARGING":
                    raise LogicException("Robot said hes fully charged without telling he needs to be recharged")
                    
                self.print("Secret:", msg)
                self.send("106 LOGOUT")
                self.end()
            elif self.prevx == -69 and self.prevy == -69:
                self.move()

            else:
                if self.dir == -69: # we had moved previously
                    if self.prevx == x and self.prevy == y and self.turning == False:
                        self.turning = False
                        self.print("Initial OBSTACLE!!!")
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
                
                        self.print("direction sellected", self.dir) 
                if self.prevx == x and self.prevy == y and self.turning == False:
                    self.turning = False
                    self.print("OBSTACLE!!!")
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
                            self.print("turn me down")
                            self.turn_to(DIRECTION.DOWN)

            self.prevx = x
            self.prevy = y
        else:
            # other actions
            pass

        self.turning = False


    def turn_right(self):
        self.print("Turning Right")
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
        msg = self.messages.pop(0) # don't need it its the same info

        if msg == "RECHARGING":
            self.print("Charging [TURN]...", [msg] + self.messages)
            self.connection.settimeout(TIMEOUT_RECHARGING)
            if len(self.messages) == 0:
                self.read()
            msg = self.messages.pop(0) # don't need it just recharging
            self.print("Charging msg:", msg)
            self.connection.settimeout(TIMEOUT)

            if len(self.messages) == 0:
                self.read()
            self.messages.pop(0) # current position message
        
    def turn_to(self, direction): # CONTINUAL ROTATION TO THE RIGHT
        self.turning = True
        if direction == self.dir:
            self.print("Turned correctly: ", self.dir)
            # adding last essages for us to work on, because client aint goint to send us anything
            self.move()
            #self.print(self.messages)
            return
        
        self.print("( To:", direction, "| from:", self.dir, ")", end=" ")
        self.turn_right()
        

        self.turn_to(direction) #RECURSIVE CALLING
            

            
    def run(self):
        try:
            self.initial_act()
            while self.thread_active:
                if len(self.messages) == 0:
                    self.read()
                while len(self.messages) > 0:
                    msg = self.messages.pop(0)
                    self.act(msg)

        except socketserver.socket.timeout as e: #Toto se bude hodit později :)
            print("Connection Killed by us: Connection Timeout", e)
        except MessageSyntaxException as e:
            self.send("301 SYNTAX ERROR")
            print("MessageSyntaxException", e)
        except ServerKeyOutOfRangeException:
            self.send("303 KEY OUT OF RANGE")
            print("ServerKeyOutOfRangeException")
        except LoginFailedException:
            self.send("300 LOGIN FAILED")
            print("LoginFailedException")
        except LogicException as e:
            self.send("302 LOGIC ERROR")
            print("LogicException", e)
        self.end()

    def end(self):
        self.connection.close()
        self.thread_active = False

if __name__ == "__main__":

    import socket

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening = ('localhost', 4444)
    server.bind(listening)

    # Useful for testing reasons
    #server.settimeout(SOCKET_TIMEOUT)

    threads = []
    server.listen(5)
    for i in range(4444):

        try:
            c = Client(server)
        except:
            print("[Timeout]: Socket closed for new connections.")
            break

        c.start()
        threads.append(c)

    # Let main thread wait for main thread
    for t in threads:
        t.join()

