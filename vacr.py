#!/usr/bin/env python

import subprocess
import wave
import time

#p = subprocess.Popen(['gst-launch-0.10', 'pulsesrc ! wavenc ! fdsink fd=1'], \
#                stdout=subprocess.PIPE)

# Arecord just dumps the raw wav to stdout. We will use this
# to read from with out wave module.
p = subprocess.Popen(['arecord'], stdout=subprocess.PIPE)

# Open the pipe.
f = wave.open(p.stdout)

# Open file we will write to.
o = wave.open('test.wav', 'w')
o.setparams((1, 1, 8000, 0, 'NONE', 'not compressed'))
o.setnchannels(1)

high, lasthigh = False, False

# Print audio set up
print f.getparams()

while True:
    # Read 1 second
    a = f.readframes(8000)
    b = [ord(x) for x in a]
    _min, _max = min(b), max(b)

    # Print bounds
    print 'min', _min
    print 'max', _max

    # TODO: The gate should obviously be configurable.
    if _max > 135 and _min < 120:
        high = True
    else:
        high = False

    # Write always if either is True.
    if lasthigh or high:
        o.writeframes(a)

    lasthigh = high

f.close()
o.close()
