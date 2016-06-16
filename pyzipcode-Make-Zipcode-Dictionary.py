#!/usr/bin/env python

#
# Make a dictionary of meetup members by location
#

import pickle
import sys
from pyzipcode import ZipCodeDatabase

#
# Global vars
#

next_link = ''
page = ''
n_members = 0
n_found = 0
zcdb = ZipCodeDatabase()
zip_dict = {}

# locate_and_extract()
#
# First skip text until you have read "locator." Then extract the text
# between "start" and "end" and return it. For example, if you have
# something like this:
#
# <div class="price">
# <b>Price in dollars: $29.95</b>
# </div>
#
# and you just want the actual number 29.95, you could do:
# locate_and_extract(page, '<div class="price">', ': $', '</b>')
#
def locate_and_extract(page, locator, start, end):
    try:
        ptr = page.index(locator)
        page = page[ptr+len(locator):]
        ptr = page.index(start)
        page = page[ptr+len(start):]
        ptr = page.index(end)
    except:
        return('', '')
    value = page[:ptr]
    page = page[ptr+len(end):]
    return(page, value)

# get_page()
#
# Return the page specified by "url"
#
def get_page(url):
    import mechanize
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.set_handle_equiv(False)
    br.addheaders = [('User-agent', 'Mozilla/5.0')] 
    response = br.open(url)   
    return(response.read())

def do_member():
    global page, n_members, n_found, zcdb, zip_dict
    page, mem_link = locate_and_extract(page, 'mem-photo', 'href="', '"')

    if mem_link == '':
        # Try to fetch the next page
        print('Fetching the next page ...')
        nplink = next_link%n_found
        print(nplink)
        page = get_page(nplink)
        if page == '': return(-1)
        page, mem_link = locate_and_extract(page, 'mem-photo', 'href="', '"')

    mem_page = get_page(mem_link)
    mem_page, first_name = \
        locate_and_extract(mem_page, '<head>', '<title>', ' ')

    # WARNING: NEXT LINE ONLY WORKS FOR US CITIES!!!
    mem_page, zipcode = \
        locate_and_extract(mem_page, 'Location:', 'cities/us/', '/')
    print('%s of %s - Name: %s, Zip code: %s'\
        %(n_found+1, n_members, first_name, zipcode))

    if zip_dict.get(zipcode) == None:
        print('Adding %s to dictionary'%zipcode)
        zip_dict[zipcode] = []
    zip_dict[zipcode] += [ first_name, ]

    return(1)

def do_zipcode(zipcode):
    try:
        z = zcdb[zipcode]
    except:
        print("Don't know zip code: '%s'"%zipcode)
        return # Just skip members with unknown zip code
    lat = z.latitude
    lon = z.longitude
    coords = '<coordinates>%s,%s,0.0</coordinates>'%(lon, lat) 
    #print('zip = %s, coord = %s'%(zipcode, coords))

    people = zip_dict[zipcode]
    data = ''
    for n in range(len(people)):
        if n != 0: data += "<br>"
        data += people[n]

#
# The mainline code is here
#

def main(argv):
    global page, n_members, n_found, next_link

    if len(argv) != 2:
        print('Usage: %s meetup-group-name'%argv[0])
        print('For example:')
        print('%s Denver-Physics-Philosophy-Meetup'%argv[0])
        exit(0)

    # What meetup calls the group
    meetup_group_name = argv[1] 
    # What I call the group
    group_name = meetup_group_name

    first_link = 'http://www.meetup.com/%s/members/'%meetup_group_name
    next_link = first_link + '?offset=%s&;sort=last_visited&;desc=1'

    page = get_page(first_link)
    #f = open('00_Members.html', 'w')
    #f.write(page)
    #f.close()

    page, n_members = locate_and_extract(page, 'All members', '(', ')')
    n_members = int(n_members)
    print('We should find %s members' %n_members)

    while True:
        RC = do_member()
        if RC == -1: break
        n_found += 1
        if n_found == n_members: break

    print('Actually processed %s members' %n_found)
    for z in zip_dict: do_zipcode(z)
    dictfile = group_name + '.dic'
    print('Writing the dictionary to: %s'%dictfile)
    f = open(dictfile, 'w')
    pickle.dump(zip_dict, f)
    f.close()
    print('Done!')

#
# Execute the main function with the given command line arguments
#

main(sys.argv)

