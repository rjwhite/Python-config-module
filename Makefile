install:
		@echo Please see INSTALL file

test:
	./run-tests.py

htmldoc:
	mkdir -p doc
	pydoc -w config
	mv config.html doc

