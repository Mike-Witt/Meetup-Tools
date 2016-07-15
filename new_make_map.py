#!/usr/bin/env python

#############################################################################
#                                                                           #
#           Imports                                                         #
#                                                                           #
#############################################################################

import argparse
# import pickle (imported in fucntions that need it)
import sys
import os.path
# import mechanize (imported in functions that need it)
import urllib2
from time import sleep, time
import geopy
from geopy.geocoders import Nominatim
# from pyzipcode import ZipCodeDatabase (imported in functions that need it)

#############################################################################
#                                                                           #
#           Global debug level and debug() trace function.                  #
#                                                                           #
#############################################################################

debug_level = 10 # Default to 10

def debug(msg, level=20, nl=True):
    global debug_level
    if level > debug_level: return
    if nl: print(msg)
    else: print(msg),
    sys.stdout.flush()

#############################################################################
#                                                                           #
#           Main code. Actually executed at the bottom of the file.         #
#                                                                           #
#############################################################################

def main():
    global debug_level
    parser = setup_argparse()
    args = parser.parse_args()
    if args.debug_level != None: debug_level = args.debug_level
    print('debug_level: %s'%debug_level)

    # If the meetup page for your group is:
    #   http://www.meetup.com/Denver-Eccentrics-Meetup/
    # Then the group_name will be:
    #   'Denver-Eccentrics-Meetup'

    group_name = args.group_name

    #
    # Figure out what the user wants to do and call the appropriate code
    #

    # If the user asked to dump out either of the dictionary files, then
    # we are just going to do that, and simply ignore any other arguments.

    if args.disp_members:
        display_member_dictionary(group_name)
        exit(0)

    if args.disp_locs:
        display_location_dictionary(group_name)
        exit(0)

    # The other requests can all be processed together. But they need to
    # be done in the right order. Also, note that we will automatically
    # create a location dictionary if one is needed. But we will NOT scrape
    # meetup to create the member dictionary unless a download is requested.
    # Those details are handled in the functions below.

    if args.download: create_member_dictionary(group_name)
    if args.geo: create_location_dictionary(group_name)
    if args.kml: make_kml_map(args, group_name)
    if args.leaflet: make_leaflet_map(args, group_name)

#############################################################################
#                                                                           #
#           Setup argument parsing with "argparse"                          #
#                                                                           #
#############################################################################

def setup_argparse():
    parser = argparse.ArgumentParser(description='Map a meetup group')
    parser.add_argument('group_name',
        help='the name of the meetup group')
    parser.add_argument('--byloc', action='store_true',
        help='Map by location. Used with --kml or --leaflet')
    parser.add_argument('--bynum', action='store_true',
        help='Map by number of members. Used with --kml or --leaflet')
    parser.add_argument('-dm', '--disp_members', action='store_true',
        help='display a member dictionary')
    parser.add_argument('-dl', '--disp_locs', action='store_true',
        help='display a location dictionary')
    parser.add_argument('-d', '--download', action='store_true',
        help='download new information from meetup members page')
    parser.add_argument('-g', '--geo', action='store_true',
        help='make a location dictionary with geographic information')
    parser.add_argument('-l', '--leaflet', action='store_true',
        help='create the map as a leaflet javascript page')
    parser.add_argument('-k', '--kml', action='store_true',
        help='create the map as a kml file')
    parser.add_argument('--debug_level', type=int,
        help='debug level - higher for more messages')
    return(parser)

#############################################################################
#                                                                           #
#           These functions support basic web-scraping                      #
#                                                                           #
#############################################################################

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

#############################################################################
#                                                                           #
#           Generic dictionary save and load from file                      #
#                                                                           #
#############################################################################

#
# Load a dictionary file using pickle
#
def read_dict(dict_name):
    import pickle
    f = open(dict_name, 'r')
    dict = pickle.load(f)
    f.close()
    debug('Loaded dictionary: %s'%dict_name, 20)
    return(dict)

#
# Save a dictionary file for future use.
#
def write_dict(dict_name, dict):
    import pickle
    f = open(dict_name, 'w')
    pickle.dump(dict, f)
    f.close()
    debug('Saved dictionary: %s'%dict_name, 20)

#############################################################################
#                                                                           #
#           Creating and displaying Member Dictionaries                     #
#                                                                           #
#############################################################################

#
# Read the meetup members page and store the info in a ".mdic" file.
#
def create_member_dictionary(group_name):
    dict_name = group_name + '.mdic'
    debug('Creating: %s' %dict_name, 10)
    member_dictionary = {}

    first_link = 'http://www.meetup.com/%s/members/'%group_name
    next_link = first_link + '?offset=%s&;sort=last_visited&;desc=1'
    page = get_page(first_link)
    page, n_members_total = locate_and_extract(page, 'All members', '(', ')')

    # Need to eliminate a possible comma in the number of members
    n_members_total = int(n_members_total.replace(',',''))
    debug('We should find %s members' %n_members_total, 10)
    debug('Note: Status will be provided about once per minute ...', 10)

    n_members_read = 0
    start_time = time()
    last_status = time()

    while True:
        # Locate the next member link on the current members page
        page, mem_link = locate_and_extract(page, 'mem-photo', 'href="', '"')

        # If there isn't one, try to fetch the next members page
        if mem_link == '':
            debug('Fetching the next page ...', 20)
            nplink = next_link%n_members_read
            page = get_page(nplink)
            debug('  Link is: %s'%nplink, 20)
            page, mem_link \
                = locate_and_extract(page, 'mem-photo', 'href="', '"')
            debug(mem_link, 20)

        # It there's no next page then we're done
        if mem_link == '': break

        # Download and process the page for this member
        sleep(1) # Don't hit meetup more than once per second
        do_member(mem_link, member_dictionary)
        n_members_read += 1
        if n_members_read == n_members_total: break

        # Periodically let the user know what's happening
        if (time() - last_status) > 60:
            last_status = time()
            time_elapsed = time() - start_time
            time_per_member = time_elapsed / n_members_read
            min_left = (n_members_total - n_members_read) * time_per_member/60
            debug('Read %s members out of %s total. Est %s minutes left'
                %(n_members_read, n_members_total, int(min_left)), 10);

    debug('Expected to find %s members'%n_members_total, 10)
    debug('Read pages for   %s members' %n_members_read, 10)
    write_dict(dict_name, member_dictionary)

#
# Process a single member's page
#
def do_member(mem_link, member_dictionary):
    # We'll use the (string) member number as the key to the dictionary
    member_number = mem_link.split('/')[-2]
    debug('Member: %s,'%member_number, 20, nl=False),

    # Get the member's page
    mem_page = get_page(mem_link)

    # Get their first name
    mem_page, first_name = \
        locate_and_extract(mem_page, '<head>', '<title>', ' ')
    debug('name: %s,'%first_name, 20, nl=False),

    SCHEMA = 'http://schema.org/'
    mem_page, schema = \
        locate_and_extract(mem_page, 'Location:', SCHEMA, '">')
    debug('schema: %s,'%(SCHEMA + schema), 20, nl=False),

    PREFIX = 'http://www.meetup.com/'
    # Get their location
    mem_page, location = \
        locate_and_extract(mem_page, 'href', PREFIX, '">')
    if location[:6] != 'cities':
        print('ERROR: Location for was not ' + PREFIX + 'cities')
        exit(0)

    location = location[6:]
    member_dictionary[member_number] = [first_name, location]
    debug('location: %s'%location, 30)

    sys.stdout.flush()
    if schema != 'PostalAddress':
        print('ERROR: Schema was not "PostalAddress"')
        exit(0)

#
# Display the contents of a Member Dictionary
#
def display_member_dictionary(group_name):
    dict = read_dict(group_name + '.mdic')
    for item in dict.items():
        print('Member: %s'%item[0])
        print('  Name:: %s'%item[1][0])
        print('  Location: %s'%item[1][1])

#############################################################################
#                                                                           #
#           Creating and displaying Location Dictionaries                   #
#                                                                           #
#############################################################################

class location_dict_item:
    def __init__(self):
        self.country = ''
        self.city = ''
        self.zip = ''
        self.latitude = ''
        self.longitude = ''
        self.members = []

    def show(self):
        return(
            'country=%s, city=%s, zip=%s, lat=%s, lon=%s, members=%s'
            %(self.country, self.city, self.zip, self.latitude,
              self.longitude, self.members)
        )

class location_stats:
    def __init__(self):
        self.n_attempted = 0
        self.n_found = 0
        self.good_zips = 0
        self.good_cities = 0
        self.bad_zips = 0
        self.bad_cities = 0

    def show(self):
        return(
            '  number tried: %s\n'%self.n_attempted +
            '  number found: %s\n'%self.n_found +
            '  good_zips %s\n'%self.good_zips +
            '  bad_zips  %s\n'%self.bad_zips +
            '  good_cities %s\n'%self.good_cities +
            '  bad_cities  %s\n'%self.bad_cities
        )

def create_location_dictionary(group_name):
    dict_name = group_name + '.ldic'
    debug('Creating: %s' %dict_name, 10)
    member_dictionary = read_dict(group_name + '.mdic')
    location_dictionary = {}

    debug('Sorting members', 10)
    for item in member_dictionary.items():
        name = item[1][0]
        location = item[1][1]
        if location_dictionary.get(location) == None:
            debug('Adding %s to the location dictionary'%location)
            location_dictionary[location] = location_dict_item()
        item = location_dictionary[location]
        item.members += [ name, ]
        debug('  Added member "%s" to location "%s"'%(name, location))

    # Fill in the actual geographic coordinates
    debug('Finding geographic coordinates', 10)
    debug('Note: Status will be provided about once per minute ...', 10)
    stats = location_stats()
    num_locs = len(location_dictionary)
    num_done = 0
    start_time = time()
    last_status = time()
    for record in location_dictionary.items():
        location = record[0]
        item = record[1]
        get_location_info(stats, location, item)
        location_dictionary[location] = item
        num_done += 1
        if (time() - last_status) > 60:
            last_status = time()
            time_elapsed = time() - start_time
            time_per_loc = time_elapsed / num_locs
            min_left = (num_locs - num_done) * time_per_loc/60
            debug('%s locations done out of %s total. Est %s minutes left'
                %(num_done, num_locs, int(min_left)), 10);
    debug('Location statistics:', 10)
    debug('%s'%stats.show(), 10)

    # Write the dictionary out to disk
    write_dict(dict_name, location_dictionary)

def get_location_info(stats, location, item):
    from pyzipcode import ZipCodeDatabase
    zcdb = ZipCodeDatabase()
    stats.n_attempted += 1

    # Split the location string up, eliminating the nulls on both ends
    foo = location.split('/')[1:-1]
    item.country = foo[0]
    if item.country == 'us':
        item.zip = foo[1]
        try: place = zcdb[item.zip]
        except:
            debug(location, 20)
            debug('Can\'t find zip code %s'%item.zip, 20)
            stats.bad_zips += 1
            return
        if place == None or place == '':
            debug(location, 20)
            debug('Can\'t find zip code %s'%item.zip, 20)
            stats.bad_zips += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        stats.n_found += 1
        stats.good_zips += 1

    elif item.country == 'gb' or item.country == 'ca':
        if len(foo) != 3:
            debug(location, 20)
            debug('Country is %s but we don\'t have a region code'%item.country, 20)
            stats.bad_cities += 1
            return
        item.city = foo[2]
        lookup_string = item.city + ', ' + item.country
        place = geo_lookup(lookup_string)

        if place == None or place == '':
            debug(location, 20)
            debug('Can\'t find coords of country = "%s", city = "%s"'\
                %(item.country, item.city), 20)
            stats.bad_cities += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        stats.good_cities += 1
        stats.n_found += 1

    else:
        # So far, it *appears* the countries other than GB, CA and US
        # follow the format /COUNTRY/CITY
        if len(foo) != 2:
            debug('Country is %s. Can\'t parse: %s'
                %(item.country, location), 20)
            stats.bad_cities += 1
            return
        item.city = foo[1]
        lookup_string = item.city + ', ' + item.country
        place = geo_lookup(lookup_string)

        if place == None or place == '':
            debug('Can\'t find coords of country = "%s", city = "%s"'\
                %(item.country, item.city), 20)
            stats.bad_cities += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        stats.good_cities += 1
        stats.n_found += 1

# geo_lookup(), get_location_info(), and fill_in_geo_locations are all
#   used to put the actual geograhic coordinates (longitude and latidude)
#   into the Location Dictionary.

def geo_lookup(lookup_string):
    geolocator = Nominatim()
    sleep_time = 5
    # We'll potentially keep trying until we get either the answer or
    # an error other than timeout, etc.
    while(True):
        try:
            place = geolocator.geocode(lookup_string)
            return(place)
        except geopy.exc.GeocoderTimedOut:
            debug('GeocoderTimedOut, sleep %s seconds and retry ...'%sleep_time, 10)
            sleep(sleep_time)
            continue
        except geopy.exc.GeocoderUnavailable:
            debug('GeocoderUnavailable, sleep %s seconds and retry ...'%sleep_time, 10)
            sleep(sleep_time)
            continue
        except KeyboardInterrupt:
            print('User abort')
            exit(0)
        except:
            e = sys.exc_info()[0]
            print(location)
            print('Looking up: %s'%lookup_string);
            print('UNEXPECTED Geocoder error: %s'%e)
            return(None)

def display_location_dictionary(group_name):
    dict = read_dict(group_name + '.ldic')
    for item in dict.items():
       print('Location: %s'%item[0])
       print('  %s'%item[1].show())

#############################################################################
#                                                                           #
#                        KML Map File                                       #
#                                                                           #
#############################################################################

def make_kml_map(args, group_name):
    print('make_kml_map(): not done yet.')

#############################################################################
#                                                                           #
#                        Leaflet Map File                                   #
#                                                                           #
#############################################################################

def make_leaflet_map(args, group_name):
    print('make_leaflet_map(): not done yet.')

#############################################################################
#                                                                           #
#           Execute the program ...                                         #
#                                                                           #
#############################################################################
#
# ... if you want to use the functions individually in ipython, or as a
# library, just get rid of this call to main().
#
main()

