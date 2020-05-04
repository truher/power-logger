import timeit
import pandas as pd
import numpy as np
from typing import Dict,List

loops=1000

inputfile:List[List[int]] = [[1,2,3,4,5,6] for x in range(0,1000)]
# input arrives as a list of row lists
# need to make columns

#######################
# zip
# 60us
def i1() -> List[int]:
    return list(map(list, zip(*inputfile))) # type:ignore
t = timeit.timeit(i1,number=loops)
print(f'i1 transpose zip {1e6*t/loops} us')

#######################
# list
# 64us
def i2() -> List[List[int]]:
    return [list(i) for i in zip(*inputfile)]
t = timeit.timeit(i2,number=loops)
print(f'i2 transpose list {1e6*t/loops} us')

#######################
# append
# 64us
def i3() -> List[List[int]]:
    x = []
    for i in zip(*inputfile):
        x.append((list(i)))
    return x
t = timeit.timeit(i3,number=loops)
print(f'i3 transpose append {1e6*t/loops} us')

#######################
# list to col dict
# 50us (winner!), 318 with np.array
def i4() -> Dict[int, int]:
    return {x[0]:np.array(x[1]) for x in enumerate(zip(*inputfile))} #type:ignore
t = timeit.timeit(i4,number=loops)
print(f'i4 transpose list to dict {1e6*t/loops} us')

#######################
# list to dict to df
# should be 50+375 but is 1370.  743 if i do the np.array above
# this involves type conversion from series to ndarray
def g1() -> pd.DataFrame:
    return pd.DataFrame(i4()) #type:ignore
t = timeit.timeit(g1,number=loops)
print(f'g1 list to col dict to df {1e6*t/loops} us')

#######################
# dictionary of column lists
x1 = list(range(0,1000)) # skipping the np array step is cheating
y1 = {'a':x1,'b':x1,'c':x1,'d':x1,'e':x1,'f':x1}
# 375 us, 650 if i include np array
def f1() -> pd.DataFrame:
    y2 = {k:np.array(v) for (k,v) in y1.items()}
    return pd.DataFrame(y2)
t = timeit.timeit(f1,number=loops)
print(f'f1 col dict of list {1e6*t/loops} us')

#######################
# list of row lists (slow)
# this is the file format
x2 = [[1,2,3,4,5,6] for x in range(0,1000)]
# 1250 us (!)
def f2() -> pd.DataFrame:
    return pd.DataFrame(x2, columns=['a','b','c','d','e','f'])
t = timeit.timeit(f2,number=loops)
print(f'f2 list of row lists {1e6*t/loops} us')

#######################
# list of row dictionaries (slowest)
x3 = [{'a':x,'b':x,'c':x,'d':x,'e':x,'f':x} for x in range(0,1000)]
# 1590 us (!!)
def f3() -> pd.DataFrame:
    return pd.DataFrame(x3)
t = timeit.timeit(f3,number=loops)
print(f'f3 row dicts {1e6*t/loops} us')

#######################
# dictionary of column series
# this involves type conversion from series to ndarray
x4 = pd.Series(list(range(0,1000)))
y4 = {'a':x4,'b':x4,'c':x4,'d':x4,'e':x4,'f':x4}
# 335 us
def f4() -> pd.DataFrame:
    return pd.DataFrame(y4) #type:ignore
t = timeit.timeit(f4,number=loops)
print(f'f4 col dict of series {1e6*t/loops} us')
