#!/usr/bin/env python

#
# Make a dictionary of meetup members by location
#

import pickle
import sys
from geopy.geocoders import Nominatim
from pyzipcode import ZipCodeDatabase

#
# Global vars
#

next_link = ''
page = ''
n_members_total = 0
n_members_read = 0
n_members_located = 0
zcdb = ZipCodeDatabase()
member_dictionary = {}

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

#
# Attempt to map a location to latitude and longitude.
#

def get_coords(country, town, zipcode, extra):
    geolocator = Nominatim()
    lat = None
    lon = None

    # We are given: country, town, and zipcode (some of which are blank)

    # If we have a zipcode use pyzipcode since we have a local database
    if zipcode != '':
        try:
            z = zcdb[zipcode]
            lat = z.latitude
            lon = z.longitude
        except:
            print('We have a zipcode: %s, but it\'s not in the database')
            return('')

    # Otherwise, we hope to have both country and town names
    elif country != '' and town != '':
        try:
            location = geolocator.geocode(zipcode)
            lat = location.latitude
            lon = location.longitude
            coords = '<coordinates>%s,%s,0.0</coordinates>'%(lon, lat)
        except:
            print('Can\'t find coords of country = "%s", town = "%s"'\
                %(country, town))
            return('')

    else:
        print('Can\'t parse that location')
        return('')

    coords = '<coordinates>%s,%s,0.0</coordinates>'%(lon, lat)
    print(coords)
    return(coords)             

#
# Function for processing a single member page
#

def get_member_name(mem_page):
    # Currently we extract the first name only for mapping purposes
    mem_page, first_name = \
        locate_and_extract(mem_page, '<head>', '<title>', ' ')
    return(mem_page, first_name)

def get_member_location(mem_page):
    country = ''
    town = ''
    zipcode = ''
    extra = ''

    PREFIX = 'meetup.com/cities/'

    mem_page, country = \
        locate_and_extract(mem_page, 'Location:', PREFIX, '/')
    print('Found country = %s'%country)

    if country == 'us':
        mem_page, zipcode = locate_and_extract(mem_page, '', '', '/')
        print('Found zipcode = %s'%zipcode)
        extra = PREFIX + zipcode + '/'

    elif country == 'gb':
        mem_page, code = locate_and_extract(mem_page, '', '', '/')
        mem_page, town = locate_and_extract(mem_page, '', '', '/')
        print('Found: code = %s, town = %s'%(code, town))
        extra = PREFIX + code + '/' + town + '/'

    else:
        print('Don\'t know country "%s"'%country)
        extra = PREFIX + code + '/' + town + '/'

    return(mem_page, country, town, zipcode, extra)

def do_member(mem_page):
    # Get the member's display name
    mem_page, member_name = get_member_name(mem_page)

    # Get the member's location
    mem_page, country, town, zipcode, extra \
        = get_member_location(mem_page)

    # Attempt to map the location to geographics coordinates
    coords = get_coords(country, town, zipcode, extra)

    # Add everything to the database
    key = extra
    if member_dictionary.get(key) == None:
        print('Adding %s to dictionary'%key)
        print('country=%s, town=%s, zipcode=%s, coords=%s'\
            %(country, town, zipcode, coords))
        location = [country, town, zipcode, coords]
        people = []
        member_dictionary[key] = [location, people]
   
    location, people = member_dictionary[key] 
    people += [ member_name, ]
    member_dictionary[key] = [location, people]

#
# The mainline code is here
#

def main(argv):
    global page, n_member_total, n_members_read, n_members_located, next_link

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

    page, n_members_total = locate_and_extract(page, 'All members', '(', ')')
    # Need to eliminate a possible comma in the number of members
    n_members_total = int(n_members_total.replace(',',''))
    n_members_total = int(n_members_total)
    print('We should find %s members' %n_members_total)

    while True:
        # Locate the next member link on the current members page
        page, mem_link = locate_and_extract(page, 'mem-photo', 'href="', '"')
        print('TOP OF MAIN LOOP: mem_link = %s'%mem_link)

        # If there isn't one, try to fetch the next members page
        if mem_link == '':
            print('Fetching the next page ...')
            page = next_link%n_members_read
            page, mem_link \
                = locate_and_extract(page, 'mem-photo', 'href="', '"')
            print(mem_link)

        # It there's no next page then we're done
        if mem_link == '': break

        # Download and process the page for this member
        mem_page = get_page(mem_link)
        do_member(mem_page)

        n_members_read += 1
        if n_members_read == n_members_total: break

    print('Read pages for %s members' %n_members_read)
    print('Found locations for %s members' %n_members_located)
    dictfile = group_name + '.dic'
    print('Writing the dictionary to: %s'%dictfile)
    f = open(dictfile, 'w')
    pickle.dump(member_dictionary, f)
    f.close()
    print('Done!')

#
# Execute the main function with the given command line arguments
#

main(sys.argv)

