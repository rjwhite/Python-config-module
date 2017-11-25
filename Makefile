DEST_DIR	= /usr/local/lib/Moxad
OWNER		= rj
GROUP		= rj
MODE        = 755

install:	directories \
			${DEST_DIR}/config

directories: 
	@if [ ! -d ${DEST_DIR} ]; then \
		mkdir -p ${DEST_DIR} ; \
		chown ${OWNER} ${DEST_DIR} ; \
		chgrp ${GROUP} ${DEST_DIR} ; \
	fi

${DEST_DIR}/config:
	install -p -o ${OWNER} -g ${GROUP} -m ${MODE} \
		config.py ${DEST_DIR}/config.py

test:
	./run-tests.py

htmldoc:
	mkdir -p doc
	pydoc -w config
	mv config.html doc

