# 파일을 읽어오고 저장하는 py
import math
import core
import numpy as np


def blocks_read(file, filesize):
    # 블록의 갯수를 filesize/cor.PACKET_SIZE(core.py에 정의됨 기본 65536) 로 나누어 구한다.
    blocks_n = math.ceil(filesize / core.PACKET_SIZE)
    # 파일을 블록단위로 나누어 저장될 배열 선언
    blocks = []

    # 블록 갯수 만큼 반복
    for i in range(blocks_n):
        # data 변수에 bytearray로 파일을 패킷 크기만큼씩 읽어서 저장.
        data = bytearray(file.read(core.PACKET_SIZE))
        # 파일 변수에 데이터가 존재 하지 않을경우 raise로 예외 처리
        if not data:
            raise "stop"

        if len(data) != core.PACKET_SIZE:
            # 부족한 data길이에 정해진 PACKET_SIZE 만큼 0으로 채운다.
            data = data + bytearray(core.PACKET_SIZE - len(data))
            # 마지막 블록일 경우 마지막 블록 위치와 처리되지 못한 바이트크기를 알림해 줌.
            assert i == blocks_n - 1, "Packet #{} has a not handled size of {} bytes".format(i, len(blocks[i]))

        # block[]에 data를 추가함
        blocks.append(np.frombuffer(data, dtype=core.NUMPY_TYPE))

    # blocks[]로 나뉘어진 파일 배열을 반환한다.
    return blocks

def blocks_write(blocks, file, filesize):
    """ Write the given blocks into a file
    # 디코딩되어 저장될 파일에 데이터 저장하는 함수
    # blocks : 디코딩되어 출력된 blocks들
    # file : 디코딩된 파일이 저장될 open 된 file
    # filesize : 원본 데이터(인코딩되기 전)의 데이터 크기.
    """

    count = 0
    # 마지막 블록을 제외한 나머지 블록을 file에 쓴다.
    for data in blocks[:-1]:
        file.write(data)
        count += len(data)

    # Convert back the bytearray to bytes and shrink back
    # 마지막 블록에 대해 bytearray를 바이트로 다시 변환하고 축소한다.

    # 원본상에는 bytes(recovered_blocks[-1])로 표기 되어 있지만, 이로 했을시
    # TypeError: only integer scalar arrays can be converted to a scalar index 와 같은 오류 출력하며
    # 마지막 block이 제대로 write되지 못해 파일이 손상되는 문제 있음.
    #last_bytes = np.array((blocks[-1])) # 마지막 블록을 array로 저장함.
    last_bytes = np.array(blocks[-1]).tobytes()
    # filesize % core.PACKET_SIZE = 파일크기를 페킷 크기로 나눈 나머지, 즉 마지막 블록에서 필요한 데이터부분.
    shrinked_data = last_bytes[:filesize % core.PACKET_SIZE]
    file.write(shrinked_data)