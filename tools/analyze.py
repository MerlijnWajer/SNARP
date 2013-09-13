#!/usr/bin/env python
# coding=utf8
'''
Analyze chunk sample level stats from SNARP

Run SNARP with the flag --stats-file to specify the filename to save
CSV sample stats data to. Analye with

    python analyze.py statsfile.csv

You'll need the analysis dependencies in analyze-requirements.txt 
installed.
'''

import pandas
from pandas import Series, DataFrame
import code
import numpy as np
import matplotlib.pyplot as plt
import sys
import csv

if __name__ == '__main__':
	with open("stats.csv" if len(sys.argv) < 2 else sys.argv[1]) as f:
		reader = csv.reader(f)
		data = [(float(peak), float(iqr)) for peak, iqr in reader]

	md = Series(zip(*data)[0])
	iqrd = Series(zip(*data)[1])

	df = DataFrame(data=dict(max_deltas=md, iqr_deltas=iqrd))

	#log_df = np.log(df) / np.log(2)
	#log_df.columns = ["lg {}".format(foo) for foo in log_df.columns]
	#log_df.hist(normed=True)

	df.hist(normed=True)

	plt.show()

	code.interact(local=locals())

