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

A optional definitions file can be provided so that a different separator
than a comma can be given, restriction to a set of allowed values, and
provide the type of value (scalar, array, hash).

If a definitions file is provided, then keywords cannot be in the config
file, unless they are defined in the definitions file.  Unless the option
'AcceptUndefinedKeywords' is provided and set to 1.

### Instance methods
- get_sections()
- get_keywords()
- get_separator()
- get_type()
- get_values()

## Config file example
    # This is a comment, with scalar, array and associative array
    section-name1:
        keyword1            = value1
        keyword2            = value2
        keyword3            = 'this is a really big multi-line \
                               value with spaces on the end   '
        keyword4            = val1, val2, 'val 3   ', val4
        keyword5            = v1 = this, \
                              v2 = " that ", \
                              v3 = fooey

    #include some/other/file.conf

## Definitions file example
     keyword                = keyword4
     type                   = array
     separator              = ,
     allowed-values         = val1, val2, val3 \
                              'val 4   '

     keyword                = keyword5
     type                   = hash
     separator              = ,

## Code example
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
