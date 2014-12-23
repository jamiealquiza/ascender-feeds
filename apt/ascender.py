#!/usr/bin/env python

import socket

class Client(object):

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect()
        self.sock.close()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.address, self.port))
        except Exception, e:
            print e

    def send(self, message):
        try:
            self.connect()
            self.sock.sendall(message)
        except Exception, e:
            print e
            return

        resp = ""
        while 1:
            r = self.sock.recv(256)
            if not r:
                print resp.rstrip()
                self.sock.close()
                break
            else:
                resp += r
                continue
