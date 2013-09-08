#!/bin/bash

SNARP=$(dirname $0)/../snarp.py

echo arecord -D hw:0,0 -r 8000 |\
	python $SNARP --silence-min 120 --silence-max 135 output.wav

