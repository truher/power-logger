# mypy: disallow-untyped-globals

from typing import List
import numpy as np

#x:List[int] = [1,2]
x = [1,2]
print(type(x))
y: int = 1
print(y)
z: np.uint8 = y
print(z)

def f(x:int) -> int:
    return x
