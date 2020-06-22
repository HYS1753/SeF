import pickle
import time
from decoder import decode

def recover_padding(dict, block ,block_n):
    """
    해당 블록의 padding을 지운다.
    :param dict: 헤더 체인
    :param block: padding을 제거할 블록
    :param block_n: 해당 블록 넘버
    :return: padding을 제거한 블록 반환
    """
    del_padding_block = b''
    padding_block = block.tobytes()            # block 안의 데이터는 np.uint64로 들어가 있어 바이트 단위로 변환
    size = dict[block_n][1]
    padding_block_size = len(padding_block)
    if padding_block_size != size:
        del_padding_block = padding_block[:size]
    return del_padding_block

def decoding(symbols, k, block_n):
    """
    심볼을 통해 디코딩 수행.
    :param symbols: 수신한 심볼들
    :param k: 원본 블록 수
    :param block_n: 디코딩 될 원본 블록의 범위
    :return: 해당 블록의 height,디코딩 된 블록을 하나하나 yield
    """
    # 블록의 헤더체인을 불렁온다. (size, muklroot, hash)
    filepath = "c:/data/ltcodetest/node0/header_chain.txt"
    with open(filepath, "rb") as file:
        header_dict = pickle.load(file)

    # 입력된 심볼을 통해 원본 블록으로 디코딩
    decode_start_time = time.time()
    recovered_blocks, recovered_n = decode(symbols, blocks_quantity=k)
    decode_end_time = time.time()
    print("decoding time : ", decode_end_time - decode_start_time)
    recover_block_num = block_n - k + 1     # 디코딩 한 블록의 height 지정
    for i in range(k):
        decoded_block = recover_padding(header_dict, recovered_blocks[i], recover_block_num)
        recover_block_num += 1
        yield recover_block_num - 1, decoded_block