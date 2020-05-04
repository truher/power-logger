import timeit
import numpy as np
from typing import List, Iterable
import itertools
import collections
from scipy.interpolate import interp1d #type:ignore

loops=1000

# data
d = np.linspace(0,999,1000)    
fp = list(d)
xp = np.linspace(0,999,1000)
# interp x axis (in-between points)
x = np.linspace(0,999,1999)

# 177 us, in between points
def f1() -> List[np.float64]:
    return list(np.interp(x, xp, fp)) #type:ignore
t = timeit.timeit(f1,number=loops)
print(f'f1 interp {1e6*t/loops} us')

# 175us in between points
def f1a() -> List[np.float64]:
    ff = interp1d(xp, d)
    return list(ff(x))
t = timeit.timeit(f1a,number=loops)
print(f'f1a interp1d {1e6*t/loops} us')

# interp x axis (trailing points)
xt = np.linspace(0,999.5,2000)
# 177 us, constant extrapolation (repeat last)
def f1t() -> List[np.float64]:
    return list(np.interp(xt, xp, fp)) #type:ignore
t = timeit.timeit(f1t,number=loops)
print(f'f1t interp repeat last {1e6*t/loops} us')

# does not work off the end without fill_value
# linear extrapolation
# 222 us (slow!)
def f1ta() -> List[np.float64]:
    ff = interp1d(xp, d, fill_value='extrapolate')
    return list(ff(xt))
t = timeit.timeit(f1ta,number=loops)
print(f'f1ta interp1d extrapolation {1e6*t/loops} us')


interp = f1()

# very slow, 13 us
def f2() -> List[np.float64]:
    return list(itertools.chain([interp[0]],interp))

t = timeit.timeit(f2,number=loops)
print(f'f2 chain {1e6*t/loops} us')

# slow, 3 us
def f3() -> List[np.float64]:
    foo = [interp[0]]
    foo.extend(interp)
    return foo

t = timeit.timeit(f3,number=loops)
print(f'f3 extend {1e6*t/loops} us')

# 0.1us
def f4() -> List[np.float64]:
    foo = interp
    foo.append(interp[0])
    return foo

t = timeit.timeit(f4,number=loops)
print(f'f4 append {1e6*t/loops} us')

# winner, 1us
def f5() -> List[np.float64]:
    foo = interp
    foo.insert(0, interp[0])
    return foo

t = timeit.timeit(f5,number=loops)
print(f'f5 insert {1e6*t/loops} us')

###########################33
# pop
d6 = d.copy()
# 0.2us
def f6() -> List[np.float64]:
    fd6 = list(d6)
    fd6.pop(0)
    return fd6

t = timeit.timeit(f6,number=loops)
print(f'f6 pop {1e6*t/loops} us')

###########################33
# slice
d7 = d.copy()
# 1.6us
def f7():
    # type: () -> np.ndarray[np.float64]
    return d7[1:]

t = timeit.timeit(f7,number=loops)
print(f'f7 slice {1e6*t/loops} us')

d8:List[np.float64] = list(d.copy())
# 72us materialize and pop
def f8() -> np.float64:
    return list(itertools.accumulate(d8)).pop(0)

t = timeit.timeit(f8,number=loops)
print(f'f8 pop {1e6*t/loops} us')

d9:List[np.float64] = list(d.copy())
# 76us islice and materialize (about the same)
def f9() -> Iterable[float]:
    return list(itertools.islice(itertools.accumulate(d9), 1, None))

t = timeit.timeit(f9,number=loops)
print(f'f9 islice {1e6*t/loops} us')
