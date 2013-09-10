#!/usr/bin/env python
#
# snarp - Simple Noise Activated Recording in Python
#
# Copyright (C) 2013  Christopher Casebeer <christopher@chc.name>
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

import logging
#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)

import wave
import time

import struct
import sys
import argparse
import contextlib
import itertools
import collections

SILENCE_MIN = 120
SILENCE_MAX = 135

# Global vars for Wave format metadata
# Usually these are fixed by the format (little, 8 bit -> unsigned, > 8 bit signed), 
# but change these values to override
INPUT_ENDIANNESS = 'little' # Wave format default
INPUT_SIGNEDNESS = None # None means permit Wave format rules to prevail

## Noise detection timings
#
# Set the times, in milliseconds, to use for various noise detection 
# parameters. Note that all times must be multiples of CHUNK_MS, since
# all audio processing is done in blocks of length CHUNK_MS. 
# 
CHUNK_MS      = 1000   # milliseconds per silence analysis period
HYSTERESIS_MS = 3000 # ms of silence before we decide audible segment is over
PRE_ROLL_MS   = 1000  # ms of silence to play at beginning of audible segment
POST_ROLL_MS  = 1000  # ms of silence to play at end of audible segment

HYSTERESIS_CHUNKS = int(float(HYSTERESIS_MS) / CHUNK_MS)
PRE_ROLL_CHUNKS   = int(float(PRE_ROLL_MS) / CHUNK_MS)
POST_ROLL_CHUNKS  = int(float(POST_ROLL_MS) / CHUNK_MS)

# Context managers for global Wave format overrides
@contextlib.contextmanager
def input_endianness(val):
    assert(val in ('little', 'big'))
    global INPUT_ENDIANNESS
    previous = INPUT_ENDIANNESS
    INPUT_ENDIANNESS = val
    yield
    INPUT_ENDIANNESS = previous

@contextlib.contextmanager
def input_signedness(val):
    assert(val in (None, 'signed', 'unsigned'))
    global INPUT_SIGNEDNESS
    previous = INPUT_SIGNEDNESS
    INPUT_SIGNEDNESS = val
    yield
    INPUT_SIGNEDNESS = previous

@contextlib.contextmanager
def silence_limits(min_, max_):
    '''Override SILENCE_MIN and SILENCE_MAX globals.'''
    global SILENCE_MIN, SILENCE_MAX
    old_min, old_max = SILENCE_MIN, SILENCE_MAX
    SILENCE_MIN, SILENCE_MAX = min_, max_
    yield
    SILENCE_MIN, SILENCE_MAX = old_min, old_max

class NoiseFilter(object):
    def __init__(self):
        pass

class RingBuffer(collections.deque):
    def append(self, value):
        discard = None
        if len(self) == self.maxlen:
            discard = self.popleft()
        collections.deque.append(self, value)
        return discard

def audible_chunks(tagged_segments):
    '''
    Generator producing audio chunks only for audible segments
    '''
    return itertools.imap(lambda pair: pair[1], 
        itertools.ifilter(lambda pair: not pair[0], tagged_segments)
    )

def audible_segments(tagged_segments):
    '''
    Return generator of generators, one per audible segment

    For each audible segment in the chunk stream, return a generator
    for its audio data chunks.
    '''
    return (segment for silent, segment in segmenter(tagged_segments) if not silent)

def segmenter(tagged_segments):
    '''
    Return generator of generators, one per segment

    For each segment in the chunk stream, return a tuple of:
        (segment_is_silent, chunk_generator_for_segment)
    '''
    for silent, segment in itertools.groupby(tagged_segments, key=lambda pair: pair[0]):
        yield silent, itertools.imap(lambda pair: pair[1], segment)

def tag_segments(tagged_chunks):
    '''
    Generator returning chunk frames tagged by segment

    Returns a tuple of (chunk_in_silent_segment, chunk_frames) for each
    chunk in the provided generator. 

    Note that this does not tag based strictly on whether the current chunk is silent
    or audible; rather it tags *which type of segment* the chunk belongs to. 
    '''
    logging.info("Config: CHUNK_MS: {}, HYSTERESIS_CHUNKS: {}, PRE_ROLL_CHUNKS: {}, POST_ROLL_CHUNKS: {}".format(
        CHUNK_MS, HYSTERESIS_CHUNKS, PRE_ROLL_CHUNKS, POST_ROLL_CHUNKS
    ))
    buffer = RingBuffer(maxlen=max(PRE_ROLL_CHUNKS, POST_ROLL_CHUNKS))
    segment_silent = True
    hysteresis_counter = 0
    for chunk_silent, chunk_samples, chunk_frames in tagged_chunks:
        if chunk_silent != segment_silent:
#            print "Bump hysteresis, saw {} in {} segment".format("silence" if chunk_silent else "audible",
#                "silent" if segment_silent else "audible")
            hysteresis_counter += 1
        else:
#            if hysteresis_counter > 10:
#                print "Hysteresis counter reset"
            if not segment_silent:
                # dump buffered silent frames so we don't lose silence in middle of audible
                for frames in buffer:
                    yield False, frames
                buffer.clear()
            hysteresis_counter = 0
        # four cases: changing state/not changing state X silent chunk/audible chunk
        if (segment_silent and not chunk_silent) or\
            hysteresis_counter >= HYSTERESIS_CHUNKS:

            print hysteresis_counter

            # changing state if we see any audible chunks 
            # or more than HYSTERESIS_CHUNKS silent chunks
            segment_silent = chunk_silent

            if not chunk_silent:
                # starting audible segment

                # first, take any extra buffer and append to silent segment
                for i in range(len(buffer) - PRE_ROLL_CHUNKS):
                    logging.debug("Dumped excess buffer chunk to silent segment.")
                    yield False, buffer.popleft()
                    
                # write out remainder of buffer as pre-roll
                logging.debug("Pre-rolling...")
                for frames in buffer:
                    logging.debug("Pre-roll chunk written.")
                    yield False, frames
                buffer.clear()

                # emit first audible chunk
                yield False, chunk_frames
            else:
                # ending audible segment, write out any currently consumed chunks
                logging.debug("Post-rolling...")

                # first few buffered chunks go to end of audible segment
                for i in range(POST_ROLL_CHUNKS):
                    if len(buffer) > 0:
                        logging.debug("Post-roll chunk written.")
                        yield False, buffer.popleft()

                # any remaining buffer chunks should go to the silent segment
                for frames in buffer:
                    logging.debug("Dumped excess buffer chunk to silent segment.")
                    yield True, frames

                buffer.clear()

                # the current (silent) chunk goes to the silent segment
                yield True, chunk_frames
        else: # not changing state
            if chunk_silent:
                # we only ever buffer silent chunks, since we don't know whether we
                # want to hear them (within, or at the beginning or end of an audible
                # segment. 
                frames = buffer.append(chunk_frames)

                # If the ring buffer is full, it will spit out the displaced, oldest
                # chunk. Go ahead and emit this as part of a silent segment, since we
                # now know we don't care about it.
                if frames is not None:
                    yield True, frames
            else:
                # we always want to hear audible chunks
                yield False, chunk_frames
    # todo: handle contents of buffer after input chunks exhausted
    # ideally would run back through state change loop one more time
    # for now, just dump out attached to current segment
    for frames in buffer:
        print "dumping left-over frames at end of file."
        yield segment_silent, frames

def tag_chunks(chunk_gen, silence_deltas):
    '''
    Tag each chunk in the generator as silent (True) or audible (False)

    Returns tuple of (chunk_silent, chunk_samples, chunk_frames)
    '''
    max_delta, iqr_delta = silence_deltas
    for chunk_samples, chunk_frames in chunk_gen:
        if len(chunk_samples) == 0:
            break

        samples = sorted(chunk_samples)
        count = len(samples)
        first, last = samples[:int(count/2)], samples[int(count/2):]
        q1, q3 = first[int(len(first)/2):][0], last[int(len(last)/2):][0]

        min_, max_ = samples[0], samples[count - 1]
        #audible = min_ < SILENCE_MIN and SILENCE_MAX < max_
        audible = max_ - min_ > max_delta
        audible = audible or q3 - q1 > iqr_delta
        silence = not audible

        md, iqrd = max_ - min_, q3 - q1

        #logging.debug('max_delta: {0}, iqr_delta: {1}, silence: {2}'.format(max_ - min_, q3 - q1, silence))
        logging.debug('{}% {}%, ({}, {}), silence: {}'.format(
            int(100 * float(max_ - min_) / max_delta), 
            int(100 * float(q3 - q1) / iqr_delta), 
            md, iqrd,
            silence
        ))

        yield silence, chunk_samples, chunk_frames

def chunked_samples(input_wave, chunk_seconds):
    '''
    Generator returning parsed and raw wave data one chunk at a time
    
    Yield a pair of (parsed wave samples, raw wave frames) from `input_wave` 
    in chunks of at most `chunk_seconds` of data. The actual number of frames 
    per chunk will vary with the input wave's frame rate. 
    '''
    sample_width = input_wave.getsampwidth()
    nchannels = input_wave.getnchannels()
    signed_data = input_is_signed_data(input_wave)
    frames_per_chunk = int(input_wave.getframerate() * chunk_seconds)
    while True:
        frames = input_wave.readframes(frames_per_chunk)
        yield list(parse_frames(frames, sample_width, nchannels, signed_data)), frames

def parse_frames(frames, sample_width, nchannels, signed_data):
    '''
    Generator to convert wave frames to sample data
    
    Arguments:
    frames        frame data 
    sample_width  sample width in bytes
    nchannels     number of channels per frame
    signed_data   True if wave data is signed, false if unsigned
    '''
    # todo: coalesce samples for all channels into one?
    chunk_size = sample_width * nchannels
    for i in xrange(0, len(frames), chunk_size):
        frame = frames[i:i + chunk_size]
        yield frame_to_sample(frame, sample_width, signed_data)

def frame_to_sample(frame, sample_width, signed_data):
    '''
    Convert one frame to one sample

    Note that we expect that the frame data will contain frames for all
    channels of the wave file. However, only the first channel will be 
    processed. The data from the remaining channels will be ignored!

    Arguments:
    frame         frame data for *all channels*, only first will be used
    sample_width  sample width in bytes
    signed_data   True if wave data is signed, false if unsigned
    '''
    # todo: accept nchannels and decode all channels
    # handling only the first channel
    frame_data = frame[0:sample_width]

    fmt = ''
    if INPUT_ENDIANNESS == 'little':
        fmt += '<'
    else:
        fmt += '>'

    if signed_data:
        fmt += {4:'l', 2:'h', 1:'b'}[sample_width]
    else:
        fmt += {4:'L', 2:'H', 1:'B'}[sample_width]

    sample = struct.unpack(fmt, frame_data)
    return sample[0]

def input_is_signed_data(wave_file):
    '''
    Return True if the input contains signed date, False if unsigned

    Wave spec says:
    - sample width == 8 bit ==> unsigned, 
    - sample width > 8 bit ==> signed

    Implement this but permit override if INPUT_SIGNEDNESS global
    is explicitly set. 
    '''
    if INPUT_SIGNEDNESS is None:
        # no explicit override, follow spec
        return (wave_file.getsampwidth() > 1)
    else:
        return INPUT_SIGNEDNESS == 'signed'

def remove_silences(input_file, output_file, bypass_file=None):
    input_wave = wave.open(input_file)

    output_wave = wave.open(output_file, 'wb')
    output_wave.setparams((
        input_wave.getnchannels(),
        input_wave.getsampwidth(),
        input_wave.getframerate(),
        0,
        'NONE',
        'not compressed'
    ))

    bypass_wave = None
    if bypass_file is not None:
        bypass_wave = wave.open(bypass_file, 'wb')
        bypass_wave.setparams((
            input_wave.getnchannels(),
            input_wave.getsampwidth(),
            input_wave.getframerate(),
            0,
            'NONE',
            'not compressed'
        ))

    # Print audio setup
    logging.debug('Input wave params: {0}'.format(input_wave.getparams()))
    logging.debug('Frame rate: {0} Hz'.format(input_wave.getframerate()))

    delta_limits = (2**7, 2**4) # whisper level
    delta_limits = (2**11, 2**8) # conversational level
    delta_limits = (2**9, 2**6) # quiet level

    conversion = 2.0**(input_wave.getsampwidth() * 8) / 2**16
    converted_delta_limits = conversion * delta_limits[0], conversion * delta_limits[1]

    logging.debug("16 bit delta limits: {0}".format(delta_limits))
    logging.debug("{0} bit delta limits: {1}".format(input_wave.getsampwidth() * 8, converted_delta_limits))

    try:
        for silent_segment, segment in \
            segmenter(
                tag_segments(
                    tag_chunks(
                        chunked_samples(input_wave, CHUNK_MS / 1000.0),
                        converted_delta_limits
                    )
                )
            ):
            logging.info("Starting {0} segment.".format("silent" if silent_segment else "audible"))
            if silent_segment:
                if bypass_wave is not None:
                    for chunk_frames in segment:
                        bypass_wave.writeframes(chunk_frames)
            else:
                for chunk_frames in segment:
                    output_wave.writeframes(chunk_frames)
                    if bypass_wave is not None:
                        bypass_wave.writeframes(chunk_frames)

    except KeyboardInterrupt:
        pass
    finally:
        input_wave.close()
        output_wave.close()
        if bypass_wave is not None:
            bypass_wave.close()

def main(*argv):
    parser = argparse.ArgumentParser(description='Remove silence from wave audio data.')
    parser.add_argument(
        '-i',
        '--input_filename', 
        default='-',
        help='Filename to read. Defaults to - for STDIN.'
    )
    parser.add_argument(
        '-b',
        '--bypass_filename',
        default=None,
        help='Filename to write bypass audio to. All audio data read from the input will be passed through.'
    )
    parser.add_argument(
        'output_filename', 
        help='Filename to write to.'
    )
    parser.add_argument(
        '--silence-min',
        type=int,
        default=SILENCE_MIN,
        help='Minimum wave sample value to consider silence.'
    )
    parser.add_argument(
        '--silence-max',
        type=int,
        default=SILENCE_MAX,
        help='Maximum wave sample value to consider silence.'
    )
    parser.add_argument(
        '--input-big-endian',
        action='store_true',
        help='Ignore the Wave spec and interpret input as big endian. Not recommended.'
    )
    parser.add_argument(
        '--input-override-signedness',
        choices=("unsigned", "signed"),
        default=None,
        help='Ignore the Wave spec and interpres input with given signedness. Not recommended.'
    )
    args = parser.parse_args(argv[1:])

    input_filename = args.input_filename
    output_filename = args.output_filename

    input_file = sys.stdin if input_filename == '-' else open(input_filename, 'rb')

    bypass_file = None
    if args.bypass_filename is not None:
        bypass_file = open(args.bypass_filename, 'wb')

    with silence_limits(args.silence_min, args.silence_max):
        with input_endianness('big' if args.input_big_endian else 'little'):
            with input_signedness(args.input_override_signedness):
                with open(output_filename, 'wb') as output_file:
                    remove_silences(input_file, output_file, bypass_file)

    return 0

if __name__ == '__main__':
    sys.exit(main(*sys.argv))

