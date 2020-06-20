from core import *

def ideal_distribution(N):
    """ Create the ideal soliton distribution. 
    In practice, this distribution gives not the best results
    Cf. https://en.wikipedia.org/wiki/Soliton_distribution
    """

    probabilities = [0, 1 / N]
    probabilities += [1 / (k * (k - 1)) for k in range(2, N+1)]
    probabilities_sum = sum(probabilities)

    assert probabilities_sum >= 1 - EPSILON and probabilities_sum <= 1 + EPSILON, "The ideal distribution should be standardized"
    return probabilities

def robust_distribution(N):
    """ Create the robust soliton distribution. 
    This fixes the problems of the ideal distribution
    Cf. https://en.wikipedia.org/wiki/Soliton_distribution
    """

    # The choice of M is not a part of the distribution ; it may be improved
    # We take the median and add +1 to avoid possible division by zero 
    M = N // 2 + 1 
    R = N / M

    extra_proba = [0] + [1 / (i * M) for i in range(1, M)]
    extra_proba += [math.log(R / ROBUST_FAILURE_PROBABILITY) / M]  # Spike at M
    extra_proba += [0 for k in range(M+1, N+1)]

    # np.add 는 각 요소를 더한다. extra_proba, idea_distribution(N)의 값을 더한다.
    probabilities = np.add(extra_proba, ideal_distribution(N))
    # np.sum 은 probabilities 의 모든 요소를 더한다.
    # 여기서는 각 probabilities 에 퍼센티지 구함(probabilities/전체 probabilities)
    probabilities /= np.sum(probabilities)
    # 전체 probabilities 의 합을 구한다.
    probabilities_sum = np.sum(probabilities)

    # 전체 probabilities 의 합이 앱실론EPSILON 값내에 들어오지 않을경우 ERROR 표시
    assert probabilities_sum >= 1 - EPSILON and probabilities_sum <= 1 + EPSILON, "The robust distribution should be standardized"
    # probabilities 반환
    # probabilities 의 갯수는 N 개 즉 블록의 갯수 (아님)
    # probabilities 는 확률 분호 random choice 하기위한.
    return probabilities
