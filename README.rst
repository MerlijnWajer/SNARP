SNARP
=====

SNARP (Simple Noise Activated Recording in Python) is, as the title suggests, a
program to record audio. It is primarily developed on the N900.

Eventually I'll split it up into a recording part and a Graphical frontend. The
frontend would probably be specific to the N900 Maemo 5 QT Widget set.

Command Line Interface
----------------------

To use SNARP from the UNIX command line, specify an output wav file to write to
as a positional argument. By default, snarp.py reads wav data from ``stdin``::

    $ cat test.wav | python snarp.py output.wav

The audio in the output will have frames from silence sections of the input removed,
but otherwise be a frame-for-frame copy of the input. 

Reading data from the standard input makes it particularly easy to read from 
different audio devices using command line audio programs and pipes. Sox_ (cross
platform) and arecord_ (Linux) are suggested. Using Sox' ``rec`` program to 
record system audio input, trimming out silences with SNARP::

    $ rec -t wav - | python snarp.py output.wav

To specify an input file rather than reading from the standard input, use the ``-i``
flag::

    $ python snarp.py -i test.wav output.wav

You may need to override the min and max sample levels used to define silent periods::

    $ python snarp.py -i test.wav --silence-min -100 --silence-max 100 output.wav

Other options and usage information can be found with ``python snarp.py -h``.

Original SNARP behavior
-----------------------

Use arecord via pipes to emulate SNARP's original default behavior::

    $ arecord -D hw:0,0 -r 8000 |\
          python snarp.py --silence-min 120 --silence-max 135 output.wav

And SNARP's original "podcaster" behavior::

    $ arecord -D front:CARD=Podcaster,DEV=0 -r 48000 -f S24_3LE |\
          python snarp.py --silence-min -1500000 --silence-max 1500000 output.wav

.. _Sox: http://sox.sourceforge.net/
.. _arecord: http://linux.die.net/man/1/arecord

