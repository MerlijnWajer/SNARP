
default:

test: force-run
	nosetests

docs: README.html

README.html: README.rst
	pandoc $^ > $@

clean: force-run
	find . -type f -name '*.pyc' -print0 | xargs -0 rm -f
	rm -f README.html

force-run: /dev/null

