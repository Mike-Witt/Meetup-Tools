#!/usr/bin/env python

#
# Add geographic coordinates to the location dictionary
#

from pickle import load, dump
from sys import argv
from geopy.geocoders import Nominatim
from pyzipcode import ZipCodeDatabase

def get_location_info(location):
    # TEST
    return(['x', 'y', 'z'])

def main(argv):
    if len(argv) < 2:
        print('Usage: %s group-name'%argv[0])
        exit(0)

    group_name = argv[1]
    file = open(group_name + '.ldic', 'r')
    location_dictionary = load(file)
    file.close()

    for item in location_dictionary.items():
        location = item[0]
        location_info = get_location_info(location)
        location_dictionary[location] += location_info

    file = open(group_name + '.ldic', 'w')
    dump(location_dictionary, file)
    file.close()

main(argv)
