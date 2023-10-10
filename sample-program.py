#!/usr/bin/env python3

from config_moxad import config
import sys

config.Config.set_debug( False )

try:
    conf = config.Config( 'configs/config.conf', 'configs/config-defs.conf',
                           AcceptUndefinedKeywords=1)
except ( IOError, SyntaxError, ValueError ) as err:
    sys.stderr.write( '%s\n' % str(err))
    sys.exit(1)

sections = conf.get_sections()
for section in sections:
    print( section + ':' )
    keywords = conf.get_keywords( section )
    for keyword in keywords:
        try:
            type = conf.get_type( section, keyword )
        except ( ValueError ) as err:
            sys.stderr.write( '%s\n' % str(err))
            sys.exit(1)

        try:
            values = conf.get_values( section, keyword )
        except ( ValueError ) as err:
            sys.stderr.write( '%s\n' % str(err))
            sys.exit(1)

        print( "\t" + keyword + ' (' + type + '):' )

        if type == 'scalar':
            print( '\t\t\'' + values + "'" )
        elif type == 'array':
            for v in values:
                print( "\t\t\'" + v + "\'" )
        elif type == 'hash':
            keys = list( values )
            for key in keys:
                print( '\t\t' + key + ' = ' + "\'" + values[ key ] + "\'" )
        else:
            print( '\t\tunknown type: ' + type )
