#!/usr/bin/env python
# coding=utf-8

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "../lib"))
import re, json

#------------------   def string_hascontent(): start     -----------------#
def string_hascontent( teststring: str ):
    return len(str(teststring))>=1 and not str(teststring).isspace()
#------------------   def string_hascontent(): end       -----------------#

#------------------   def string_preformat(): star t     -----------------#
def string_preformat( msg: str ):
    """ allow {{key}} to be used for formatting in text
    that already uses curly braces.  First switch this into
    something else, replace curlies with double curlies, and then
    switch back to regular braces
    https://stackoverflow.com/questions/5466451/how-do-i-print-curly-brace-characters-in-a-string-while-using-format
    """
    msg = msg.replace('{{', '<<<').replace('}}', '>>>')
    msg = msg.replace('{', '{{').replace('}', '}}')
    msg = msg.replace('<<<', '{').replace('>>>', '}')
    return msg
#------------------   def string_preformat(): end        -----------------#