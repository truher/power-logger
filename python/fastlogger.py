import lib,sys
from datetime import datetime

serials = []
while True:
    serials = lib.transcribe_all(serials, sys.stdout)
