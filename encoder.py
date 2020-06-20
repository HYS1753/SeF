from core import *
from distributions import *

def get_degrees_from(distribution_name, N, k):
    """ 주어진 확률 분포에서 랜덤도를 반환한다. 도 분포는 포아송 분포처럼 보여야 하며 디코딩의 시작을 보장하기 위해 첫 번째 드롭의 정도는 1이다.
    :param distribution_name:  ideal, robust
    :param N: block size
    :param k: drop quantity
    :return: random degree 반환
    """

    if distribution_name == "ideal":
        probabilities = ideal_distribution(N)
    elif distribution_name == "robust":
        probabilities = robust_distribution(N)
    else:
        probabilities = None

    # population는 0 ~ 블록의 크기 +_1의 list이다.
    # ex. n = 100   -> [0, 1, 2, 3, 4, ... , 100]
    population = list(range(0, N+1))
    # random.choices(papulation, weight, k)
    # population에서 중복을 허락하면서 k크기(인코딩 후 심볼의 수)의 요소 리스트를 반환한다.
    # weight 시퀀스라 지정되면, 상대 가중치에 따라 선택된다.
    # population과 weight는 서로 같은 길이여야 한다.

    # 여기서는 첫번쨰는 무조건 1, decoding하기 위해, 나머지는 redundancies 개수 만큼
    # population에서 probabilities의 가중치에 따라 랜덤 초이스 한다.
    return [1] + choices(population, probabilities, k=k-1)
   
def encode(blocks, drops_quantity):
    """ Iterative encoding - Encodes new symbols and yield them.
    Encoding one symbol is described as follow:

    1.  Randomly choose a degree according to the degree distribution, save it into "deg"
        Note: below we prefer to randomly choose all the degrees at once for our symbols.

    2.  Choose uniformly at random 'deg' distinct input blocs. 
        These blocs are also called "neighbors" in graph theory.
    
    3.  Compute the output symbol as the combination of the neighbors.
        In other means, we XOR the chosen blocs to produce the symbol.

    :param blocks: 원본 데이터의 블록 list
    :param drops_quantity: drops크기
    :return:
    """

    # Display statistics
    blocks_n = len(blocks)
    # 랜덤한 이웃의 특성상, 최소한 같은 양의 block이 drop되어야 한다.
    # assert : 뒤에 나오는 조건이 참이 아니면 뒤에나오는 Error문을 반환한다.
    assert blocks_n <= drops_quantity, "Because of the unicity in the random neighbors, it is need to drop at least the same amount of blocks"

    print("Generating graph...")
    start_time = time.time()

    # Generate random indexes associated to random degrees, seeded with the symbol id
    # 0부터 블록의 길이 만큼 값이 들어있는 list에서 robust를 사용해 랜덤하게 drop_quantitiy개수 만큼 뽑아냄.
    # 아래의 경우 robust solition distibution, 블록의 길이, 드롭할 양
    # random_degrees는 즉 각 drop_quantitiy 마다 선택될 블록의 갯수이다.
    random_degrees = get_degrees_from("robust", blocks_n, k=drops_quantity)

    print("Ready for encoding.", flush=True)

    for i in range(drops_quantity):
        
        # Get the random selection, generated precedently (for performance)
        # 랜덤한 선택을 가저온다. core.py에 generate_index함수있다.
        # block_n의 인덱스 들 중 i를 통해 random.seed를 결정하고, random_Degrees[i]개를 뽑아 낸다.
        # selection_indexes는 선택된 블록 index, deg는 선택된 블록 갯수(random_degrees[i]) 이다.
        selection_indexes, deg = generate_indexes(i, random_degrees[i], blocks_n)

        # Xor each selected array within each other gives the drop (or just take one block if there is only one selected)
        # 선택된 array의 각 값을 xor한다.

        # drop은 원본 데이터 block에서 selection_index의 첫번째 값 번째 블록
        drop = blocks[selection_indexes[0]]
        # 첫번째의 degree를 제외한 갯수만큼 반복 xor
        for n in range(1, deg):
            # degree의 갯수만큼 선택된 블록들 끼리 xor 진행.
            drop = np.bitwise_xor(drop, blocks[selection_indexes[n]])
            # drop = drop ^ blocks[selection_indexes[n]] # according to my tests, this has the same performance

        # Create symbol, then log the process
        # index = drop_quantities의 index이자, random.seed의 값
        # degree = xor될 블록의 갯수
        # drop = 각 block을 xor한 값.
        symbol = Symbol(index=i, degree=deg, data=drop)

        # VERBOSE는 defalut False이므로 넘어감.
        if VERBOSE:
            symbol.log(blocks_n)

        # core.py에 지정된 log함수를 사용하여 표시함.
        log("Encoding", i, drops_quantity, start_time)

        # yield 는 return과 비슷한 것으로 반복문을 나가지 않고 한번의 흐름후 반환하는 값.
        yield symbol

    print("\n----- Correctly dropped {} symbols (packet size={})".format(drops_quantity, PACKET_SIZE))
