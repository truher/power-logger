import timeit
import numpy as np #type:ignore
import json
import orjson
import binascii

loops=1000

rng = np.random.default_rng()
# ndarray int32 because orjson
xnp = rng.integers(1023,size=1000,dtype=np.uint32)
ynp = rng.integers(1023,size=1000,dtype=np.uint32)
x = list([x.item() for x in xnp])
y = list([x.item() for x in ynp])


#######################
# list zip json
# 988us (slow!)
def f2() -> str:
    z =z=[{'x':a,'y':b} for (a,b) in zip(x,y)]
    zz=[{'label':'a', 'data':z}, {'label':'b', 'data':z}]
    return json.dumps(zz)
t = timeit.timeit(f2,number=loops)
print(f'f2 list zip json {1e6*t/loops} us')

#######################
# list zip f
# 724 us even simple operations are slow
def f1() -> str:
    z = [{'x':a,'y':b} for (a,b) in zip(x,y)]
    return f"[{{'label':'a', 'data':{z} }}, {{'label':'b', 'data':{z} }}]"
t = timeit.timeit(f1,number=loops)
print(f'f1 list zip f {1e6*t/loops} us')

#######################
# list zip orjson
# 212 us orjson much faster than f
def f3() -> bytes:
    z = [{'x':a,'y':b} for (a,b) in zip(x,y)]
    zz=[{'label':'a', 'data':z}, {'label':'b', 'data':z}]
    return orjson.dumps(zz)
t = timeit.timeit(f3,number=loops)
print(f'f3 list zip orjson {1e6*t/loops} us')

########################
# list f, parallel lists
# 201 us avoid zip, save 500us
def f0() -> str:
    return f"[{{'label':'a', 'x':{x}, 'y':{y} }}, {{'label':'b', 'x':{x}, 'y':{y} }}]"
t = timeit.timeit(f0,number=loops)
print(f'f0 list f parallel {1e6*t/loops} us')

#######################
# just tobytes, needs encoded
# 116 us, avoid integer serialization
def f4() -> str:
    xnpb = binascii.hexlify(xnp.tobytes())
    ynpb = binascii.hexlify(ynp.tobytes())
    return f"[{{'label':'a', 'x':{xnpb!r}, 'y':{ynpb!r} }}, {{'label':'b', 'x':{xnpb!r}, 'y':{ynpb!r} }}]"
t = timeit.timeit(f4,number=loops)
print(f'f4 ndarray tobytes f {1e6*t/loops} us')

#######################
# zip orjson ndarray -- orjson can't handle numpy types outside numpy arrays
# 60us
#def f5() -> str:
#    z = [{'x':a,'y':b} for (a,b) in zip(xnp,ynp)]
#    zz=[{'label':'a', 'data':z}, {'label':'b', 'data':z}]
#    return orjson.dumps(zz, option=orjson.OPT_SERIALIZE_NUMPY)
#t = timeit.timeit(f5,number=loops)
#print(f'f5 ndarray zip orjson {1e6*t/loops} us')


#####################
# parallel list orjson
# 57 us avoid zip, save 150 us
def f7() -> bytes:
    zz = [{'label':'a', 'x':x, 'y':y }, {'label':'b', 'x':x, 'y':y }]
    return orjson.dumps(zz, option=orjson.OPT_SERIALIZE_NUMPY)
t = timeit.timeit(f7,number=loops)
print(f'f7 parallel list orjson {1e6*t/loops} us')

#######################
# parallel orjson ndarray
# 28 us (fastest), simplest is best
def f6() -> bytes:
    zz = [{'label':'a', 'x':xnp, 'y':ynp }, {'label':'b', 'x':xnp, 'y':ynp }]
    return orjson.dumps(zz, option=orjson.OPT_SERIALIZE_NUMPY)
t = timeit.timeit(f6,number=loops)
print(f'f6 parallel ndarray orjson {1e6*t/loops} us')
