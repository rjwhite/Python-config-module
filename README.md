# Read config file(s) with Python module

## Description
This module is a set of OOP methods to read a config file and provide access
to its sections, keywords and values.  A section is a grouping of
   ***keyword = values***.
A section begins at the beginning of a line and the keywords for that
section are indented.  A keyword can point to a scalar value, an array of
values, or an associative array of values.

Lines can be continued across multiple lines by ending a line with a
backslash.  Values are separated by commas.
To have a comma or a backslash as part of the data, escape them with a backslash.

Other config files can be included, to any depth, via a ***#include*** line.

Comments begin with a '#' character (if it isn't a #include) and blank lines
are ignored.

To preserve whitespace around values, use matching single or double quotes
around a value.

An optional definitions file can be provided so that a different separator
than a comma can be given, restriction to a set of allowed values, and
provide the type of value there instead of in the main config file.
These can be specified for a specific keyword within a section, or
globally to a keyword that may be present in multiple sections.

If a definitions file is provided, then keywords cannot be in the config
file, unless they are defined in the definitions file.  Unless the option
'AcceptUndefinedKeywords' is provided and set to 'yes'.

If a 'type' is provided in both the config file and the definitions file
for a section/keyword, then they must match.  One does not over-ride
the other.

To see documentation, do a pydoc config

### Class methods
- set_debug()

### Instance methods
- get_sections()
- get_keywords()
- get_type()
- get_values()

## Config file example
    # This is a comment
    section-name1:
        keyword1 (scalar) = value1
        keyword2          = value2
        keyword3          = 'this is a really big multi-line \
                             value with spaces on the end   '
        keyword4 (array)  = val1, val2, 'val 3   ', val4
        keyword5 (hash)   = v1 = this, \
                            v2 = " that ", \
                            v3 = fooey

    #include some/other/file.conf

    section-name2:
        keyword4      = This keyword4 is separate from the \
                        keyword4 in the section section-name1
        something     = 'This has a comma here \, in the data'

    section-name1:
        more-stuff    = more stuff for section-name1

## Definitions file example
     # This keyword1 will only apply to section section-name1
     keyword                = section-name1:keyword1
     type                   = array
     separator              = ;
     allowed-values         = val1, val2, val3, \
                              'val 4   '

     # this keyword2 will apply to all sections
     keyword                = keyword2
     type                   = hash
     separator              = ,

## Code example
    #!/usr/bin/env python3
    
    from config_moxad import config
    import sys
    
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
            print( "\t" + keyword + ':' )
    
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
