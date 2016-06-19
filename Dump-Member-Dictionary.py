#!/usr/bin/env python

#
# Dump a member dictionary 
#

from sys import argv
from pickle import load

def main(argv):
    if len(argv) != 2:
        print('Usage is: %s GROUP-NAME'%argv[0])
        exit(0)

    dict_name = argv[1] + '.mdic'
    f = open(dict_name, 'r')
    member_dictionary = load(f)
    f.close()

    for item in member_dictionary.items():
        print('Member: %s'%item[0])
        print('  Name:: %s'%item[1][0])
        print('  Location: %s'%item[1][1])

main(argv)
