#!/usr/bin/python

# mkblocklist.py: Turn the list of Unicode codepoints into C data.

# Copyright (C) 2013-2017 Brian Raiter <breadbox@muppetlabs.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re
import sys

# This script parses the UnicodeData.txt file supplied by unicode.org
# which describes the current set of Unicode characters, and extracts
# the official name of each assigned codepoint and whether it is a
# combining character. The script filters out control characters and
# undefined sections. The data is then output as a C file containing
# an array initialization statement.

# A codepoint object corresponds to a single struct in the C array.
# uchar is the Unicode codepoint number of the character. name is the
# official name of the character. combining is True if the character
# is a combining character.

class codepoint(object):
  def __init__(self, uchar, name, combining=False):
    self.uchar = uchar
    self.combining = 1 if combining else 0
    self.name = name
    self.namesize = len(name)
    self.nameoffset = None

  def entry(self):
    return '{{{0},{1},{2},{3}}}'.format(self.nameoffset, self.namesize,
					self.uchar, self.combining)

# The complete list of Unicode characters.
charlist = []

# The size of the longest character name.
maxnamesize = 0

# Parse the Unicode data file. Each line is made up of multiple fields
# delimited by semicolons. This program only needs the information in
# the first three fields. The leftmost field contains the codepoint
# number (in hexadecimal). The next field contains the full official
# name of the codepoint (in all-caps). The third field contains a
# short sequence of letters that indicate attributes of the codepoint.
# A flag value of 'Mn' indicates a combining character, a value of
# 'Cc' indicates a non-graphical control character, etc. Finally, two
# codepoints in a row enclosed in angle brackets define a range of
# valid characters that are otherwise omitted from the data file (due
# to being largely redundant). This function identifies such ranges
# and expands them back to their full contents.

rstart = None
for line in sys.stdin:
  uchar, name, flags = line.split(';')[0:3]
  if flags[0] == 'C' and flags[1] != 'f':
    continue
  uchar = int(uchar, 16)
  name = name.lower()
  if name[0] == '<':
    m = re.match(r'(?i)<([^,]+), (first|last)>$', name)
    if rstart:
      name = m.group(1).lower()
      for u in xrange(rstart, uchar + 1):
	charlist.append(codepoint(u, name))
      rstart = None
    else:
      rstart = uchar
  else:
    charlist.append(codepoint(uchar, name, flags == 'Mn'))
  if maxnamesize < charlist[-1].namesize:
    maxnamesize = charlist[-1].namesize

# Transfer all the names into a single heap of strings. The strings
# are added to the heap in order of length, longest to shortest, so as
# to identify (and collapse) names that are substrings of longer
# names.

sys.stderr.write('Parsing the codepoint list ...\n')

nameheap = ''
for size in xrange(maxnamesize, 0, -1):
  for char in charlist:
    if char.namesize != size:
      continue
    char.nameoffset = nameheap.find(char.name)
    if char.nameoffset == -1:
      char.nameoffset = len(nameheap)
      nameheap += char.name
    char.name = None

# Finally, output the list of characters and the heap of name strings
# as C initialization statements.

sys.stdout.write(
    '/* This file is generated by mkcharlist.py. Do not edit directly. */\n')
sys.stdout.write('#include "data.h"\n')
sys.stdout.write('charinfo const charlist[] = {\n')
for char in charlist:
  sys.stdout.write(char.entry() + ',\n')

sys.stdout.write(
    '};\n'
    'int const charlistsize = sizeof charlist / sizeof *charlist;\n'
    'char const *charnamebuffer = "\\\n')
for i in xrange(0, len(nameheap), 76):
  sys.stdout.write(nameheap[i:i+76] + '\\\n')
sys.stdout.write('";\n')
