import matplotlib.pyplot as plt
import glob
import numpy as np
from scipy.interpolate import interp1d

X, Y = [], []
for fn in glob.glob('d.*'):
  for line in open(fn, 'r'):
    values = [float(s) for s in line.split()]
    X.append(values[0])
    Y.append(values[1])
plt.plot(X, Y,'o')

X1 = np.linspace(np.amin(X), np.amax(X), num=1001, endpoint=True)
Y1 = interp1d(X,Y,kind='nearest')
plt.plot(X1, Y1(X1))

plt.show()
