
## 서버 클라이언트 통합
import socket
import argparse
import threading
import struct
import numpy as np
import core
from core import *
from TCP_process import *
import TCP_process
from encoder import encode
from decoder import decode
from fileConvert import blocks_read, blocks_write
from blockencoder import read_blocks, save_symbols
from blockdecoder import decoding
# host(server의 IP)
host = '127.0.0.1'
# 서버로 요청한 클라이언트의 conn
user_list = {}
# 패킷의 크기
packet_size = 1024 #1040
# 요청한 블록 넘버
user_block_num = 0
# 디코딩 할 심볼이 저장될 변수
symbols = []
# 인코딩 할 심볼이 저장될 변수
encoded_symbols =[]
# LTcode Redundancy
redundancy = 2.0
# client count
ClientCount = 0
# client port 목록
neighbor_port = []
# 블록 size chain
block_size = {360:6849649, 635292:1225385}
# 블록 단위
k = 50

def check_header(message):
    temp= struct.unpack('ii', message)
    header = temp[0]
    payload = temp[1]
    return header, payload

def decode_symbol(encoded_symbols, k, user_block_num):
    global symbols
    file_path = 'c:/data/ltcodetest/node0/recoveredblocks'
    # 해당 폴더가 없을 시 생성
    if not (os.path.isdir(file_path)):
        os.makedirs(os.path.join(file_path))
    # 디코딩 한 블록을 저장한다.
    for height, curr_block in decoding(encoded_symbols, k, user_block_num):
        block_path = file_path + "/" + str(height) + ".block"
        with open(block_path, "wb") as file:
            file.write(curr_block)
    print("Decoded block saved at " + file_path)
    symbols= []

# =================================  수신서버 스레드 ======================================
# Symbol_Send_Request 메시지를 수신받아 가지고 있는 심볼을 전송하는 스레드
def handle_receive_send_symbol(client_socket, block_num):
    # 자신이 해당하는 블록의 심볼을 가지고 있는지 확인
    filepath = "c:/data/ltcodetest/node0/symboldata" + str(block_num - k + 1) + "-" + str(block_num)
    # 해당하는 블록의 심볼을 가지고 있지 않을 경우
    if not (os.path.isdir(filepath)):
        # 해당하는 심볼을 가지고 있지 않다고 알림
        client_socket.sendall(createHeader('Error', block_num))
        client_socket.close()
    # 해당하는 블록의 심볼을 가지고 있을 경우 심볼을 전송한다.
    else:
        Having_symbol_count = len(next(os.walk(filepath + "/"))[2])
        client_socket.sendall(createHeader('Symbol_Send_Start', user_block_num))  # 들어있는 블록의 마지막값 k = 50으로 고정
        header, dump = check_header(client_socket.recv(packet_size))  # Symbol_Receive_Ready 도착
        if header == Symbol_Receive_Ready:
            for i in range(Having_symbol_count):
                header = 0
                # 분산저장된 해당 블록의 데이터 블러오기
                symbol_path = filepath + "/" + str(i) + ".npy"
                file_symbols = np.load(symbol_path, allow_pickle=True).tolist()
                temp = createHeader('Symbols')
                temp = temp + struct.pack('ii', file_symbols.index, file_symbols.degree)
                temp = temp + file_symbols.data.tobytes()
                # 전송하는 심볼의 크기 전송
                client_socket.sendall(createHeader('Symbols', len(temp)))
                # 심볼 데이터 전송
                client_socket.sendall(temp)
                # 심볼의 크기가 커서 하나 보내고 받았는지 확인후 전송
                while header != Symbols_End:
                    msg = client_socket.recv(packet_size)
                    if not msg: continue
                    # header, dump = check_header(msg)
                    header = struct.unpack('i', msg[:4])[0]

            # 심볼 전송 완료 후 Symbol_Send_End msg 전송
            client_socket.sendall(createHeader('Symbol_Send_End'))
            msg, dump = check_header(client_socket.recv(packet_size))
            if msg == Symbol_Receive_End:
                print("Symbols Send process End, Sended ", Having_symbol_count, "Symbols")
        else:
            client_socket.sendall(createHeader('Error'))
        client_socket.close()

# Symbol_Send_Start 메시지를 수신 받아 인코딩된 심블을 받아 저장하는 스레드
def handle_receive_receive_symbol(client_socket, block_num):
    # 심볼을 저장할 준비가 되었다고 서버에 알림
    msg = 0
    symbol_count = 0
    client_socket.sendall(createHeader('Symbol_Receive_Ready'))
    # Symbol_Send_End 메시지 받을 때까지 반복
    while msg != Symbol_Send_End:
        recv = client_socket.recv(packet_size)
        # 빈소켓 수신시 continue
        if not recv: continue
        msg, length = check_header(recv[:8])  # length 는 심볼의 크기
        if msg == Symbols:
            # 해당 심볼이 저장될 임시 버퍼
            temp = b''
            while length:
                newbuf = client_socket.recv(length)
                if not newbuf: return None
                temp += newbuf
                length -= len(newbuf)
            index = struct.unpack('i', temp[8:12])[0]
            degree = struct.unpack('i', temp[12:16])[0]
            data = np.frombuffer(temp[16:], dtype=core.NUMPY_TYPE)
            symbol = Symbol(index=index, degree=degree, data=data)
            save_symbols(symbol, block_num, k, symbol_count)
            symbol_count += 1
            # 심볼 하나 받아서 저장했다고 알림
            client_socket.sendall(createHeader('Symbols_End'))

    # 전체 심볼 수신 완료 알림 + 서버측 소캣 종료
    client_socket.sendall(createHeader('Symbol_Receive_End'))
    print("Received ", symbol_count, "Symbols.")
    client_socket.close()

# =================================  송신 스레드 ======================================
def handle_send(conn, func, payload):
    # func == 1 : Encode and propagates symbols.
    # func == 2 : Receive symbols from nodes and decode.
    # global ClientCount, symbols
    global symbols, encoded_symbols, ClientCount, neighbor_port, user_block_num
    if func == 1:
        symbols_n = len(encoded_symbols)
        ClientCount = len(neighbor_port)
        # 클라이언트의 갯수만큼으로 심볼의 길이를 자른다.
        # ex 100개 심볼 4개 클라이언트 send_range = [0, 25, 50, 75, 100] -> index에 따라 위치 조정 0 이면 [0, 25]
        send_range = []
        send_range.append(0)
        for i in range(ClientCount - 1):
            send_range.append((symbols_n//ClientCount) * (i + 1))
        send_range.append(symbols_n)
        # 해당 클리이언트 별로 범위 지정
        index = neighbor_port.index(payload)
        send_range = [send_range[index], send_range[index + 1]]
        conn.sendall(createHeader('Symbol_Send_Start', user_block_num))     # 들어있는 블록의 마지막값 k = 50으로 고정
        header, dump = check_header(conn.recv(packet_size))      # Symbol_Receive_Ready 도착
        if header == Symbol_Receive_Ready:
            # 스레드에 입력된 포트의 index에 따라 맞는 심볼을 전송한다. 심볼의 크기도 같이 전송
            for curr_symbols in encoded_symbols[send_range[0]:send_range[1]]:
                header = 0
                temp = createHeader('Symbols')
                temp = temp + struct.pack('ii', curr_symbols.index, curr_symbols.degree)
                temp = temp + curr_symbols.data.tobytes()
                # 전송하는 심볼의 크기 전송
                conn.sendall(createHeader('Symbols', len(temp)))
                # 심볼 데이터 전송
                conn.sendall(temp)
                # 심볼의 크기가 커서 하나 보내고 받았는지 확인후 전송
                while header != Symbols_End:
                    msg = conn.recv(packet_size)
                    if not msg: continue
                    #header, dump = check_header(msg)
                    header = struct.unpack('i', msg[:4])[0]

            # 심볼 전송 완료 후 Symbol_Send_End msg 전송
            conn.sendall(createHeader('Symbol_Send_End'))
            msg, dump = check_header(conn.recv(packet_size))
            if msg == Symbol_Receive_End:
                print("Symbols Send process End: ", payload)
        else:
            conn.sendall(createHeader('Error'))
        encoded_symbols = []
        conn.close()
    elif func == 2:
        ClientCount = len(neighbor_port)
        conn.sendall(createHeader('Symbol_Send_Request', user_block_num))
        header, dump = check_header(conn.recv(packet_size))  # Symbol_Send_Start 도착
        if header == Symbol_Send_Start:
            msg = 0
            symbol_count = 0
            conn.sendall(createHeader('Symbol_Receive_Ready', user_block_num))
            while msg != Symbol_Send_End:
                recv = conn.recv(packet_size)
                # 빈소켓 수신시 continue
                if not recv: continue
                msg, length = check_header(recv[:8])  # length 는 심볼의 크기
                if msg == Symbols:
                    # 해당 심볼이 저장될 임시 버퍼
                    temp = b''
                    while length:
                        newbuf = conn.recv(length)
                        if not newbuf: return None
                        temp += newbuf
                        length -= len(newbuf)
                    index = struct.unpack('i', temp[8:12])[0]
                    degree = struct.unpack('i', temp[12:16])[0]
                    data = np.frombuffer(temp[16:], dtype=core.NUMPY_TYPE)
                    # 수신한 심볼을 symbols 리스트에 저장.
                    symbols.append(Symbol(index=index, degree=degree, data=data))
                    symbol_count += 1
                    # 심볼 하나 받아서 저장했다고 알림
                    conn.sendall(createHeader('Symbols_End'))
            print("Received From",payload, " ", symbol_count, "s Symbols End")
            # 전체 심볼 수신 완료 알림 + 서버측 소캣 종료
            conn.sendall(createHeader('Symbol_Receive_End'))
            conn.close()
            ClientCount -= 1
            # 모든 클라이언트로 부터 심볼을 받으면 디코딩 시작.
            if ClientCount == 0:
                decode_symbol(symbols, k, user_block_num)
        else:
            print("Receive message Error : ", header, "do not have", dump,"block symbols")


# ===================================== 메인 입력 ==========================================
def client():
    global ClientCount, user_block_num, host, encoded_symbols, redundancy, neighbor_port, k
    neighbor_port = ['5001', '5002', '5003']
    ClientCount = len(neighbor_port)
    k = 50          # 인코딩할 블록의 갯수
    while 1:
        print("*****************************************************************")
        print("*\t1. Encode and propagates symbols.\t\t\t*")
        print("*\t2. Receive symbols from nodes and decode.\t\t*")
        print("*****************************************************************")
        func = int(input("Enter function number : "))
        if (func != 1) and (func != 2):
            print("Please enter the correct function number.")
            continue

        # 이웃 port 설정 ip는 127.0.0.1 고정
        neighbor = int(input("If you don't want to use default port, Enter 0 (default = 5001, 5002, 5003): "))
        if neighbor == 0:
            user_port = input("Neighbor Node's Port num (input with space) : ")
            neighbor_port = user_port.split(" ")
            ClientCount = len(neighbor_port)

       # encode and propagate
        if func == 1:
            #k = int(input("Enter the number of blocks to encode : "))
            user_block_num = int(input("Enter last block number : "))
            # encoding start
            temp = read_blocks(user_block_num, k)
            drops_qunatity = len(temp) * redundancy
            for curr_symbols in encode(temp, drops_quantity= int(drops_qunatity)):
                encoded_symbols.append(curr_symbols)
            # 스레드 통한 tcp 연결 시작 이후 작업은 각 스레드에서 작업
            for port in neighbor_port:
                # IPv4 체계, TCP 타입 소켓 객체를 생성
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # 지정한 host와 prot를 통해 서버에 접속합니다.
                client_socket.connect((host, int(port)))
                # 스레드 생성
                print("make thread")
                send_thread = threading.Thread(target=handle_send, args=(client_socket, func, port))
                send_thread.daemon = True
                send_thread.start()
                # send_thread.join()
        elif func == 2:
            user_block_num = int(input("Enter block number you want: "))
            # user_block_num 은 해당 블록이 들어있는 범위로 수정 ex) 600030 -> 600050
            user_block_num = user_block_num + (k - (user_block_num % k))
            # 스레드 통한 tcp 연결 시작 이후 작업은 각 스레드에서 작업
            for port in neighbor_port:
                # IPv4 체계, TCP 타입 소켓 객체를 생성
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # 지정한 host와 prot를 통해 서버에 접속합니다.
                client_socket.connect((host, int(port)))
                # 스레드 생성
                print("make thread")
                send_thread = threading.Thread(target=handle_send, args=(client_socket, func, port))
                send_thread.daemon = True
                send_thread.start()
                # send_thread.join()



# ================================= 서버 생성 =============================================
def server_accept_func():
    global user_block_num
    # Client 입력 스레드
    notice_thread = threading.Thread(target=client, args=())
    notice_thread.daemon = True
    notice_thread.start()

    #IPv4 체계, TCP 타입 소켓 객체를 생성
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #포트를 사용 중 일때 에러를 해결하기 위한 구문
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #ip주소와 port번호를 함께 socket에 바인드 한다.
    #포트의 범위는 1-65535 사이의 숫자를 사용할 수 있다.
    server_socket.bind(('', port))
    #서버가 최대 5개의 클라이언트의 접속을 허용한다.
    server_socket.listen(5)
    #print("listen")
    while 1:
        try:
            #클라이언트 함수가 접속하면 새로운 소켓을 반환한다.
            client_socket, addr = server_socket.accept()
        except KeyboardInterrupt:
            for user, con in user_list:
                con.close()
            server_socket.close()
            print("Keyboard interrupt")
            break
        temp = client_socket.recv(packet_size)
        msg, payload = check_header(temp)
        #user_block_num = payload
        if msg == Symbol_Send_Request:
            # accept()함수로 입력만 받아주고 이후 알고리즘은 핸들러에게 맡긴다.
            # Server 수신 스레드
            print("run server thread")
            receive_thread = threading.Thread(target=handle_receive_send_symbol, args=(client_socket, payload))
            receive_thread.daemon = True
            receive_thread.start()
        elif msg == Symbol_Send_Start:
            # accept()함수로 입력만 받아주고 이후 알고리즘은 핸들러에게 맡긴다.
            # Server 수신 스레드
            print("run server thread")
            receive_thread = threading.Thread(target=handle_receive_receive_symbol, args=(client_socket, payload))
            receive_thread.daemon = True
            receive_thread.start()

if __name__== '__main__':
    parser = argparse.ArgumentParser(description="\nServer\n-p port\n")
    parser.add_argument('-p', help="port")

    args = parser.parse_args()
    try:
        port = int(args.p)
    except:
        pass
    server_accept_func()
