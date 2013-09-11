
import snarp
import wave
import os

OUTPUT_FILENAME = "/tmp/output.wav"

def assert_eq(a, b):
	assert a == b, "{0!r} != {1!r}".format(a, b)

def test_basic_functionality():
	inputs = [
		("test/data/generated-beeps-44k-16bit-1ch.wav", 262395, 55125),
		("test/data/generated-beeps-44k-8bit-1ch.wav", 262395, 55125),
		("test/data/generated-beeps-22k-16bit-1ch.wav", 131198, 27563),
		("test/data/generated-beeps-22k-8bit-1ch.wav", 131198, 27563),
	]
	for filename, expected_input_frames, expected_output_frames in inputs:
		check_basic_functionality(filename, expected_input_frames, expected_output_frames)

def check_basic_functionality(filename, expected_input_frames, expected_output_frames):
	with open(filename, "rb") as input:
		with open(OUTPUT_FILENAME, "wb+") as output:
		#	with snarp.silence_limits(120, 135):
			snarp.remove_silences(input, output)

			input.seek(0)
			output.seek(0)

			wave_input = wave.open(input, 'rb')
			wave_output = wave.open(output, 'rb')

			print("Filename: {0}".format(filename))
			print("Input is {0} frames long".format(wave_input.getnframes()))
			print("Output is {0} frames long".format(wave_output.getnframes()))

			# Given that we're using the correct test input file
			assert_eq(wave_input.getnframes(), expected_input_frames)
			# Ensure we removed a consistent amount of silence
			assert_eq(wave_output.getnframes(), expected_output_frames)

	# cleanup, delete temp output file
	os.unlink(OUTPUT_FILENAME)


if __name__ == '__main__':
	test()

