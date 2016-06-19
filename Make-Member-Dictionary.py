#!/usr/bin/env python

#
# Make a dictionary of group members
#

from pickle import dump
from sys import argv, stdout
from mtlib import get_page, locate_and_extract

def do_member(mem_link, member_dictionary):
    # We'll use the (string) member number as the key to the dictionary
    member_number = mem_link.split('/')[-2]
    print('Member: %s,'%member_number),
   
    # Get the member's page 
    mem_page = get_page(mem_link)

    # Get their first name
    mem_page, first_name = \
        locate_and_extract(mem_page, '<head>', '<title>', ' ')
    print('name: %s,'%first_name),

    SCHEMA = 'http://schema.org/'
    mem_page, schema = \
        locate_and_extract(mem_page, 'Location:', SCHEMA, '">')
    print('schema: %s,'%(SCHEMA + schema)),

    PREFIX = 'http://www.meetup.com/'
    # Get their location
    mem_page, loc = \
        locate_and_extract(mem_page, 'href', PREFIX, '">')
    location = PREFIX + loc

    member_dictionary[member_number] = [first_name, location] 
    print('location: %s'%location)

    stdout.flush() 
    if schema != 'PostalAddress':
        print('ERROR: Schema was not "PostalAddress"')
        exit(0)
    
def make_member_dictionary(group_name):
    member_dictionary = {}

    first_link = 'http://www.meetup.com/%s/members/'%group_name
    next_link = first_link + '?offset=%s&;sort=last_visited&;desc=1'

    page = get_page(first_link)
    page, n_members_total = locate_and_extract(page, 'All members', '(', ')')

    # Need to eliminate a possible comma in the number of members
    n_members_total = int(n_members_total.replace(',',''))

    print('We should find %s members' %n_members_total)
    n_members_read = 0
    while True:
        # Locate the next member link on the current members page
        page, mem_link = locate_and_extract(page, 'mem-photo', 'href="', '"')

        # If there isn't one, try to fetch the next members page
        if mem_link == '':
            print('Fetching the next page ...')
            nplink = next_link%n_members_read
            page = get_page(nplink)
            print('  Link is: %s'%nplink)
            page, mem_link \
                = locate_and_extract(page, 'mem-photo', 'href="', '"')
            print(mem_link)

        # It there's no next page then we're done
        if mem_link == '': break

        # Download and process the page for this member
        do_member(mem_link, member_dictionary)
        n_members_read += 1
        if n_members_read == n_members_total: break

    print('Expected to find %s members'%n_members_total)
    print('Read pages for   %s members' %n_members_read)
    return(member_dictionary)

def main(argv):
    if len(argv) != 2:
        print('Usage is: %s GROUP-NAME'%argv[0])
        exit(0)
    group_name = argv[1]
    member_dict = make_member_dictionary(argv[1])
    file = open(group_name + '.mdic', 'w')
    dump(member_dict, file)
    file.close()

main(argv)
