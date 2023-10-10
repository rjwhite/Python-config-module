# DON'T run this as root

# If you are in a virtual environment, then it will probably
# install into;
#	 <virtual-path>/config_moxad/lib/python3.X/site-packages/config_moxad
# Otherwise it will probably end up in:
#	<your-HOME>/.local/lib/python3.X/site-packages/config_moxad
# and assume you meant the --user option since you are a normal user and
#  don't have write perms into the system site-packages

help:
	@echo use "'make install'" to install package
	@echo use "'make test'" to run tests
	@echo use "'make build-dist'" to build package from source
	@echo use "'make uninstall'" to uninstall package
	@echo use "'make htmldoc'" to create HTML documentation

install:
	@if [ `whoami` = 'root' ]; then \
		echo "DON'T run this as root!" ; \
	else \
		python3 -m pip install . ; \
	fi

build-dist:
	python3 -m pip install --upgrade build
	python3 -m build

test:
	python3 run-tests.py

htmldoc:
	mkdir -p doc
	python3 -m pydoc -w config_moxad/config.py
	mv config.html doc

clean:
	rm -f config.pyc

uninstall:
	python3 -m pip uninstall config_moxad
