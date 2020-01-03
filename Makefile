# If you run a install as root, it will install into a python system directory
# Otherwise it will install into your HOME

install:
	@if [ `whoami` = 'root' ]; then \
		echo "I am Groot!" ; \
		echo "Installing into system python directory" ; \
		sudo python setup.py install ; \
	else \
		echo "I am NOT Groot!" ; \
		echo "Installing as a regular user into ${HOME}/lib/python" ; \
		python setup.py install --home=~ ; \
	fi

test:
	./run-tests.py

htmldoc:
	mkdir -p doc
	pydoc -w config
	mv config.html doc

sdist:
	python setup.py sdist

clean:
	rm -f config.pyc
