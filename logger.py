#!/usr/bin/env python

import datetime, serial, string

ids = [ "5737333034370D0E14", "5737333034370A220D" ]

def header():
  h = ["t","0ct1","0ct2","0ct3","0ct4","1ct1","1ct2","1ct3","1ct4","v"]
  print " ".join(h)

def readit(idx, ser):
  r = ser.readline()
  if r != "":
    f = r.split()
    id = f[0]
    if id == h[0]:
    elif id == h[1]:
    else:
      print "unrecognized id"
    print datetime.datetime.now(),id," ".join(f)

ser0 = serial.Serial('/dev/ttyACM0', 9600, 8, 'N', 1, timeout=20)
ser1 = serial.Serial('/dev/ttyACM1', 9600, 8, 'N', 1, timeout=20)

header()
while True:
  readit(0, ser0)
  readit(1, ser1)
