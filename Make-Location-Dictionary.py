#!/usr/bin/env python

# Read a member dictionary (which has every member listed separately with
# their corresponding "raw" locations) and create a location dictionary
# which has unique entries for each location, and a list of members in that
# location.

from sys import argv
from pickle import load, dump

def sort_member(member_info, location_dictionary):
    name = member_info[0]
    location = member_info[1] 
    print('sort_member:')
    print('  Name: %s'%name)
    print('  loc:  %s'%location)

    if location_dictionary.get(location) == None:
        print('Adding %s to the location dictionary'%location)
        location_dictionary[location] = [ ]
    location_dictionary[location] += [ name, ]
    print('  Added %s to location "%s"'%(name, location))

def main(argv):
    if len(argv) != 2:
        print('Usage: %s meetup-group-name'%argv[0])
        exit(0)

    group_name = argv[1] 
    file = open(group_name + '.mdic', 'r')
    member_dictionary = load(file)
    file.close()

    location_dictionary = {}
    for item in member_dictionary.items(): 
        sort_member(item[1], location_dictionary)

    file = open(group_name + '.ldic', 'w')
    dump(location_dictionary, file)
    file.close()
        
main(argv)
