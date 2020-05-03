import timeit
import numpy as np #type:ignore
from typing import List,Any
import itertools
import collections
from scipy.interpolate import interp1d #type:ignore

loops=1000

# data
#d = np.random.uniform(0,1,1000)    
d = np.linspace(0,999,1000)    
fp = list(d)
xp = np.linspace(0,999,1000)
# interp x axis (in-between points)
x = np.linspace(0,999,1999)
# 177 us, in between points
def f1() -> Any:
    return list(np.interp(x, xp, fp))
#print(len(f1()))
#print(f1())
t = timeit.timeit(f1,number=loops)
print(f'f1 interp {1e6*t/loops} us')

# 175us in between points
def f1a() -> Any:
    #ff = interp1d(xp, d, fill_value='extrapolate')
    ff = interp1d(xp, d)
    return list(ff(x))
#print(len(f1a()))
#print(f1a())
t = timeit.timeit(f1a,number=loops)
print(f'f1a interp1d {1e6*t/loops} us')

# interp x axis (trailing points)
xt = np.linspace(0,999.5,2000)
# 177 us, constant extrapolation (repeat last)
def f1t() -> Any:
    return list(np.interp(xt, xp, fp))
#print(len(f1t()))
#print(f1t())
t = timeit.timeit(f1t,number=loops)
print(f'f1t interp repeat last {1e6*t/loops} us')

# does not work off the end without fill_value
# linear extrapolation
# 222 us (slow!)
def f1ta() -> Any:
    ff = interp1d(xp, d, fill_value='extrapolate')
    #ff = interp1d(xp, d)
    return list(ff(xt))
#print(len(f1ta()))
#print(f1ta())
t = timeit.timeit(f1ta,number=loops)
print(f'f1ta interp1d extrapolation {1e6*t/loops} us')


interp = f1()

# very slow, 13 us
def f2(): # type:ignore
    return list(itertools.chain([interp[0]],interp))

t = timeit.timeit(f2,number=loops)
print(f'f2 chain {1e6*t/loops} us')

# slow, 3 us
def f3(): # type:ignore
    foo = [interp[0]]
    foo.extend(interp)
    return foo

t = timeit.timeit(f3,number=loops)
print(f'f3 extend {1e6*t/loops} us')

# 0.1us
def f4(): # type:ignore
    foo = interp
    foo.append(interp[0])
    return foo

t = timeit.timeit(f4,number=loops)
print(f'f4 append {1e6*t/loops} us')

# winner, 1us
def f5(): # type:ignore
    foo = interp
    foo.insert(0, interp[0])
    return foo

t = timeit.timeit(f5,number=loops)
print(f'f5 insert {1e6*t/loops} us')

###########################33
# pop
d6 = d.copy()
# 0.2us
def f6(): # type:ignore
    fd6 = list(d6)
    fd6.pop(0)
    return fd6

t = timeit.timeit(f6,number=loops)
print(f'f6 pop {1e6*t/loops} us')

###########################33
# slice
d7 = d.copy()
# 1.6us
def f7(): # type:ignore
    #fd7 = list(d7)
    return d7[1:]

t = timeit.timeit(f7,number=loops)
print(f'f7 slice {1e6*t/loops} us')

d8 = list(d.copy())
# 72us materialize and pop
def f8(): # type:ignore
    return list(itertools.accumulate(d8)).pop(0)

t = timeit.timeit(f8,number=loops)
print(f'f8 pop {1e6*t/loops} us')

d9 = list(d.copy())
# 76us islice and materialize (about the same)
def f9(): # type:ignore
    return list(itertools.islice(itertools.accumulate(d9), 1, None))

t = timeit.timeit(f9,number=loops)
print(f'f9 islice {1e6*t/loops} us')



