import os
import sys
import math
import time
import numpy as np
import random
from random import choices

SYSTEMATIC = False
VERBOSE = False
# PACKET_SIZE = 65536
# PACKET_SIZE = 32768
# PACKET_SIZE = 16384
# PACKET_SIZE = 4096
PACKET_SIZE = 1024
# PACKET_SIZE = 512
# PACKET_SIZE = 128
ROBUST_FAILURE_PROBABILITY = 0.01
NUMPY_TYPE = np.uint64
# NUMPY_TYPE = np.uint32
# NUMPY_TYPE = np.uint16
# NUMPY_TYPE = np.uint8
EPSILON = 0.0001
##########################
Symbol_Send_Request = 0x01      # 심볼 요청
Symbol_Send_Start = 0x02        # 심볼 전송한다고 알림
Symbol_Receive_Ready = 0x03     # 심볼 수신 준비 완료
Symbol_Send_End = 0x04          # 심볼 전송 완료
Symbol_Receive_End = 0x05       # 심볼 수신 완료
Error = 0x06
Symbols = 0x00
Symbols_End = 0x07
Symbols_Size = 0x08

# symbol 클래스
class Symbol:
    __slots__ = ["index", "degree", "data", "neighbors"] # fixing attributes may reduce memory usage

    def __init__(self, index, degree, data):
        self.index = index
        self.degree = degree
        self.data = data

    def log(self, blocks_quantity):
        neighbors, _ = generate_indexes(self.index, self.degree, blocks_quantity)
        print("symbol_{} degree={}\t {}".format(self.index, self.degree, neighbors))

def generate_indexes(symbol_index, degree, blocks_quantity):
    """Randomly get `degree` indexes, given the symbol index as a seed

    Generating with a seed allows saving only the seed (and the amount of degrees) 
    and not the whole array of indexes. That saves memory, but also bandwidth when paquets are sent.

    The random indexes need to be unique because the decoding process uses dictionnaries for performance enhancements.
    Additionnally, even if XORing one block with itself among with other is not a problem for the algorithm, 
    it is better to avoid uneffective operations like that.

    To be sure to get the same random indexes, we need to pass

    :param symbol_index: drop_quantity 의 index
    :param degree: xor된 원본 block의 갯수.
    :param blocks_quantity: 원본 데이터의 블록 겟수
    :return: xor된 원본 데이터의 block index와 degree 갯수 반환.
    """
    # 기본 값으로 SYSTEMAIC이 False이므로 else 부분만 실행.
    if SYSTEMATIC and symbol_index < blocks_quantity:
        indexes = [symbol_index]               
        degree = 1     
    else:
        # seed를 통해 random 사용할시 동일한 값이 나오도록 설정한다.
        random.seed(symbol_index)
        # indexes는 xor될 blocks들의 번호이다.
        # random.sample은 중복되지 않는 랜덤값을 반환한다.
        # 따라서 여기서는 원본의 블록들 중, degree의 갯수만큼 골라서 반환한다.
        indexes = random.sample(range(blocks_quantity), degree)

    return indexes, degree

# log 함수
# process: 해당 프로세스 명
# iteration :  전체 중 몇 번째 인지. ex) encode시 drop_quantities중 몇 번째 인지.
# total: drop_quantities개수
def log(process, iteration, total, start_time):
    """Log the processing in a gentle way, each seconds"""
    # 전역 변수로 log_actual_time지정
    global log_actual_time

    # 글로벌 심볼 테이블에서 log_actual_time이 존재하지 않을경우. 즉, 처음 이 함수를 실행 할 때.
    if "log_actual_time" not in globals():
        # 현재 시간을 log_actual_time에 저장.
        log_actual_time = time.time()

    # log 함수 호출 할때 처음보다 1초 지났거나, 마지막 블록일시 실행
    if time.time() - log_actual_time > 1 or iteration == total - 1:
        # 현재의 시간
        log_actual_time = time.time()
        # machine epsilon 은 부동소수점 연산에서 반올림함으로 초차의 상한값.
        elapsed = log_actual_time - start_time + EPSILON    # 지난 시간.
        speed = (iteration + 1) / elapsed * PACKET_SIZE / (1024 * 1024)

        print("-- {}: {}/{} - {:.2%} symbols at {:.2f} MB/s       ~{:.2f}s".format(
            process, iteration + 1, total, (iteration + 1) / total, speed, elapsed), end="\r", flush=True)