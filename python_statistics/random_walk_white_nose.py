## ホワイトノイズ
%matplotlib inline
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

figsize = (20,8)
mean = 0
std = 1
num_samples = 1000
samples = np.random.normal(mean, std, size=num_samples)

plt.figure(figsize=figsize)
plt.plot(samples)
plt.show()

# この系列に関してDF検定してみると、自己相関がない。ということがわかるはず。
df = pd.DataFrame(samples)

## ランダムウォーク
def random_process():
    sample_size = 200
    a = 0
    y = 0
    disturbance_term = np.random.normal(size=sample_size)
    
    X, Y = [], []
    for i in range(0, sample_size):
        y = a + y + disturbance_term[i]
        X.append(i)
        Y.append(y)
        
    figsize = (20,8)
    plt.figure(figsize=figsize)
    plt.plot(X, Y, color='r')
    plt.show()
    
random_process()
