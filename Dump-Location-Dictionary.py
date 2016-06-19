#!/usr/bin/env python

#
# Dump a location dictionary 
#

from sys import argv
from pickle import load

def main(argv):
    if len(argv) != 2:
        print('Usage is: %s GROUP-NAME'%argv[0])
        exit(0)

    dict_name = argv[1] + '.ldic'
    f = open(dict_name, 'r')
    location_dictionary = load(f)
    f.close()

    for item in location_dictionary.items():
        print('Location: %s'%item[0])
        print('  Members: %s'%item[1])

main(argv)
