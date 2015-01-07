#!/usr/bin/env python

from config import Config

import sys
import __builtin__

__builtin__.G_debug = False

configs = [ 
    'configs/config1.conf',
    'configs/config2.conf',
    'configs/config3.conf'
]
num_configs = 0
config_obj = []

for config in configs:
    try:
        conf = Config( config, "configs/test-defs.conf", AcceptUndefinedKeywords=1)
    except ( IOError, SyntaxError, ValueError ) as err:
        sys.stderr.write( '%s\n' % str(err))
        continue

    config_obj.append( conf )
    num_configs += 1

for num in range( num_configs ):
    print "config file: " + configs[ num ]
    conf = config_obj[ num ]

    sections = conf.get_sections()
    for section in sections:
        print "\t" + section
        keywords = conf.get_keywords( section )
        for keyword in keywords:
            print "\t\t" + keyword + ' = ',
            values = conf.get_values( section, keyword )
            print values

    print ""
