import socket
import struct
import asyncio
import logging
from config import RCON_HOST, RCON_PORT, RCON_PASSWORD

logger = logging.getLogger(__name__)

class RCONSocket:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((self.host, self.port))
        self._send_packet(3, self.password.encode('utf-8'))
        resp = self._receive_packet()
        if resp['id'] == -1:
            raise Exception("RCON authentication failed")
        return True

    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def _send_packet(self, packet_type, body):
        packet_id = 1
        length = 10 + len(body)
        packet = struct.pack('<ii', length, packet_id) + struct.pack('<i', packet_type) + body + b'\x00\x00'
        self.sock.send(packet)

    def _receive_packet(self):
        header = self.sock.recv(4)
        if not header:
            return None
        length = struct.unpack('<i', header)[0]
        data = self.sock.recv(length)
        packet_id, packet_type = struct.unpack('<ii', data[:8])
        body = data[8:-2].decode('utf-8')
        return {'id': packet_id, 'type': packet_type, 'body': body}

    def send_command(self, command):
        self._send_packet(2, command.encode('utf-8'))
        resp = self._receive_packet()
        return resp['body']

async def send_rcon_command(command):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _rcon_sync, command)

def _rcon_sync(command):
    rcon = RCONSocket(RCON_HOST, RCON_PORT, RCON_PASSWORD)
    try:
        rcon.connect()
        response = rcon.send_command(command)
        return response
    finally:
        rcon.disconnect()
