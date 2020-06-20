from core import *

def recover_graph(symbols, blocks_quantity):
    """ Get back the same random indexes (or neighbors), thanks to the symbol id as seed.
    For an easy implementation purpose, we register the indexes as property of the Symbols objects.
    심볼에 정의되어있는 Seed를 통해 각 심볼이 xor된 원본 데이터블록의 이웃들을 구한다.
    :param symbols: 인코딩 되어있는 심볼들의 list
    :param blocks_quantity: 원본 데이터의 블록 갯수
    :return: 원본데이터의 블록들 중 몇 번째 블록이 xor 되었는지를 표현하는 neighbors를 추가해 반환한다.
    """

    for symbol in symbols:
        # 심볼에 포함되어있는 index(seed), degree(xor된 블록 갯수), block_quantity(원본 데이터 블록 수)
        # 를 통해서 각 심볼에 xor된 원본 데이터의 이웃들(neighbors)과 그 갯수(deg)를 반환한다.
        neighbors, deg = generate_indexes(symbol.index, symbol.degree, blocks_quantity)
        # neighbors에 있는 값 전부 symbos.neighbors에 저장.
        symbol.neighbors = {x for x in neighbors}
        symbol.degree = deg

        # VERBOSE 는 False 이므로 생략
        if VERBOSE:
            symbol.log(blocks_quantity)
    # symbols 반환.
    return symbols

def reduce_neighbors(block_index, blocks, symbols):
    """ Loop over the remaining symbols to find for a common link between 
    each symbol and the last solved block `block`

    To avoid increasing complexity and another for loop, the neighbors are stored as dictionnary
    which enable to directly delete the entry after XORing back.
    :param block_index: 복원된 원본 블록의 블록 index 값
    :param blocks: 복원할 원본 블록의 tuple
    :param symbols: 인코딩되어있는 symbols
    :return: x
    """
    # 남은 symbols들을 반복해서 작업
    for other_symbol in symbols:
        # 남은 심봄들중 degree가 1보다 크고, 복원된 원본 블록의 블록 index값을 neighbors로 가지는 심볼만 수행.
        if other_symbol.degree > 1 and block_index in other_symbol.neighbors:
        
            # XOR the data and remove the index from the neighbors
            # 데이터를 XOR해서 neighbors에 있는 원본 블록의 블록 index 값을 지운다.
            # data = 기존의 데이터 ^ 복원된 원본 블록의 값.
            other_symbol.data = np.bitwise_xor(blocks[block_index], other_symbol.data)
            # neighbors에서 복원된 원본 블록의 index를 지운다.
            other_symbol.neighbors.remove(block_index)
            # xor 후 해당 심볼의 degree를 1 줄임.
            other_symbol.degree -= 1
            # VERBOSE는 False이므로 수행하지 않음.
            if VERBOSE:
                print("XOR block_{} with symbol_{} :".format(block_index, other_symbol.index), list(other_symbol.neighbors.keys())) 


def decode(symbols, blocks_quantity):
    """ Iterative decoding - Decodes all the passed symbols to build back the data as blocks. 
    The function returns the data at the end of the process.
    
    1. Search for an output symbol of degree one
        (a) If such an output symbol y exists move to step 2.
        (b) If no output symbols of degree one exist, iterative decoding exits and decoding fails.
    
    2. Output symbol y has degree one. Thus, denoting its only neighbour as v, the
        value of v is recovered by setting v = y.

    3. Update.

    4. If all k input symbols have been recovered, decoding is successful and iterative
        decoding ends. Otherwise, go to step 1.

    :param symbols: 인코딩된 심볼들
    :param blocks_quantity: 원본 데이터의 블록수
    :return:
    """

    symbols_n = len(symbols)    # 심볼의 갯수
    # 심볼의 갯수가 0보다 크지 않으면 Error출력
    assert symbols_n > 0, "There are no symbols to decode."

    # We keep `blocks_n` notation and create the empty list
    blocks_n = blocks_quantity  # 원본 데이터의 블록수를 block_n 으로 함
    blocks = [None] * blocks_n  # blocks를 원본데이터의 블록수 만큼 None으로 채워서 초기화.

    # Recover the degrees and associated neighbors using the seed (the index, cf. encoding).
    # seed를 사용하여 디그리들과 관련된 이웃 을 복구한다. 즉, 각 심볼에 neighbor들을 추가해줌.
    symbols = recover_graph(symbols, blocks_n)
    print("Graph built back. Ready for decoding.", flush=True)

    # 원본으로 복원한 블록의 갯수
    solved_blocks_count = 0
    # 복원하는데 반복한 횟수.
    iteration_solved_count = 0
    start_time = time.time()

    # 복원한 블록의 갯수가 0개 이거나 반복한 횟수가 0보다 클때.
    while iteration_solved_count > 0 or solved_blocks_count == 0:
    
        iteration_solved_count = 0

        # Search for solvable symbols
        # enumerate 함수는 반복문 사용시 몇 번째인지 알수 있도록 i에 인덱스 번호와 symbol 에 컬렉션 원소를 반환.
        for i, symbol in enumerate(symbols):

            # Check the current degree. If it's 1 then we can recover data
            # 해당 심볼의 현재 degree를 확인해서 1이면 복원 가능하다.
            if symbol.degree == 1: 

                iteration_solved_count += 1
                # block_index에 symbol.neighbors를 분리해 다음 이웃의 index를 저장.
                # ex ) next(iter(range(3))일 경우 호출할 때 마다 0, 1, 2 출력
                block_index = next(iter(symbol.neighbors))
                # symbols에서 i번째 를 pop(리턴하면서 삭제) 한다.
                symbols.pop(i)

                # This symbol is redundant: another already helped decoding the same block
                # blocks[block_index] 가 None이 아니면 이미 디코딩 된 블록이므로 continue한다.
                if blocks[block_index] is not None:
                    continue

                # blaocks에 디코딩된 값 저장.
                blocks[block_index] = symbol.data

                # VERBOSE 는 False 이므로 무시하고 진행.
                if VERBOSE:
                    print("Solved block_{} with symbol_{}".format(block_index, symbol.index))
              
                # Update the count and log the processing
                solved_blocks_count += 1
                log("Decoding", solved_blocks_count, blocks_n, start_time)

                # Reduce the degrees of other symbols that contains the solved block as neighbor
                # 복원된 블록을 이웃으로 가지는 다른 심볼의 degree를 줄인다.
                # block_index = 이번에 원본 블록으로 복원된 블록의 index값.
                # blocks = 원본 블록이될 tuple
                # symbols = 인코딩 되어있는 심볼들
                reduce_neighbors(block_index, blocks, symbols)

    print("\n----- Solved Blocks {:2}/{:2} --".format(solved_blocks_count, blocks_n))
    # np.asarray : blocks를 array형태로 변환하여 출력,
    return np.asarray(blocks), solved_blocks_count