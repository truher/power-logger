import numpy as np
import pandas as pd
import timeit
import itertools
from typing import List, IO
from numpy import int8, int64, ndarray
from numpy import uint8 # type: ignore[attr-defined]
import binascii

loops = 1000
t = 0.0 # type:float

# read 10 lines as bytes: 15us (winner)
def readfile1():
    # type: () -> List[bytes]
    with open('db10.csv', 'rb') as datafile: # type: IO[bytes]
        return datafile.readlines()
t = timeit.timeit(readfile1,number=loops)
print(f'readfile1 rb 10  elapsed time: {1e6*t/loops} us')

# read 10 lines as string: 23 (loser)
#def readfile3():
#    # type: () -> List[str]
#    with open('db10.csv', 'r') as datafile: # type: IO[str]
#        return datafile.readlines()
#t = timeit.timeit(readfile3,number=loops)
#print(f'readfile3 r 10 elapsed time: {1e6*t/loops} us')

# read 100 lines as bytes: 91us (winner)
def readfile2():
    # type: () -> List[bytes]
    with open('db100.csv', 'rb') as datafile: # type: IO[bytes]
        return datafile.readlines()
t = timeit.timeit(readfile2,number=loops)
print(f'readfile2 rb 100 elapsed time: {1e6*t/loops} us')

# read 100 lines as string: 104us (loser)
#def readfile4():
#    # type: () -> List[str]
#    with open('db100.csv', 'r') as datafile: # type: IO[str]
#        return datafile.readlines()
#t = timeit.timeit(readfile4,number=loops)
#print(f'readfile4 r 100 elapsed time: {1e6*t/loops} us')

# very slow, 2300 us
#def readfile6() -> pd.DataFrame:
#    return pd.read_csv('db100.csv', delim_whitespace=True, header=None,
#                       names=['one','two','three','four'])
#t = timeit.timeit(readfile6,number=loops)
#print(f'readfile6 pd 100 elapsed time: {1e6*t/loops} us')

observations = np.random.normal(0,30,1000).astype(int8) # type: ndarray[int8]
unsigned_observations = (observations+128).astype(uint8) # type: ndarray[uint8]
unsigned_observations_bytes = unsigned_observations.tobytes() # type: bytes

# 1.2us
#hex_encoded = unsigned_observations_bytes.hex() # type: str
#def f1():
#    # type: () -> str
#    return unsigned_observations_bytes.hex()
#t = timeit.timeit(f1,number=loops)
#print(f'f1 bytes.hex() elapsed time: {1e6*t/loops} us')


# 1.3us, fast enough i guess
#hexlified = binascii.hexlify(unsigned_observations_bytes) # type: bytes
def f2():
    # type: () -> bytes
    return binascii.hexlify(unsigned_observations_bytes)
t = timeit.timeit(f2,number=loops)
print(f'f2 binascii.hexlify() elapsed time: {1e6*t/loops} us')

def readfile5():
    # type: () -> List[bytes]
    with open('db1.csv', 'rb') as datafile: # type: IO[bytes]
        return datafile.readlines()

allrows = readfile5() # type: List[bytes]
onerow = allrows[0] # type: bytes
fields = onerow.split() # type: List[bytes]
observation_field = fields[3] # type: bytes

#hex_encoded = observation_field
#assert hex_encoded.encode() == hexlified


# 35us
#def f3a():
#    # type: () -> List[int]
#    return [y-128 for y in list(bytes.fromhex(hex_encoded))]
#t = timeit.timeit(f3a,number=loops)
#print(f'f3a bytes.fromhex elapsed time: {1e6*t/loops} us')

######################3
# decode from hex
# 35us, fast enough i guess, i think this could be faster.
decoded_fromhex = [y-128 for y in list(binascii.unhexlify(observation_field))] # type: List[int]
def f3():
    # type: () -> List[int]
    return [y-128 for y in list(binascii.unhexlify(observation_field))]
t = timeit.timeit(f3,number=loops)
print(f'f3 unhexlify elapsed time: {1e6*t/loops} us')


########################
# cumulative sum
# 20us, winner
def f4():
    # type: () -> List[int]
    return list(itertools.accumulate(decoded_fromhex))
t = timeit.timeit(f4,number=loops)
print(f'f4 accumulate elapsed time: {1e6*t/loops} us')


# 55us, loser, 106 with ndarray conversion, really loser
def f5():
    # type: () -> List[int]
    decoded_fromhex_ndarray = np.array(decoded_fromhex) # type: ndarray[int64]
    return list(np.ndarray.cumsum(decoded_fromhex_ndarray))
t = timeit.timeit(f5,number=loops)
print(f'f5 cumsum elapsed time: {1e6*t/loops} us')

##############################
# drop an item
l = list(range(0,1000))
# 25 us
def l1():
    # type: () -> List[int]
    return [x for x in l if x != 500]
t = timeit.timeit(l1,number=loops)
print(f'l1 del elapsed time: {1e6*t/loops} us')
