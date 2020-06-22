# encoding 프로세스 관련 함수
# 전송하는 자는 각 블록에 padding을 추가하고 블록화 시켜서 반환하는함수
# 수신하는 자는 받은 심볼을 각 파일로 저장하는 함수.
import core
from core import *


# max_block_size에 맞추어 블록 크기를 조정한다.
def block_padding(raw_data, max_block_size):
    curr_block_size = len(raw_data)
    if curr_block_size != max_block_size:
        # 해당 블록의 최대 크기가 맞지 않을 경우 리스트 내의 가장 큰 값의 길이가 되도록 0 채워 넣음
        temp = raw_data + bytearray(max_block_size - curr_block_size)
        return np.frombuffer(temp, dtype=core.NUMPY_TYPE)
    else:
        return np.frombuffer(raw_data, dtype=core.NUMPY_TYPE)


# 입력된 블록 높이까지 k개의 블록을 읽어와 padding을 추가한 일정한 크기의 블록을 만든다.
def read_blocks(blockheight, k):
    raw_blocks = []     # 원본 데이터 블록이 들어갈 list
    blocks_size = []    # 원본 데이터 블록의 크기 들어갈 list
    padding_blocks = []
    # 해당 블록을 배열에 넣는다.
    for i in range(blockheight - k + 1, blockheight + 1):
        file_path = "c:/data/ltcodetest/node0/blocks/" + str(i) + ".block"
        with open(file_path, "rb") as file:
            temp = bytearray(file.read())
            raw_blocks.append(temp)
            blocks_size.append(len(temp))
    # np.dtype => np.uint64를 맞추기 위해 사이즈 조정 (np.uint64 = 8bytes)
    max_block_size = max(blocks_size)
    print(max_block_size)
    if (max_block_size % 8) != 0:
        max_block_size = max_block_size + (8 - (max_block_size % 8))
    print(max_block_size)
    # 입력된 블록의 갯수 만큼 padding 추가
    for i in range(k):
        padding_blocks.append(block_padding(raw_blocks[i], max_block_size))

    return padding_blocks

def save_symbols(symbol, block_num, k, count):
    filepath = "c:/data/ltcodetest/node0/symboldata"+ str(block_num - k + 1) + "-" + str(block_num)
    # 해당 위치에 폴더가 없을경우 생성
    if not (os.path.isdir(filepath)):
        os.makedirs(os.path.join(filepath))
    filepath = filepath + "/" + str(count)
    np.save(filepath, symbol)
