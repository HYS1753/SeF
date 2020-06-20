
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


# host(server의 IP)
host = '127.0.0.1'
# 서버로 요청한 클라이언트의 conn
user_list = {}
# 패킷의 크기
packet_size = 1040 #1040
# 요청한 블록 넘버
user_block_num = 0
# 심볼이 저장될 변수
symbols = []
# client count
ClientCount = 0
# 블록 size chain
block_size = {360:6849649, 635292:1225385}

def check_header(message):
    temp= struct.unpack('ii', message)
    header = temp[0]
    payload = temp[1]
    return header, payload

def decoding():
    global block_size
    global user_block_num
    global symbols
    size = block_size[user_block_num]
    file_path = "c:/data/ltcodetest/node0/" + str(user_block_num) + "-decoded.block"
    if (size % core.PACKET_SIZE == 0):
        block_n = size / core.PACKET_SIZE
    else:
        block_n = (size // core.PACKET_SIZE) + 1
    decode_start_time = time.time()
    recovered_blocks, recovered_n = decode(symbols, blocks_quantity=int(block_n))
    decode_end_time = time.time()
    print("decoding time : ", decode_end_time - decode_start_time)
    print("decoded file was saved at  ", file_path)
    # 복구된 블록을 copy파일에 저장.
    with open(file_path, "wb") as file_copy:
        #print("\n\nrecovered block lendght" , len(recovered_blocks), recovered_n)
        blocks_write(recovered_blocks, file_copy, size)
    # 심볼 초기화
    symbols = []

def handle_receive(client_socket, addr):
    # 해당 블록이 자신이 가진 블록인지 확인
    if user_block_num in block_size:
        raw_size = block_size[user_block_num]
        client_socket.sendall(createHeader('Symbol_Send_Start', raw_size))
        msg, payload = check_header(client_socket.recv(packet_size))
        if msg == Symbol_Receive_Ready:
            # 분산저장된 해당 블록의 데이터 블러오기
            symbol_path = "c:/data/ltcodetest/node0/" + str(user_block_num) + ".block"
            file_symbols = np.load(symbol_path, allow_pickle=True).tolist()
            for curr_symbols in file_symbols:
                temp = createHeader('Symbols')
                temp = temp + struct.pack('ii', curr_symbols.index, curr_symbols.degree)
                temp = temp + curr_symbols.data.tobytes()
                client_socket.sendall(temp)
            # 자신이 가지고 있는 심볼 전송 완료시 전송완료 msg 전송
            client_socket.sendall(createHeader('Symbol_Send_End'))
            msg, payload = check_header(client_socket.recv(packet_size))
            if msg == Symbol_Receive_End:
                print("Symbols Send process End")
    else:
        client_socket.sendall(createHeader('Error', user_block_num))
    # 전송 완료 또는 오류시 접속 종료.
    client_socket.close()

def handle_send(conn, user_block_num):
    global ClientCount, symbols
    # print("connected")
    # print(conn)
    conn.sendall(createHeader('Symbol_Send_Request', user_block_num))
    header, payload = check_header(conn.recv(packet_size))      # Symbol_Send_Start, 원본 파일 크기 받음
    #print(header, payload)
    block_size[user_block_num] = payload
    if header == Symbol_Send_Start:
        conn.sendall(createHeader('Symbol_Receive_Ready'))
        while header != Symbol_Send_End:
            recv = conn.recv(packet_size)
            header, payload = check_header(recv[:8])
            if header == Symbols:
                index = struct.unpack('i', recv[8:12])[0]
                degree = struct.unpack('i', recv[12:16])[0]
                if len(recv) == packet_size:
                    data = np.frombuffer(recv[16:], dtype=core.NUMPY_TYPE)
                    # print(index, degree) # 수신한 심볼 확인
                    symbols.append(Symbol(index=index, degree=degree, data=data))

        conn.sendall(createHeader('Symbol_Receive_End', user_block_num))
        conn.close()
        ClientCount -= 1
        print("심볼의 길이:",len(symbols))
        print("Remain count: ", ClientCount)
        if ClientCount == 0:
            decoding()
        #if len(symbols) == (block_n * 2):
        #    decoding()

def client():
    global ClientCount, user_block_num, host
    while 1:
        user_block_num = int(input("Enter the block number you want : "))
        if user_block_num == 0:
            break
        user_port = input("Neighbor Node's Port num (input with space) : ")
        user_port_list = user_port.split(" ")
        ClientCount = len(user_port_list)
        for port in user_port_list:
            # IPv4 체계, TCP 타입 소켓 객체를 생성
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 지정한 host와 prot를 통해 서버에 접속합니다.
            client_socket.connect((host, int(port)))
            # 스레드 생성
            #client_socket.sendall(str(user_block_num).encode())
            print("make thread")
            send_thread = threading.Thread(target=handle_send, args=(client_socket, user_block_num))
            send_thread.daemon = True
            send_thread.start()
            #send_thread.join()


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
        user_block_num = payload
        if msg == Symbol_Send_Request:
            # accept()함수로 입력만 받아주고 이후 알고리즘은 핸들러에게 맡긴다.
            # Server 수신 스레드
            print("run server thread")
            receive_thread = threading.Thread(target=handle_receive, args=(client_socket, addr))
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
