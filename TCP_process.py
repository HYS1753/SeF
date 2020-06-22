import core
from core import *
import struct

# TCP 패킷의 헤더 작성
def createHeader(type, payload = 0):
    if type == 'Symbol_Send_Request':
        header = struct.pack('ii', Symbol_Send_Request, payload)    # 요청할 block no
    elif type == 'Symbol_Send_Start':
        header = struct.pack('ii', Symbol_Send_Start, payload)      # 0
    elif type == 'Symbol_Receive_Ready':
        header = struct.pack('ii', Symbol_Receive_Ready, payload)
    elif type == 'Symbol_Send_End':
        header = struct.pack('ii', Symbol_Send_End, payload)
    elif type == 'Symbol_Receive_End':
        header = struct.pack('ii', Symbol_Receive_End, payload)
    elif type == 'Symbols':
        header = struct.pack('ii', Symbols, payload)
    elif type == 'Symbols_Size':
        header = struct.pack('ii', Symbols_Size, payload)
    elif type == 'Symbols_End':
        header = struct.pack('ii', Symbols_End, payload)
    else:
        header = struct.pack('ii', Error, payload)
    return header

# Encoding
# symbol_Send_start -> Symbol_Receive_Ready
# -> Symbols -> Symbol_Send_End -> Symbol_Receive_End

# Decoding
# Symbol_Send_Request -> symbol_Send_start -> Symbol_Receive_Ready
# -> Symbols -> Symbol_Send_End -> Symbol_Receive_End