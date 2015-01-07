import __builtin__
import re

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

    Use single or double quotes around a value if you need leading or
    trailing whitespace on a value.

    A optional definitions file can be given to tell it if the
    type of data above for the keywords is different than the
    default type of 'scalar'.   The definitions file is of format:
        keyword         = string
        type            = scalar | array | hash
        allowed-values  = value1, value2, ...
        separator       = string (default = ,)
    The first line of each entry must be the 'keyword' command.

    If the definitions file is given, then only keywords specified in the
    definitions file can used in the configuration file.  Unless the
    'AcceptUndefinedKeywords' option is used and set to a true value.

    Note that a 'section' is just a way of grouping and organizing
    keywords.  Whatever the type of a keyword (scalar, array or hash),
    it is the same if that keywiord is used in multiple 'section's.

    To see debug output, set __builtin__.G_debug to true

        from config import Config
        import sys
        import __builtin__
        __builtin__.G_debug = True      # turn on debugging

        try:
            conf = Config( 'blah.conf', 'blah-defs.conf', AcceptUndefinedKeywords=1)
        except ( IOError, SyntaxError, ValueError ) as err
            sys.stderr.write( '%s\\n' % str(err))
            sys.exit(1)
    """

    # states
    STATE_SECTION       = 1
    STATE_KEYWORDS      = 2
    STATE_NONE          = 3

    def __init__( self, config_file, defs_file="", **options ):
        """
        Initialization function.
        Not user callable.  Ignore this.  Go away.
        """

        self.config_file    	= config_file
        self.defs_file      	= defs_file

        i_am                    = __name__ + ":init()"
        self.accept_all_keys    = options.pop( 'AcceptUndefinedKeywords', False )
        self.values         	= {}

        # we have a pile of state to keep in our instance to make handling
        # recursive calls to __read_file() easier

        self.state          	= Config.STATE_NONE
        self.recursion_depth    = 0
        self.errors         	= []
        self.num_errs           = 0
        self.error_msg      	= ""

        # for the definitions file
        self.have_defs_file 	= 0         # set to 1 if exists and processed
        self.defs_type          = {}        # 'type'
        self.defs_ok_values     = {}        # 'allowed-values'
        self.defs_separator     = {}        # 'separator'
        self.defs_keywords      = {}        # 'keyword'
        self.defs_ok_keywords   = {}        # keywords defined in defs file

        self.section_name   	= ""        # current section being processed
        self.sections           = {}
        self.sections_ordered   = []

        # if user has not set G_debug, set it to false
        try:
            __builtin__.G_debug
        except (NameError, AttributeError) as e:
            __builtin__.G_debug = False

        if __builtin__.G_debug:
            print i_am + ': processing config file ' + config_file
            print i_am + ': processing definitions file ' + defs_file

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

        i_am            = __name__ + ":read_defs_file()"
        keyword         = ""        # keyword in effect
        allowed_types   = ( [ "scalar", "array", "hash" ] )
        error_msg       = ""
        num_errs        = 0

        line_number = 0 

        if __builtin__.G_debug:
            print i_am + ": processing definitions file: " + defs_file

        try:
            f = open( defs_file, "r" )
            for line in f:
                line_number += 1

                line2 = line.rstrip()                   # trailing whitespace
                if line2 == "": continue                # blank lines
                if line2.startswith( "#" ): continue    # comments

                m = re.match( "^([\w+\-]+)\s*=\s*(.*)\s*$", line2 )
                if m:
                    key   = m.group(1)
                    value = m.group(2)
                else:
                    error = "{0}: invalid line #{1:d} in {2} ({3})". \
                        format( i_am, line_number, defs_file, line2 )
                    error_msg += error + '\n'      # add to other errors
                    num_errs += 1

                if key == "keyword":
                    self.defs_keywords[ value ] = value
                    self.defs_ok_keywords[ value ] = 1
                    keyword = value
                elif key == "type":
                    if value not in allowed_types:
                        error = "{0}: invalid type ({1}) line #{2:d} in {3} ({4})". \
                            format( i_am, value, line_number, defs_file, line2 )
                        error_msg += error + '\n'      # add to other errors
                        num_errs += 1
                    self.defs_type[ keyword ] = value
                elif key == "separator":
                    self.defs_separator[ keyword ] = value
                elif key == "allowed-values":
                    values = value.split( "," )
                    self.defs_ok_values[ keyword ] = []
                    for v in values:
                        v = v.strip()       # leading  and trailing whitespace
                        self.defs_ok_values[ keyword ].append( v )
                else:
                    error = "{0}: invalid keyword ({1}) line #{2:d} in {3} ({4})". \
                        format( i_am, key, line_number, defs_file, line2 )
                    error_msg += error + '\n'      # add to other errors
                    num_errs += 1

            f.close

            if num_errs > 0:
                error_msg = error_msg.strip()   # strip trailing newline
                raise SyntaxError( error_msg )

        except IOError as e:
            if __builtin__.G_debug:
                print i_am + ": could not open: " + defs_file
            raise       # we ultimately ignore this further up the stack

        # print out our data structures if G_debug is set

        if __builtin__.G_debug:
            print i_am + ': data dump of definitions file ' + defs_file + ':'
            for k in self.defs_keywords:
                t = "scalar"
                s = ","

                print '\t' + k + ":"
                if k in self.defs_type: t = self.defs_type[ k ]
                if k in self.defs_separator: s = self.defs_separator[ k ]
                if k in self.defs_ok_values:
                    print "\t\tallowed values:"
                    for v in self.defs_ok_values[k]:
                        print "\t\t\t\'" + v + "\'"
                print "\t\tseparator: \'" + s + "\'"
                print "\t\ttype: \'" + t + "\'"


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

        Continuation lines can be done with a backslash at the end of a line.
        It is recursive, using '#include file' to read in other config files.
        """

        continuation        = 0     # flag for continuation line
        i_am            = __name__ + ":read_file()"

        self.recursion_depth += 1
        depth       = self.recursion_depth      # short-cut variable
        line_number = 0 

        if __builtin__.G_debug:
            debug_str = i_am + ": (depth=" + str(depth) + ")"
            print debug_str + " processing config file ", cnf_file

        try:
            f = open( cnf_file, "r" )
            for line in f:
                line_number += 1
                str1 = line.rstrip()

                # See if this is a continuation from a previous line
                if continuation == 1:
                    str1 = last_str + str1.lstrip()
                
                # See if there is a include file

                m = re.match( r"^#include\s+([\w/\.]+)$", str1 )
                if m:
                    include_file = m.group(1)
                    Config.__read_file( self, include_file )
                    continue

                if str1.startswith( "#" ): continue

                if str1.endswith( "\\" ):
                    continuation = 1
                    last_str = str1
                    last_str = last_str.rstrip( "\\" )
                    continue
                else:
                    continuation = 0

                # start of a new section
                m = re.match( "^(\w+)[:]*\s*", str1 )
                if m:
                    self.state = Config.STATE_SECTION
                    self.section_name = m.group(1)

                    if self.section_name not in self.sections:
                        self.sections[ self.section_name ] = {}
                        self.sections_ordered.append( self.section_name )

                    continue

                # inside a section
                m = re.match( "^\s+([\w\.\-]+)\s*=\s*(.*)\s*$", str1 )
                if m:
                    # ok, it's a 'keyword = value(s)' line
                    self.state = Config.STATE_KEYWORDS
                    keyword  = m.group(1)
                    value    = m.group(2)

                    # see if allowed (defined) keyword
                    if ((self.have_defs_file == 1) and (not self.accept_all_keys)):
                        if keyword not in self.defs_ok_keywords:
                            error = i_am + ": keyword (" + keyword + ") not defined " + \
                                "on line " + str(line_number) + " in: " + cnf_file
                            self.error_msg += error + '\n'      # add to other errors
                            self.num_errs += 1
                            continue

                    # defaults
                    separator   = ","
                    type        = "scalar"
                    ok_values   = ""

                    # need to find out what type of data this is
                    # If we have a definitions file, over-ride our defaults
                    if self.have_defs_file == 1:
                        if keyword in self.defs_keywords:
                            if keyword in self.defs_type:
                                type = self.defs_type[ keyword ]
                            if keyword in self.defs_separator:
                                separator   = self.defs_separator[ keyword ]
                            if keyword in self.defs_ok_values:
                                ok_values = self.defs_ok_values[ keyword ]

                    if __builtin__.G_debug: print debug_str + " type = " + type + \
                        " for " + self.section_name + "/" + keyword

                    obj = value         # default (scalar)
                    if type == "scalar":
                        # get rid of surrounding matching quotes
                        m = re.match( "^\'(.*)\'$", value )
                        if m:
                            value = m.group(1)
                        m = re.match( "^\"(.*)\"$", value )
                        if m:
                            value = m.group(1)
                        obj = value
                    elif type == "array":
                        values = value.split( separator )
                        obj = []
                        for val in values:
                            val = val.lstrip()
                            val = val.strip()
                            # get rid of surrounding matching quotes
                            m = re.match( "^\'(.*)\'$", val )
                            if m:
                                val = m.group(1)
                            m = re.match( "^\"(.*)\"$", val )
                            if m:
                                val = m.group(1)
                            obj.append( val )
                    elif type == "hash":
                        # we need to build a associative array (dictionary)
                        values = value.split( separator )
                        obj = {}
                        for val in values:
                            k, v = val.split( '=' )
                            # strip surrounding whitespace
                            k = k.strip()
                            v = v.strip()

                            # get rid of surrounding matching quotes
                            m = re.match( "^\'(.*)\'$", v )
                            if m: v = m.group(1)

                            m = re.match( "^\"(.*)\"$", v )
                            if m: v = m.group(1)

                            obj[ k ] = v

                    # this is dopey.  There has to be a easier way...
                    hash1 = self.sections[ self.section_name ]
                    hash1[ keyword ] = obj
                    self.sections[ self.section_name ] = hash1

                    continue        # not really needed (yet)

            f.close

            if (( depth == 1 ) and ( self.num_errs > 0 )):
                self.error_msg = self.error_msg.strip()
                raise ValueError(self.error_msg )

            # debugging info when we are all done the top (recursive) level
            if ( __builtin__.G_debug ) and ( depth == 1 ):
                print debug_str + " data dump from config file" + cnf_file + ":"
                for s in  self.sections:
                    print "\t" + s                  # section
                    for k in self.sections[ s ]:
                        print "\t\t", k, '=',       # keyword
                        obj = self.sections[ s ]
                        v = obj[k]
                        print "\'" + str(v)  + "\'" # value

        except IOError:
            # we don't want to clobber our error message deep down in a
            # recursive Hell.  So save our error message and as we bubble
            # up the stack, use the error from the previous call.  We do
            # this because we want to preserve the correct config file
            # in the error message

            if not self.error_msg:
                self.error_msg = i_am + ': ' + 'Cant open file: ' + cnf_file
                raise IOError( self.error_msg )
            else:
                raise

        except ValueError:
                raise

        finally:
            self.recursion_depth -= 1


    def get_type( self, keyword ):
        """
        Get the type of a keyword.

        type = conf.get_type( keyword )

        type can be any of 'scalar', 'array' or 'hash'.
        The config format could be any of:
            keyword1 = value1   (scalar)
            keyword2 = value2, value3, value4  (array)
            keyword3 = key5 = value5, key6 = value6, key7 = value7 (hash)
        """

        i_am    = __name__ + ":get_type()"

        type    = "scalar"      # default

        if not isinstance( keyword, basestring):
            raise ValueError( i_am + ": keyword argument is not a string" )

        if self.have_defs_file == 0: return( type )

        if keyword in self.defs_keywords:
            if __builtin__.G_debug:
                print i_am + ': (debug): we have a definitions file' + \
                    self.defs_file

            if keyword in self.defs_type:
                type = self.defs_type[ keyword ]
                if __builtin__.G_debug:
                    print i_am + ': (debug): found a type of ' + type \
                          + ' from ' + self.defs_file

        return( type )


    def get_separator( self, keyword ):
        """
        Get the separator of values.
            separator = conf.get_separator( keyword )

        The default separator is a comma (,) unless changed in the
        definitions file with a entry like:
            separator = string
        that goes with the keyword previously defined.  ie:
            keyword         = ip-domains
            type            = array
            allowed-values  = IPv4, IPv6
            separator       = ,

        The separator is not used for the 'allowed-values' as seen
        above in the definitions file example, but used as a separator
        in the config file for value types that are 'array's and hash's.
        """

        i_am    = __name__ + ":get_separator()"

        separator = ","      # default

        if not isinstance( keyword, basestring):
            raise ValueError( i_am + ": keyword argument is not a string" )

        if self.have_defs_file == 0: return( separator )

        if keyword in self.defs_keywords:
            if __builtin__.G_debug:
                print i_am + ': (debug): we have a definitions file: ' + \
                    self.defs_file

            if keyword in self.defs_separator:
                separator = self.defs_separator[ keyword ]
                if __builtin__.G_debug:
                    print i_am + ': (debug): found a separator of ' + \
                        "\'" + separator + "\'" + ' from ' + self.defs_file

        return( separator )


    def get_sections( self ):
        """
        Return a list of the section names in a config file

        sections = conf.get_sections()
        """
        i_am    = __name__ + ":get_sections()"

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

        i_am    = __name__ + ":get_keywords()"
        keys = []

        if not isinstance( section , basestring):
            raise ValueError( i_am + ": section argument is not a string" )

        if section in self.sections:
            for k in self.sections[ section ]:
                keys.append( k )
        else:
            if __builtin__.G_debug:
                print i_am + ": could not find any keywords for section " \
                    + "\'" + section + "\'"

        return( keys )


    def get_values( self, section, keyword ):
        """
        Return values of a keyword in a section

        values = conf.get_values( section, keyword )
        eg:
            sections = conf.get_sections()
            for section in sections:
                print section
                keywords = conf.get_keywords( section )
                for keyword in keywords:
                    print "\\t" + keyword
                    values = conf.get_values( section, keyword )
                    print "\\t\\t", values

        The data-type of the return value depends on the 'type' of
        the data.  By default it is a scalar, so a string would be 
        returned.  But the type can be changed via the optional
        definitions file, which can specify either a scalar, array
        or hash for a keyword.  The return value of get_values() 
        is the appropriate type.

        If the type is unknown to the program for a specific keyword,
        it can find out with a call to get_type().
        """
        i_am    = __name__ + ":get_values()"

        if not isinstance( section , basestring):
            raise ValueError( i_am + ": section argument is not a string" )
        if not isinstance( keyword, basestring):
            raise ValueError( i_am + ": keyword argument is not a string" )

        if section in self.sections:
            if keyword in self.sections[ section ]:
                for k in self.sections[ section ]:
                    if k != keyword: continue
                    obj = self.sections[ section ]
                    v = obj[k]
                    return( v )
            else:
                if __builtin__.G_debug:
                    print i_am + ": could not find keyword \'" + \
                        keyword + "\' in section \'" + section + "\'"
        else:
            if __builtin__.G_debug:
                print i_am + ": could not find section \'" + section + "\'"
        return( None )

if __name__ == "__main__":
    # test myself

    import sys

    __builtin__.G_debug = False
    try:
        conf = Config( './test.conf', "./test-defs.conf", AcceptUndefinedKeywords=1)
    except ( IOError, SyntaxError, ValueError ) as err:
        sys.stderr.write( '%s\n' % str(err))
        sys.exit(1)

    sections = conf.get_sections()
    for section in sections:
        print section + ':'
        keywords = conf.get_keywords( section )
        for keyword in keywords:
            print "\t" + keyword + ':'
            values = conf.get_values( section, keyword )
            print "\t\t", values
