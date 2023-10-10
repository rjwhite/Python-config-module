"""
human readable config files

This module reads human-readable config files with sections comprised
of keyword = values, where the values can be a simple scalar (by default)
or arrays, or associative arrays (dicts).

You can supply an optional definitions file providing value types, allowed
values, different separators, etc.  It can recursively include other config
files.
"""

# Copyright 2017 RJ White
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import sys

_PY2 = sys.version_info[0] == 2
_PY3 = sys.version_info[0] == 3

_string_type = str
if _PY2:
    _string_type = basestring
if _PY3:
    _string_type = str

__version__ = '4.0.1'
_VERSION = __version__      # for backwards compatibility < ver 4.0


class Config(object):
    """
    Read a config file.

    The format of the config file will be:
        section1:
            keyword1    = value1, value2, value3    # for array
            keyword2    = value1                    # for scalar
            keyword3    = key1=val1, key2=val2      # for hash

        section2:
            keyword4    = ...

    Continuation lines can be done with a backslash at the end of a line.
    It is recursive, using '#include file' to read in other config files.

    A optional definitions file can be given to tell it if the
    type of data above for the keywords is different than the
    default type of 'scalar'.   The definitions file is of format:
        keyword         = string
        type            = scalar | array | hash
        allowed-values  = value1, value2, ...
        separator       = string (default = ,)
    Each block of definitions are separated by at least 1 blank line.
    A blank line signifies the end of a definition block.

    The 'keyword' string value given can be specific to a section, such as:
        keyword  = some-section:some-keyword
    If the section name is not given then it applies to the keyword of that
    name in all sections.  A section specific definition over-rides a generic
    one.

    The 'separator' given in the definitions file applies to the
    values the config file, and not the definitions file itself.  
    ie: the separator used in the definitions file to separate values in
    'allowed-values' is always a comma.

    If you want the literal separator character in your data, or
    you change it, be sure to escape your data in the config file
    appropriately with the backslash character.

    If the definitions file is given, then only keywords specified in the
    definitions file can used in the configuration file.  Unless the
    'AcceptUndefinedKeywords' option is used and set to a true value.

    if there is no definitions file to specify different data types, you
    can specify the type in the config file surrounded by brackets, such as:
        section1:
            keyword1 (array)  = value1, value2, value3    # for array
            keyword2 (scalar) = value1                    # for scalar
            keyword3 (hash)   = key1=val1, key2=val2      # for hash

    Note that a 'section' is just a way of grouping and organizing
    keywords.  Whatever the type of a keyword (scalar, array or hash),
    it is the same if that keyword is used in multiple 'section's.

    Use single or double quotes around a value if you need leading or
    trailing whitespace on a value.

    To see debug output:  config.Config.set_debug( True )
    """

    # states while processing a section
    _STATE_SECTION      = 1
    _STATE_KEYWORDS     = 2
    _STATE_NONE         = 3

    # keywords used in processing definitions file
    _DEFS_KEYWORD       = 'keyword'
    _DEFS_TYPE          = 'type'
    _DEFS_SEPARATOR     = 'separator'
    _DEFS_ALLOWED       = 'allowed-values'
    _DEFS_SECTION       = 'section'

    # types of data
    _TYPE_SCALAR        = 'scalar'
    _TYPE_ARRAY         = 'array'
    _TYPE_HASH          = 'hash'
    _ALLOWED_TYPES      = ( _TYPE_SCALAR, _TYPE_ARRAY, _TYPE_HASH )

    _DEFAULT_TYPE       = _TYPE_SCALAR
    _DEFAULT_SEPARATOR  = ','

    # to deal with escape characters and value separators that are
    # wanted as part of the data
    _HIDE_SEPARATOR     = 'EvIlCoMmA'
    _HIDE_BACKSLASH     = 'EvIlBaCkSlAsH'

    _DEBUG              = 0     # use set_debug() to set

    def __init__( self, config_file, defs_file="", **options ):
        """
        Initialization function.
        Not user callable.  Ignore this.  Go away.
        """

        self.config_file        = config_file
        self.defs_file          = defs_file

        i_am                    = sys._getframe().f_code.co_name
        self.accept_all_keys    = options.pop( 'AcceptUndefinedKeywords', False )
        self.values             = {}
        self.generic_types      = {}    # get_type( keyword )
        self.specific_types     = {}    # get_type( section, keyword )

        # we have a pile of state to keep in our instance to make handling
        # recursive calls to __read_file() easier

        self.state              = Config._STATE_NONE
        self.recursion_depth    = 0
        self.errors             = []
        self.num_errs           = 0
        self.error_msg          = ""

        # for the definitions file
        self.have_defs_file     = 0         # set to 1 if exists and processed
        self.defs               = {}        # definitions
        self.defs_ok_keywords   = {}        # keywords defined in defs file

        self.section_name       = ""        # current section being processed
        self.sections           = {}
        self.sections_ordered   = []
        self.keywords_ordered   = {}

        Config.__debug( self, __name__, i_am, 'config module version {0}'. \
            format( __version__ ))
        Config.__debug( self, __name__, i_am, 'running Python version {0}'. \
            format( sys.version_info[0] ))
        Config.__debug( self, __name__, i_am, 'processing config file ' +
            config_file )
        Config.__debug( self, __name__, i_am, 'processing definitions file ' +
            defs_file )

        # read in a definitions file.
        # It is optional so it is ok if it does not exist
        try:
            Config.__read_defs_file( self, self.defs_file ) 
            self.have_defs_file = 1
        except IOError:
            pass        # ok to not have a defs file
        except SyntaxError:
            raise

        # now read the config file
        try:
            Config.__read_file( self, self.config_file ) 
        except (IOError, ValueError):
            raise


    def __allowed( self, section, keyword, value ):
        """
        Not user callable.

        returns 1 if allowed, 0 if not allowed
        """

        allowed = None
        full_keyword = section + ':' + keyword

        # general case
        if keyword in self.defs:
            if Config._DEFS_ALLOWED in self.defs[ keyword ]:
                allowed = self.defs[ keyword ][ Config._DEFS_ALLOWED ]

        # specific case over-rides general case
        if full_keyword in self.defs:
            if Config._DEFS_ALLOWED in self.defs[ full_keyword ]:
                allowed = self.defs[ full_keyword ][ Config._DEFS_ALLOWED ]

        # no allowed values found, so allow anything
        if allowed == None: return 1

        for str in allowed:
            if str == value:
                return 1

        return 0
    


    def __read_defs_file( self, defs_file ):
        """
        Not user callable.  Ignore this.  Go away.

        Reads a optional definitions file which sets up data structures
        in the instance so that we know how to use the items described
        in the config file.
    
        keywords understood in the definitions file are:
            keyword         = <some-string>
            type            = scalar | array | hash  (default = scalar)
            separator       = <some-string> (default = ',')
            allowed-values  = comma-separated strings
    
        This is meant as a internal function and should only be called
        once for a config file, despite possible recursive calls because
        of #includes in the config file
        """

        i_am = sys._getframe().f_code.co_name
        error_msg = ""
        num_errs  = 0
        got_entry = 0     # flag for processing entry
        got_data  = 0     # we read some data

        # set up empty object
        obj      = {}    # object of a definitions entry
        keyword  = ""
        section  = "" 

        line_number  = 0 
        continuation = 0     # flag for continuation line

        Config.__debug( self, __name__, i_am, 'processing definitions file ' +
            defs_file )

        try:
            f = open( defs_file, "r" )
            for line in f:
                line_number += 1

                line2 = line.rstrip('\r\n\t ')
                if line2.startswith( "#" ):    continue     # comments
                if re.match( "\s*\#", line2 ): continue     # indented comment 

                # See if this is a continuation from a previous line
                if continuation == 1:
                    line2 = last_str + line2.lstrip()

                #  have to double-escape to get a single backslash!?  blech!
                if re.match( '.*[^\\\\]\\\\$', line2 ):
                    continuation = 1
                    dbg = 'got a continuation line on line #{0:d} in {1}'. \
                        format( line_number, defs_file )
                    Config.__debug( self, __name__, i_am, dbg ) ;
                    last_str = line2
                    last_str = last_str.rstrip( "\\" )
                    continue
                else:
                    continuation = 0

                if line2 == "":
                    if got_data:
                        # we got *some* definitions
                        if got_entry:
                            # we also got a 'keyword' definition.  good to go
                            # finished with an entry.  save it

                            if section != "":
                                self.defs[ section + ":" + keyword ] = obj
                            else:
                                self.defs[ keyword ] = obj
                        else:
                            error = "Have not provided a keyword definition " + \
                                    "by end of block on line #{0:d} in {1}". \
                                format( line_number, defs_file )
                            error_msg += error + '\n'   # add to other errors
                            num_errs += 1

                    keyword   = ""          # reset
                    section   = ""          # reset
                    got_entry = 0           # reset
                    got_data  = 0           # reset
                    obj       = {}          # new entry

                    continue                # blank line

                # keyword = something
                m = re.match( "([\w\-]+)\s*=\s*(.*)\s*$", line2 )
                if m:
                    key   = m.group(1)
                    value = m.group(2)
                else:
                    error = "Invalid line #{0:d} in {1} ({2})". \
                        format( line_number, defs_file, line2 )
                    error_msg += error + '\n'      # add to other errors
                    num_errs += 1
                    continue

                if key == Config._DEFS_KEYWORD:
                    keyword = value
                    section = ""        # default
                    full_keyword = keyword
                    # match section:keyword
                    m = re.match( "([\w\-]+):([\w\-]+)$", value )
                    if m:
                        section = m.group(1)
                        keyword = m.group(2)
                        full_keyword = section + ':' + keyword

                    obj[ Config._DEFS_KEYWORD ] = keyword
                    obj[ Config._DEFS_SECTION ] = section
                    got_entry = 1
                    got_data  = 1

                    self.defs_ok_keywords[ full_keyword ] = 1
                elif key == Config._DEFS_TYPE:
                    if value not in Config._ALLOWED_TYPES:
                        error = "Invalid type ({0}) line #{1:d} in {2} ({3})". \
                            format( value, line_number, defs_file, line2 )
                        error_msg += error + '\n'      # add to other errors
                        num_errs += 1
                        continue

                    got_data  = 1
                    obj[ Config._DEFS_TYPE ] = value
                elif key == Config._DEFS_SEPARATOR:
                    # get rid of surrounding matching quotes
                    m = re.match( "\'(.*)\'$", value )
                    if m: value = m.group(1)

                    m = re.match( "\"(.*)\"$", value )
                    if m: value = m.group(1)

                    got_data  = 1
                    obj[ Config._DEFS_SEPARATOR ] = value
                elif key == Config._DEFS_ALLOWED:

                    # if the user escapes a comma or backslash to have it part
                    # of the data, then hide it for now

                    value = value.replace( '\\\\', Config._HIDE_BACKSLASH )
                    value = value.replace( '\\,',  Config._HIDE_SEPARATOR )

                    got_data  = 1
                    values = value.split( "," )
                    obj[ Config._DEFS_ALLOWED ] = []
                    for v in values:
                        v = v.strip()       # leading  and trailing whitespace
                        # get rid of surrounding matching quotes
                        m = re.match( "\'(.*)\'$", v )
                        if m: v = m.group(1)
                        m = re.match( "\"(.*)\"$", v )
                        if m: v = m.group(1)

                        # put any separators back but without the backslash
                        v = v.replace( Config._HIDE_SEPARATOR, ',' )

                        # now put any dual backslashes back - but only one
                        v = v.replace( Config._HIDE_BACKSLASH, '\\' )

                        obj[ Config._DEFS_ALLOWED ].append( v )
                else:
                    error = "Invalid keyword ({0}) line #{1:d} in {2} ({3})". \
                        format( key, line_number, defs_file, line2 )
                    error_msg += error + '\n'      # add to other errors
                    num_errs += 1
                    continue

            f.close()

            # finish up outstanding entry if it exists
            if got_data:
                # we got *some* definitions
                if got_entry:
                    # we also got a 'keyword' definition.  good to go
                    # finished with an entry.  save it

                    if section != "":
                        self.defs[ section + ":" + keyword ] = obj
                    else:
                        self.defs[ keyword ] = obj
                else:
                    error = "Have not provided a keyword definition " + \
                            "by end of block on line #{0:d} in {1}". \
                        format( line_number, defs_file )
                    error_msg += error + '\n'      # add to other errors
                    num_errs += 1

            if num_errs > 0:
                error_msg = error_msg.strip()   # strip trailing newline
                raise SyntaxError( error_msg )

        except IOError as e:
            if defs_file != "":
                filename = "'" + defs_file + "'"
            else:
                filename = 'a definitions file'
            Config.__debug( self, __name__, i_am, 'could not open ' + filename )
            raise       # we ultimately ignore this further up the stack

        # print out our data structures if G_debug is set

        if Config._DEBUG:
            print( '\ndata dump of definitions file ' + defs_file + ':' )
            for key in self.defs:
                type    = Config._DEFAULT_TYPE
                sep     = Config._DEFAULT_SEPARATOR
                section = ""

                if Config._DEFS_TYPE in self.defs[ key ]:
                    type = self.defs[key][Config._DEFS_TYPE]
                if Config._DEFS_KEYWORD in self.defs[ key ]:
                    keyword = self.defs[key][Config._DEFS_KEYWORD]
                if Config._DEFS_SECTION in self.defs[ key ]:
                   section = self.defs[key][Config._DEFS_SECTION]
                if Config._DEFS_SEPARATOR in self.defs[ key ]:
                    sep = self.defs[key][Config._DEFS_SEPARATOR]

                if section != "":
                    print( '\t' + section + ':' + keyword + ':' )
                else:
                    print( '\t' + keyword + ':' )

                print( "\t\ttype: \'" + type + "\'" )
                print( "\t\tseparator: \'" + sep + "\'" )

                if Config._DEFS_ALLOWED in self.defs[ key ]:
                    print( "\t\tallowed values:" )
                    for v in self.defs[ key ][ Config._DEFS_ALLOWED ]:
                        print( "\t\t\t\'" + v + "\'" )
            print( "\n" )


    def __read_file( self, cnf_file ):
        """
        Not user callable.  Ignore this.  Go away.

        The format of the config file will be:
            section1:
                keyword1    = value1, value2, value3    # for array
                keyword2    = value1                    # for scalar
                keyword3    = key1=val1, key2=val2      # for hash

            section2:
                keyword4    = ...

        It gets the 'type' of data from the definitions file, but you can
        also specify it directly in the config file, such as:
            section1:
                keyword1 (array)   = value1, value2, value3    # for array
                keyword2 (scalar)  = value1                    # for scalar
                keyword3 (hash)    = key1=val1, key2=val2      # for hash

        Any disagreement between the type given in the config file and the
        definitions file will use the config file as authoritative.

        It defaults to 'scalar', so it does not need to be provided.

        Continuation lines can be done with a backslash at the end of a line.
        It is recursive, using '#include file' to read in other config files.
        """

        continuation = 0     # flag for continuation line
        i_am = sys._getframe().f_code.co_name

        self.recursion_depth += 1
        depth       = self.recursion_depth      # short-cut variable
        line_number = 0 

        debug_str = "(depth=" + str(depth) + ")"
        Config.__debug( self, __name__, i_am, debug_str + 
                        ' processing config file ' + cnf_file )

        try:
            f = open( cnf_file, "r" )
            for line in f:
                line_number += 1
                str1 = line.rstrip('\r\n\t ')

                # See if there is a include file

                m = re.match( r"^#include\s+([\w/\.\-]+)$", str1 )
                if m:
                    include_file = m.group(1)
                    Config.__read_file( self, include_file )
                    continue

                if str1.startswith( "#" ):    continue     # comment
                if re.match( "\s*\#", str1 ): continue     # indented comment 
                if str1 == "": continue                    # blank line

                # See if this is a continuation from a previous line
                if continuation == 1:
                    str1 = last_str + str1.lstrip()

                if re.match( '.*[^\\\\]\\\\$', str1 ):
                    continuation = 1
                    dbg = 'got a continuation line on line #{0:d} in {1}'. \
                        format( line_number, cnf_file )
                    Config.__debug( self, __name__, i_am, dbg ) ;
                    last_str = str1
                    last_str = last_str.rstrip( "\\" )
                    continue
                else:
                    continuation = 0


                # start of a new section
                m = re.match( "([\w\-]+)[:]*\s*", str1 )
                if m:
                    self.state = Config._STATE_SECTION
                    self.section_name = m.group(1)

                    if self.section_name not in self.sections:
                        self.sections[ self.section_name ] = {}
                        self.sections_ordered.append( self.section_name )
                        self.keywords_ordered[ self.section_name ] = []

                    continue


                # test if inside a section
                # m:    "    this = that"
                # m2:   "    this (type) = that"
                m  = re.match( "\s+([\w\.\-]+)\s*=\s*(.*)\s*$", str1 )
                m2 = re.match( "\s+([\w\.\-]+)\s+\(([\w]+)\)\s*=\s*(.*)\s*$", str1 )

                if m or m2:
                    # ok, it's a 'keyword = value(s)' line

                    # make sure we have a valid section

                    if self.section_name == "":
                        err = "found keyword not within a section, on line #{0:d} in {1}". \
                            format( line_number, config_file )
                        raise ValueError( "{0}: {1}".format( i_am, err ))

                    self.state = Config._STATE_KEYWORDS

                    most_sig_type = None    # most significant 'type'
                    if m2:
                        # we have a 'type' that over-rides all others.  save it for now
                        keyword       = m2.group(1)
                        most_sig_type = m2.group(2)
                        value         = m2.group(3)

                        # sanity check
                        if most_sig_type not in Config._ALLOWED_TYPES:
                            error = "Invalid type ({0}) line #{1:d} in {2} ({3})". \
                                format( most_sig_type, line_number, cnf_file, str1 )
                            self.error_msg += error + '\n'      # add to other errors
                            self.num_errs += 1
                            continue
                    else:
                        keyword  = m.group(1)
                        value    = m.group(2)

                    # see if allowed (defined) keyword
                    full_keyword = self.section_name + ':' + keyword
                    if ((self.have_defs_file == 1) and (not self.accept_all_keys)):
                        if ( keyword not in self.defs_ok_keywords ) and \
                           ( full_keyword not in self.defs_ok_keywords ):
                            error = "Keyword ({0}) not defined on line #{1:d} in {2} ({3})". \
                                format( keyword, line_number, cnf_file, str1.lstrip() )
                            self.error_msg += error + '\n'      # add to other errors
                            self.num_errs += 1
                            continue

                    # defaults
                    separator = Config._DEFAULT_SEPARATOR
                    type      = None
                    ok_values = None

                    # need to see if any definitions from definitions file
                    if self.have_defs_file == 1:
                        # first try for most general case of 'keyword'
                        if keyword in self.defs:
                            if Config._DEFS_SEPARATOR in self.defs[ keyword ]:
                                separator = self.defs[ keyword ][ Config._DEFS_SEPARATOR ]
                            if Config._DEFS_ALLOWED in self.defs[ keyword ]:
                                ok_values = self.defs[ keyword ][ Config._DEFS_ALLOWED ]
                            if Config._DEFS_TYPE in self.defs[ keyword ]:
                                type = self.defs[ keyword ][ Config._DEFS_TYPE ]
                                self.generic_types[ keyword ] = type

                        # next try specific case
                        if full_keyword in self.defs:
                            if Config._DEFS_SEPARATOR in self.defs[ full_keyword ]:
                                separator = self.defs[ full_keyword ][ Config._DEFS_SEPARATOR ]
                            if Config._DEFS_ALLOWED in self.defs[ full_keyword ]:
                                ok_values = self.defs[ full_keyword ][ Config._DEFS_ALLOWED ]
                            if Config._DEFS_TYPE in self.defs[ full_keyword ]:
                                type = self.defs[ full_keyword ][ Config._DEFS_TYPE ]
                                if not self.section_name in self.specific_types:
                                    self.specific_types[ self.section_name ] = {}
                                self.specific_types[ self.section_name ][ keyword ] = type

                    # now see if we had the type defined in the actual data file
                    # If so, make sure it also matches if also given in defs file

                    if most_sig_type != None:
                        if type != None and most_sig_type != type:
                            error = "Type given in defs file ({0}) does not match " \
                                    "type given in config file ({1}) for section \'{2}\', " \
                                    "keyword \'{3}\' on line {4} in {5}". \
                                    format( type, most_sig_type, self.section_name, \
                                        keyword, line_number, cnf_file )

                            self.error_msg += error + '\n'      # add to other errors
                            self.num_errs += 1
                            continue

                        type = most_sig_type
                        if not self.section_name in self.specific_types:
                            self.specific_types[ self.section_name ] = {}
                        self.specific_types[ self.section_name ][ keyword ] = type

                    if type == None:
                        type = Config._DEFAULT_TYPE
                        self.generic_types[ keyword ] = type

                    Config.__debug( self, __name__, i_am, debug_str + " type = " + \
                        type + " for " + self.section_name + "/" + keyword )


                    # if the user escapes a comma or backslash to have it part
                    # of the data, then hide it for now

                    value = value.replace( '\\\\', Config._HIDE_BACKSLASH )
                    value = value.replace( '\\' + separator,  Config._HIDE_SEPARATOR )

                    obj = value         # default (scalar)
                    if type == Config._TYPE_SCALAR:
                        # get rid of surrounding matching quotes
                        m = re.match( "\'(.*)\'$", value )
                        if m: value = m.group(1)
                        m = re.match( "\"(.*)\"$", value )
                        if m: value = m.group(1)

                        # put any separators back but without the backslash
                        value = value.replace( Config._HIDE_SEPARATOR, separator )

                        # now put any dual backslashes back - but only one
                        value = value.replace( Config._HIDE_BACKSLASH, '\\' )

                        if Config.__allowed( self, self.section_name, keyword, value ) == 0:
                            error = "Value \'{0}\' not allowed on line #{1:d} in {2}: \'{3}\'". \
                                format( value, line_number, cnf_file, str1 )
                            self.error_msg += error + '\n'      # add to other errors
                            self.num_errs += 1
                            continue

                        obj = value

                    elif type == Config._TYPE_ARRAY:
                        values = value.split( separator )
                        obj = []
                        for val in values:
                            val = val.strip()
                            # get rid of surrounding matching quotes
                            m = re.match( "\'(.*)\'$", val )
                            if m: val = m.group(1)
                            m = re.match( "\"(.*)\"$", val )
                            if m: val = m.group(1)

                            # put any separators back but without the backslash
                            val = val.replace( Config._HIDE_SEPARATOR, separator )

                            # now put any dual backslashes back - but only one
                            val = val.replace( Config._HIDE_BACKSLASH, '\\' )

                            if Config.__allowed( self, self.section_name, keyword, val ) == 0:
                                error = "Value \'{0}\' not allowed on line #{1:d} in {2}: \'{3}\'". \
                                    format( val, line_number, cnf_file, str1 )
                                self.error_msg += error + '\n'      # add to other errors
                                self.num_errs += 1
                            else:
                                obj.append( val )

                    elif type == Config._TYPE_HASH:
                        # we need to build a associative array (dictionary)
                        values = value.split( separator )
                        obj = {}
                        for val in values:
                            m  = re.match( "\s*([\w\.\-]+)\s*=\s*(.*)\s*$", val )
                            if not m: 
                                error = "did not find a KEYWORD = VALUE in hash on line #{0:d} in {1}: \'{2}\'". \
                                    format( line_number, cnf_file, val )
                                self.error_msg += error + '\n'      # add to other errors
                                self.num_errs += 1
                            else:
                                k = m.group(1)
                                v = m.group(2)

                                # strip surrounding whitespace
                                k = k.strip()
                                v = v.strip()

                                # get rid of surrounding matching quotes
                                m = re.match( "\'(.*)\'$", v )
                                if m: v = m.group(1)
                                m = re.match( "\"(.*)\"$", v )
                                if m: v = m.group(1)

                                # put any separators back but without the backslash
                                v = v.replace( Config._HIDE_SEPARATOR, separator )

                                # now put any dual backslashes back - but only one
                                v = v.replace( Config._HIDE_BACKSLASH, '\\' )

                                if Config.__allowed( self, self.section_name, keyword, v ) == 0:
                                    error = "Value \'{0}\' not allowed on line #{1:d} in {2}: \'{3}\'". \
                                        format( v, line_number, cnf_file, str1 )
                                    self.error_msg += error + '\n'      # add to other errors
                                    self.num_errs += 1
                                else:
                                    obj[ k ] = v

                    else:
                        error = "Unknown type ({0}) on line #{1:d} in {2}: \'{3}\'". \
                            format( type , line_number, cnf_file, str1 )
                        self.error_msg += error + '\n'      # add to other errors
                        self.num_errs += 1
                        continue

                    self.sections[ self.section_name ][ keyword ] = obj

                    # we want an ordered list of keyword for each section
                    self.keywords_ordered[ self.section_name ].append( keyword )

                    continue        # not really needed (yet)

                else:
                    error = "Unrecognized line on line #{0:d} in {1}: \'{2}\'". \
                        format( line_number, cnf_file, str1 )
                    self.error_msg += error + '\n'      # add to other errors
                    self.num_errs += 1
                    continue

            f.close()

            if (( depth == 1 ) and ( self.num_errs > 0 )):
                self.error_msg = self.error_msg.strip()
                raise ValueError(self.error_msg )

        except IOError:
            # we don't want to clobber our error message deep down in a
            # recursive Hell.  So save our error message and as we bubble
            # up the stack, use the error from the previous call.  We do
            # this because we want to preserve the correct config file
            # in the error message

            if not self.error_msg:
                self.error_msg = 'Cant open file: ' + cnf_file
                raise IOError( self.error_msg )
            else:
                raise

        except ValueError:
                raise

        finally:
            self.recursion_depth -= 1


    def __debug( self, module, func, str ):
        if Config._DEBUG:
            print( "debug: {0}: {1}(): {2}".format( module, func, str ))


    # to be backward compatible with the first version which only took
    # a keyword , we'll use *args instead of ( section, keyword )

    def get_type( self, *args ):
        """
        Get the type of a keyword.

        type = conf.get_type( keyword )
        type = conf.get_type( section, keyword )

        type can be any of 'scalar', 'array' or 'hash'.
        The config format could be any of:
            keyword1 = value1   (scalar)
            keyword2 = value2, value3, value4  (array)
            keyword3 = key5 = value5, key6 = value6, key7 = value7 (hash)

        If the keyword is not found, the default type of 'scalar' is returned
        """

        i_am = sys._getframe().f_code.co_name

        num_args = len( args )
        if num_args > 1:
            # ignore any excess arguments
            section = args[0]
            keyword = args[1]
            if not isinstance( section, _string_type ):
                raise ValueError( i_am + ": section argument is not a string" )
        elif  num_args == 1:
            keyword = args[0]
            if not isinstance( keyword, _string_type ):
                raise ValueError( i_am + ": keyword argument is not a string" )
        else:
            raise ValueError( i_am + ": missing argument(s)" )

        # set a default type
        type = Config._DEFAULT_TYPE

        # next try to get a generic type
        if keyword in self.generic_types:
            type = self.generic_types[ keyword ]
            Config.__debug( self, __name__, i_am, \
                'found a GENERIC type of ' + type + ' for keyword=' + keyword )

        # and now try to get a specific type
        if num_args > 1:
            if section in self.specific_types:
                if keyword in self.specific_types[ section ]:
                    type = self.specific_types[ section ][ keyword ]
                    Config.__debug( self, __name__, i_am, \
                        'found a SPECIFIC type of ' + type + ' for ' + \
                        'section=' + section + ', keyword=' + keyword )

        return( type )



    def get_sections( self ):
        """
        Return a list of the section names in a config file

        sections = conf.get_sections()
        """

        return( self.sections_ordered )


    def get_keywords( self, section ):
        """
        Return a list of the keywords used in a section in a config file

        keywords = conf.get_keywords( section )

        eg:
            sections = conf.get_sections()
            for section in sections:
                keywords = conf.get_keywords( section )
                for keyword in keywords:
                    ...
        """

        i_am = sys._getframe().f_code.co_name
        keys = []

        if not isinstance( section, _string_type ):
            raise ValueError( i_am + ": section argument is not a string" )

        if section in self.sections:
            for k in self.keywords_ordered[ section ]:
                keys.append( k )
        else:
            error = "could not find any keywords for section \'{0}\'". \
                format( section )
            Config.__debug( self, __name__, i_am, error )
            raise ValueError( i_am + ": " + error )

        return( keys )


    def get_values( self, section, keyword ):
        """
        Return values of a keyword in a section

        values = conf.get_values( section, keyword )
        eg:
            sections = conf.get_sections()
            for section in sections:
                print( section )
                keywords = conf.get_keywords( section )
                for keyword in keywords:
                    print( "\\t" + keyword )
                    values = conf.get_values( section, keyword )
                    print( "\\t\\t", values )

        The data-type of the return value depends on the 'type' of
        the data.  By default it is a scalar, so a string would be 
        returned.  But the type can be changed via the optional
        definitions file, which can specify either a scalar, array
        or hash for a keyword.  The return value of get_values() 
        is the appropriate type.

        If the type is unknown to the program for a specific keyword,
        it can find out with a call to get_type().
        """

        i_am = sys._getframe().f_code.co_name

        if not isinstance( section, _string_type ):
            raise ValueError( i_am + ": section argument is not a string" )
        if not isinstance( keyword, _string_type ):
            raise ValueError( i_am + ": keyword argument is not a string" )

        if section in self.sections:
            if keyword in self.sections[ section ]:
                for k in self.sections[ section ]:
                    if k != keyword: continue
                    obj = self.sections[ section ]
                    v = obj[k]
                    return( v )
            else:
                error = "could not find keyword \'{0}\' in section \'{1}\'". \
                    format( keyword, section )
                Config.__debug( self, __name__, i_am, error )
                raise ValueError( i_am + ": " + error )

        else:
            error = "could not find section \'{0}\'".format( section )
            Config.__debug( self, __name__, i_am, error )
            raise ValueError( i_am + ": " + error )

        return( None )


    @classmethod
    def set_debug( cls, value ):

        old_value = Config._DEBUG
        if value == 0 or value == False:
            set_state = False
            if old_value == True:
                print( "debug: setting debug to OFF" )
        else:
            set_state = True
            print( "debug: setting debug to ON" )

        Config._DEBUG = set_state

        return( old_value )

            
if __name__ == "__main__":
    # % python config.py [-d] [-a] [-h] [-c config] [-f defs-file]
    # To use the default config file and defs file, you'll want to
    # use the -a option (AcceptUndefinedKeywords = True) if you 
    # want the undeclared keywords to pass

    import sys

    config_file = 'configs/config.conf'
    config_defs = 'configs/config-defs.conf'
    debug       = False
    undef_keys  = False

    num_args = len( sys.argv )
    i = 1
    while i < num_args:
        arg = sys.argv[i]
        if arg == '-c' or arg == '--config':
            i = i + 1 ;     config_file = sys.argv[i]
        elif arg == '-f' or arg == '--defs':
            i = i + 1 ;     config_defs = sys.argv[i]
        elif arg == '-d' or arg == '--debug':
            debug = True
        elif arg == '-a' or arg == '--accept':
            undef_keys = True
        elif arg == '-h' or arg == '--help':
            print( "python {0:s} [option]*".format( sys.argv[0] ))
            print( "   [-a|--accept] (AcceptUndefinedKeywords)" )
            print( "   [-c|--config] config-file (default={0:s})".format( config_file ))
            print( "   [-f|--defs]   defs-file (default={0:s})".format( config_defs ))
            print( "   [-d|--debug]  (debug)" )
            print( "   [-h|--help]   (help)" )
            sys.exit(0)
        else:
            print( "unknown option: {0:s}".format( arg ))
            sys.exit(1)

        i = i+1

    Config.set_debug( debug )

    try:
        conf = Config( config_file, config_defs, AcceptUndefinedKeywords=undef_keys)
    except ( IOError, SyntaxError, ValueError ) as err:
        sys.stderr.write( '%s\n' % str(err))
        sys.exit(1)

    print( 'Using config file: {0}'.format( config_file ))
    if config_defs != "":
        print( 'Using config definitions file: {0}'.format( config_defs ))
    else:
        print( "Not using a definitions file" )

    print( "Config Version = {0:s}".format( Config._VERSION ))
    print( "Using Python version {0}\n".format( sys.version_info[0] ))
    sections = conf.get_sections()
    for section in sections:
        print( section + ':' )
        keywords = conf.get_keywords( section )
        for keyword in keywords:
            type = conf.get_type( section, keyword )
            print( "\t{0:s}  ({1:s}):".format( keyword, type ))
            values = conf.get_values( section, keyword )
            if type == 'scalar':
                print( "\t\t\'{0:s}\'".format( values ))
            elif type == 'array':
                for v in values:
                    print( "\t\t\'{0:s}\'".format( v ))
            elif type == 'hash':
                keys = list( values )
                for key in keys:
                    value = values[ key ]
                    print( "\t\t{0:s} = \'{1:s}\'".format( key, value ))
            else:
                print( "\t\t" + values )        # cant happen
        print( "" )
