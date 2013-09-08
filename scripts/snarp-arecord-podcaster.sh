#!/bin/bash

SNARP=$(dirname $0)/../snarp.py

arecord -D front:CARD=Podcaster,DEV=0 -r 48000 -f S24_3LE |\
	python $SNARP --silence-min -1500000 --silence-max 1500000 output.wav

