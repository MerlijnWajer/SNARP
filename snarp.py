#!/usr/bin/env python

import subprocess
import wave
import time
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class SinkInput(object):
    """
        TODO: arecord will keep on running. We need to drop frames when it's
        paused or when just not being read. Perhaps only keep recent frames?
        Also, arecord is a rather primitive way to read input. Might want to
        switch to gstreamer.
    """

    def __init__(self):
        # Arecord just dumps the raw wav to stdout. We will use this
        # to read from with out wave module.
        self.p = subprocess.Popen(['arecord'], stdout=subprocess.PIPE)
        # Open the pipe.
        self.f = wave.open(self.p.stdout)
        self.nchan, self.sampwidth, self.framerate, self.nframes, self.comp, \
                self.compname = self.f.getparams()

    def start(self):
        pass

    def stop(self):
        pass

    def get_output(self):
        return self.f

class NoiseFilter(object):
    def __init__(self):
        pass

class BufferedClassFile(object):
    def __init__(self):
        self.s = StringIO.StringIO()

    def get_stream(self):
        return self.s

#p = subprocess.Popen(['gst-launch-0.10', 'pulsesrc ! wavenc ! fdsink fd=1'], \
#                stdout=subprocess.PIPE)

ofile = 'test.wav'


inp = SinkInput()

# Print audio setup
print inp.f.getparams()

print 'Sample / s:', inp.framerate

if inp.framerate != 8000 or inp.nchan != 1:
    print 'Format currently not supported.'\
            'Only supported format is 8000 frames and 1 channel'

buf = BufferedClassFile()

# Open file we will write to.
o = wave.open(buf.get_stream(), 'w')
o.setparams((inp.nchan, inp.sampwidth, inp.framerate, 0, 'NONE', \
            'not compressed'))

high, lasthigh = False, False

    
try:
    while True:
        # Read 1 second
        a = inp.f.readframes(inp.framerate)
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

finally:
    inp.f.close()
    o.close()
    print len(buf.get_stream().getvalue())
