#!/usr/bin/env python
#
# snarp - Simple Noise Activated Recording in Python
#
# Copyright (C) 2011  Merlijn Wajer <merlijn@wizzup.org>
# Copyright (C) 2011  Antonio Ospite <ospite@studenti.unina.it>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import wave
import time
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import struct

# Parameters of S24_3LE
#FORMAT_SAMPLE_SIGNED=True
#FORMAT_SAMPLE_ENDIANNESS='little' # or 'big'
# Sample width and sample storage width can be different:
# FORMAT_SAMPLE_WIDTH is the resolution of the sample
# FORMAT_SAMPLE_WIDTH_STORAGE is the storage format, how many bytes are used to
# represent a sample of resolution FORMAT_SAMPLE_WIDTH
#
# A _frame_ width will be (FORMAT_SAMPLE_WIDTH_STORAGE * CHANNELS)
#
# Examples of formats with the same sample with but different storage width:
#  S24_LE  -> FORMAT_SAMPLE_WIDTH = 24, FORMAT_SAMPLE_STORAGE_WIDTH_BYTES = 4
#  S24_3LE -> FORMAT_SAMPLE_WIDTH = 24, FORMAT_SAMPLE_STORAGE_WIDTH_BYTES = 3
#FORMAT_SAMPLE_WIDTH_BITS=24
#FORMAT_SAMPLE_STORAGE_WIDTH_BYTES=3


INPUTS = {
    'default' : {
        'device'        : 'hw:0,0',
        'extra_options' : [],
        'sample_rate'   : 8000,
        'channels'      : 1,
        'format'        : {
            'sample_signed'              : False,
            'sample_endianness'          : 'little',
            'sample_width_bits'          : 8,
            'sample_width_storage_bytes' : 1
        },
        'silence_min' : 120,
        'silence_max' : 135
    },
    'podcaster' : {
        'device' : 'front:CARD=Podcaster,DEV=0',
        'extra_options' : ['-f', 'S24_3LE'],
        'sample_rate'   : 48000,
        'channels'      : 1,
        'format'        : {
            'sample_signed'              : True,
            'sample_endianness'          : 'little',
            'sample_width_bits'          : 24,
            'sample_width_storage_bytes' : 3
        },
        'silence_min' : -1500000,
        'silence_max' :  1500000
    }
}


INPUT_SRC = INPUTS["default"]
#INPUT_SRC = INPUTS["podcaster"]

SILENCE_MIN = INPUT_SRC['silence_min']
SILENCE_MAX = INPUT_SRC['silence_max']

INPUT_CMD = ['arecord', '-D', INPUT_SRC['device'], \
    '-r', str(INPUT_SRC['sample_rate'])] + INPUT_SRC['extra_options']
#INPUT_CMD = ['gst-launch-0.10', 'pulsesrc ! wavenc ! fdsink fd=1']


class SinkInput(object):
    """
        TODO: arecord will keep on running. We need to drop frames when it's
        paused or when just not being read. Perhaps only keep recent frames?
        Also, arecord is a rather primitive way to read input. Might want to
        switch to gstreamer.
    """

    def __init__(self, command):
        # Arecord just dumps the raw wav to stdout. We will use this
        # to read from with out wave module.
        self.p = subprocess.Popen(command, stdout=subprocess.PIPE)
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


def frame_to_sample(frame):
    sample_storage_bytes = INPUT_SRC['format']['sample_width_storage_bytes']

    # handling only the first channel
    frame_data = frame[0:sample_storage_bytes]

    # Padding all samples to 4byte integer
    if INPUT_SRC['format']['sample_width_storage_bytes'] < 4:

        if INPUT_SRC['format']['sample_endianness'] == 'little':
            frame_data_MSB = frame_data[sample_storage_bytes - 1]
        else:
            frame_data_MSB = data[0]

        # Check if positive or negative and set the MSB accordigly
        if ord(frame_data_MSB) & 0x80:
            padding_MSB = '\xff'
            frame_data_MSB = chr(ord(frame_data_MSB) & ~0x80)
        else:
            padding_MSB = '\x00'

        # Set the middle padding
        padding = '\x00' * (4 - sample_storage_bytes - 1)

        if INPUT_SRC['format']['sample_endianness'] == 'little':
            frame_data = frame_data + padding + padding_MSB
        else:
            frame_data = padding_MSB + padding + frame_data

    fmt = ''
    if INPUT_SRC['format']['sample_endianness'] == 'little':
        fmt += '<'
    else:
        fmt += '>'

    if INPUT_SRC['format']['sample_signed']:
        fmt += 'l'
    else:
        fmt += 'L'

    sample = struct.unpack(fmt, frame_data)
    return sample[0]


def get_samples(frames):
    # chunk iteration taken from
    # http://stackoverflow.com/questions/434287
    samples = []
    chunkSize = INPUT_SRC['format']['sample_width_storage_bytes'] * \
            INPUT_SRC['channels']
    for i in xrange(0, len(frames), chunkSize):
        frame = frames[i:i + chunkSize]
        sample = frame_to_sample(frame)
        samples.append(sample)

    return samples


ofile = 'test.wav'

inp = SinkInput(INPUT_CMD)

# Print audio setup
print inp.f.getparams()

print 'Sample / s:', inp.framerate

buf = BufferedClassFile()

# Open file we will write to.
o = wave.open(buf.get_stream(), 'w')
o.setparams((inp.nchan, inp.sampwidth, inp.framerate, 0, 'NONE', \
            'not compressed'))

high, lasthigh = False, False


try:
    while True:
        # Read 1 second of audio
        a = inp.f.readframes(inp.framerate * inp.nchan)
        b = get_samples(a)
        _min, _max = min(b), max(b)

        # Print bounds
        print 'min', _min
        print 'max', _max

        if _max > SILENCE_MAX and _min < SILENCE_MIN:
            high = True
            print "Recording..."
        else:
            high = False

        # Write always if either is True.
        if lasthigh or high:
            o.writeframes(a)

        lasthigh = high

except KeyboardInterrupt:
    inp.f.close()
    # TODO: encapsulate the following logic in the destuctor
    #       of BufferedClassFile
    buf.get_stream().flush()
    dump = open(ofile, 'w')
    dump.write(buf.get_stream().getvalue())
    dump.close()
    o.close()
    print len(buf.get_stream().getvalue())
