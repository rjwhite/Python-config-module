#!/usr/bin/env python3

from config_moxad import config
import sys

config_file  = 'configs/config.conf'
defs_file    = 'configs/config-defs.conf'

def expecting( test_num, description, got, expect ):
    ret = 1
    result = 'NOT ok'       # default to fail
    if got == expect:
        result = 'OK'
        ret = 0

    print( "test #{0:d}: ({1}): {2}.\n".format( test_num, description, result ) + \
        "\tExpected: \'{0}\'\n".format( expect ) + \
        "\tGot: \'{0}\'".format( got ))

    return( ret )



config.Config.set_debug( False )

num_errs = 0 
test_num = 1
try:
    conf = config.Config( config_file, defs_file, AcceptUndefinedKeywords=True )
except ( IOError, SyntaxError, ValueError ) as err:
    sys.stderr.write( '%s\n' % str(err))
    sys.exit(1)

try:
    sections = conf.get_sections()
except ( ValueError ) as err:
    sections = ()
num_errs += expecting( test_num, 'num of sections for ' + config_file, len(sections), 7 )
test_num += 1

try:
    keywords = conf.get_keywords( 'section1' )
except ( IOError, SyntaxError, ValueError ) as err:
    keywords = ()
num_errs += expecting( test_num, 'num of keywords in section \'section1\'', len(keywords), 8 )
test_num += 1

try:
    expect = '  another scalar with leading and trailing spaces  '
    value = conf.get_values( 'section1', 'keyword1.2' )
except ( IOError, SyntaxError, ValueError ) as err:
    value = ""
num_errs += expecting( test_num, 'scalar value for section1:keyword1.2', value, expect )
test_num += 1


an_array = [ 'one', 'two', 'three', 'four' ]
try:
    values = conf.get_values( 'section1', 'keyword1.4' )
except ( IOError, SyntaxError, ValueError ) as err:
    values = ()
num_errs += expecting( test_num, 'arrays values for section1:keyword1.4', str(values), str(an_array) )
test_num += 1


try:
    values = conf.get_values( 'section1', 'keyword1.5' )
    value = values[ '2' ]
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( test_num, 'hash value for section1:keyword1.5[\'2\']', value, 'two' )
test_num += 1


try:
    type = conf.get_type( 'section1', 'keyword1.8' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( test_num, 'get type (array) for section1:keyword1.8', type, 'array' )
test_num += 1


try:
    type = conf.get_type( 'keyword1.6' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( test_num, 'get type (hash) for keyword=keyword1.6', type, 'hash' )
test_num += 1


if num_errs:
    print( "\nFAILed tests with {0:d} errors".format( num_errs ))
    sys.exit(1)
else:
    print( "\nALL tests PASSed" )
    sys.exit(0)
