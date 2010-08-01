#!/usr/bin/env python

import subprocess
import wave
import time

#p = subprocess.Popen(['gst-launch-0.10', 'pulsesrc ! wavenc ! fdsink fd=1'], \
#                stdout=subprocess.PIPE)

ofile = 'test.wav'

# Arecord just dumps the raw wav to stdout. We will use this
# to read from with out wave module.
p = subprocess.Popen(['arecord'], stdout=subprocess.PIPE)

# Open the pipe.
f = wave.open(p.stdout)

# Print audio set up
print f.getparams()

nchan, sampwidth, framerate, nframes, comp, compname = f.getparams()
print 'Sample / s:', framerate

if framerate != 8000 or nchan != 1:
    print 'Format currently supported. Only supported format is 8000 frames and 1
channel'


# Open file we will write to.
o = wave.open(ofile, 'w')
o.setparams((nchan, sampwidth, framerate, 0, 'NONE', 'not compressed'))

high, lasthigh = False, False

while True:
    # Read 1 second
    a = f.readframes(framerate)
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
