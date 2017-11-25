#!/usr/bin/env python

import config
import sys

config_file  = 'configs/test.conf'
defs_file    = 'configs/test-defs.conf'
config_file2 = 'configs/test2.conf'

def expecting( num, description, got, expect):
    ret = 1
    result = 'NOT ok'       # default to fail
    if got == expect:
        result = 'OK'
        ret = 0

    print "test #{0}: ({1}): {2}. Expected \'{3}\', Got \'{4}\'". \
        format( num, description, result, expect, got )

    return( ret )



config.Config.set_debug( False )

num_errs = 0 
try:
    conf = config.Config( config_file, defs_file, AcceptUndefinedKeywords=True )
except ( IOError, SyntaxError, ValueError ) as err:
    sys.stderr.write( '%s\n' % str(err))
    sys.exit(1)

try:
    conf2 = config.Config( config_file2, defs_file, AcceptUndefinedKeywords=True )
except ( IOError, SyntaxError, ValueError ) as err:
    sys.stderr.write( '%s\n' % str(err))
    sys.exit(1)

try:
    sections = conf.get_sections()
except ( ValueError ) as err:
    sections = ()
num_errs += expecting( 1, 'num of sections for ' + config_file, len(sections), 8 )

try:
    keywords = conf.get_keywords( 'section1' )
except ( IOError, SyntaxError, ValueError ) as err:
    keywords = ()
num_errs += expecting( 2, 'num of keywords in section=section1', len(keywords), 3 )

try:
    value = conf.get_values( 'section2', 'things' )
except ( IOError, SyntaxError, ValueError ) as err:
    value = ""
num_errs += expecting( 3, 'scalar value for section2:things', value, 'this and that   ' )

an_array = [ 'blue', 'yellow', 'red', 'orange', 'purple' ]
try:
    values = conf.get_values( 'some-arrays', 'some-colours' )
except ( IOError, SyntaxError, ValueError ) as err:
    values = ()
num_errs += expecting( 4, 'arrays values for some-arrays:some-colours', str(values), str(an_array) )

try:
    values = conf.get_values( 'some-hashes', 'colours' )
    value = values[ 'critical' ]
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 5, 'hash value for some-hashes:colours[critical]', value, 'red' )

try:
    type = conf.get_type( 'some-arrays', 'some-colours' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 6, 'get type (array) for some-arrays:some-colours', type, 'array' )

try:
    type = conf.get_type( 'colours' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 7, 'get type (hash) for keyword=colours', type, 'hash' )


try:
    separator = conf.get_separator( 'things' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 8, 'get separator for keyword=things', separator, ',' )

try:
    type = conf2.get_type( 'bikes', 'yamaha' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 9, 'get type (array) for bikes:yamaha', type, 'array' )

try:
    type = conf2.get_type( 'bikes', 'honda')
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 10, 'get type (scalar) for bikes:honda', type, 'scalar' )

try:
    value = conf2.get_values( 'bikes', 'ducati' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 11, 'scalar value for bikes:ducati', value, '2001' )

try:
    type = conf2.get_type( 'planets', 'big')
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 12, 'get type (scalar) for planets:big', type, 'scalar' )

try:
    type = conf2.get_type( 'planets', 'small')
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 13, 'get type (array) for planets:small', type, 'array' )

try:
    type = conf2.get_type( 'big')
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 14, 'get type (scalar) for keyword big', type, 'scalar' )

try:
    separator = conf2.get_separator( 'small' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 15, 'get separator for keyword=small', separator, ':' )

try:
    separator = conf2.get_separator( 'planets', 'small' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 16, 'get separator for planets:small', separator, ':' )

try:
    separator = conf.get_separator( 'section1', 'array1' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 17, 'get separator for section1:array1', separator, ':' )

try:
    separator = conf.get_separator( 'array1' )
except ( IOError, SyntaxError, ValueError ) as err:
    pass
num_errs += expecting( 18, 'get separator for array1', separator, ',' )


if num_errs:
    print "\nFAILed tests with {0:d} errors".format( num_errs )
    sys.exit(1)
else:
    print "\nALL tests PASSed"
    sys.exit(0)
