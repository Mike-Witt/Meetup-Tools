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
# import urllib2 (imported in functions that need it)
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
        self.bad_zips = 0
        self.good_cities = 0
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
#                Mapping Parameters and common Mapping Code                 #
#                                                                           #
#############################################################################

# Danger Will Robinson! Gobal variables for kml and leaflet files.

kml = None
leaflet_page = None

# These mapping parameters are (potentially) used by both the KML code and
# the Leaflet code.

class mapping_parms:

    def __init__(self):

        # number_table is a dictionary where the key is the number of members
        # and the value is number of locations which have that many members.

        self.number_table = {}

        # color_table is a dictionary where the key is the number of members
        # and the value is the color for locations with that many members.

        self.color_table = {}

        # These are the extremes of the geographic coordinates encountered.
        # This information is used to center the map and determine the zoom
        # factor (for leaflets only.)

        self.high_lat = -91
        self.high_lon = -181
        self.low_lat = 91
        self.low_lon = 181

        # Specific icon to be used (currently google maps only).
        # Hardcoded. Select one by editing: self.ICON =
       
        PREFIX = 'http://www.gstatic.com/mapspro/images/stock/' 
        DEFAULT = PREFIX + '503-wht-blank_maps.png'
        STAR  = PREFIX + '960-wht-star-blank.png'
        HOUSE = PREFIX + '1197-fac-headquarters.png'

        self.ICON = STAR # Edit me to change icon

        # Intensity for locations with most members (0 is the most intense)

        self.high_color = 0

        # Intensity for locations with least members

        self.low_color = 200

# In the location dictionary we'll have multiple entries which actually
# refer to the same geographic location. These need to be merged together.
# This code is currently called when the map is produced. But it would
# probably be better to do it when the location dictionary is created.

def merge_duplicate_locations(location_dictionary):

    # Build a temporary dictionary indexed by geo coords (as strings)
    geo_dict = {}

    # Examine each item in the location dict.
    for item in location_dictionary.items():
        lon = str(item[1].longitude)
        lat = str(item[1].latitude)
        if lat == None: continue
        if lat == '' : continue
        if lon == None: continue
        if lon == '': continue
        key = str(lon) + ',' + str(lat)

        # If we get a hit, merge the two in the original location dict.
        if key in geo_dict:
            merge_locations(location_dictionary, geo_dict[key], item[0], key)

        # Otherwise add it to the temp dict
        else:
            geo_dict[key] = item[0]

def merge_locations(location_dictionary, target, source, coords):

    # Target and source are raw location (indices in the location_dictionary).
    # Merge all the members from source into target

    debug('  %s and %s have the same geographic coordinates: %s'
        %(target, source, coords), 20)
    debug('    Merging members from %s into %s and deleting %s'
        %(source, target, source), 20)
    target_item = location_dictionary[target]
    source_item = location_dictionary[source]
    target_item.members += source_item.members
    del location_dictionary[source]

# 
# Fiddle with the "quoting" used in the URLs
#
def fix_url_quotes(location_dictionary):
    import urllib2
    for item in location_dictionary.items():
        city = item[1].city
        if '%' in city:
            new_city = urllib2.unquote(city)
            debug('  Fixing: %s --> %s'%(city, new_city))
            item[1].city = new_city
            location_dictionary[item[0]] = item[1]

#
# get_stats():
#
# Here we do things like find out the range of latitude and longitude to
# be incorporated into the map, determine the color to be used based on
# how many members in a location, and so on.
#
def get_stats(mp, location_dictionary):
    for item in sorted(location_dictionary.items(), key=mykey, reverse=True):

        # If we've got good coordinates, then save the highs and lows
        try:
            lon = float(item[1].longitude)
            lat = float(item[1].latitude)
            if lon > mp.high_lon: mp.high_lon = lon
            if lat > mp.high_lat: mp.high_lat = lat
            if lon < mp.low_lon: mp.low_lon = lon
            if lat < mp.low_lat: mp.low_lat = lat
        except ValueError: pass

        location = item[0]
        people = item[1].members
        n_members = len(people)
        try:
            n_locations = mp.number_table[n_members]
            mp.number_table[n_members] = n_locations + 1
        except:
            mp.number_table[n_members] = 1
            mp.color_table[n_members] = 0
    debug('get_stats:', 20)
    debug('The number_table has %s entries'%len(mp.number_table), 20)
    division = (mp.low_color - mp.high_color) / (len(mp.number_table) - 1)
    current_color = mp.high_color
    debug('A color division is: %s'%division, 20)
    for n_members in sorted(mp.number_table, reverse=True):
        n_locations = mp.number_table[n_members]
        mp.color_table[n_members] = current_color
        current_color += division

        msg = '  There are %s locations with %s members'%(n_locations, n_members)
        msg += ', color: %s'%mp.color_table[n_members]
        debug(msg, 20)

    # It appears we need to add a fudge factor to the latitude to get
    # everything inside the leaflet map.
    mp.high_lat += (mp.high_lat - mp.low_lat)*.20
    mp.low_lat -= (mp.high_lat - mp.low_lat)*.20

    debug('Latitude: (%s, %s), Longitude: (%s, %s)' %(mp.low_lat, mp.high_lat, mp.low_lon, mp.high_lon), 20)

#############################################################################
#                                                                           #
#                        KML Map File                                       #
#                                                                           #
#############################################################################

# For general information on the Keyhole Markup Language (KML)
# see: https://developers.google.com/kml

#
# Write the prefix of the .kml file
#
def start_kml(group_name):
    global kml
    kml = open(group_name + '.kml', 'w')
    kmlline("<kml xmlns='http://www.opengis.net/kml/2.2'>")
    kmlline("    <Document>")
    kmlline("        <name>No Name</name>")
    kmlline("        <description><![CDATA[]]></description>")
    kmlline("")
    kmlline("        <Folder>")
    kmlline("        <name>Members</name>")

#
# Write one line of the .kml file
#
def kmlline(text):
    global kml
    kml.write(text + '\n')

#
# A kml icon
#
def kml_icon(name, value, icon_type):
    kmlline("        <Style id='icon-%s'>"%name)
    kmlline("            <IconStyle>")
    kmlline("                <color>ff%02x%02xff</color>"%(value,value))
    kmlline("                <scale>1.1</scale>")
    kmlline("                <Icon>")
    kmlline("                    <href>%s</href>"%icon_type)
    kmlline("                </Icon>")
    kmlline("                <hotSpot x='16' y='31' xunits='pixels' yunits='insetPixels'>")
    kmlline("                </hotSpot>")
    kmlline("            </IconStyle>")
    kmlline("            <LabelStyle>")
    kmlline("                <scale>0.0</scale>")
    kmlline("            </LabelStyle>")
    kmlline("        </Style>")

#
# Write the suffix of the .kml file
#
def end_kml(mp):
    global kml
    kmlline("        </Folder>")
    kmlline("")

    # Make an icon for each color needed
    debug('end_kml():', 20)
    for n_members in sorted(mp.number_table, reverse=True):
        color = mp.color_table[n_members]
        icon_name = str(n_members)
        debug('icon_name: %s, color: %s'%(icon_name, color), 10)
        kml_icon(icon_name, color, mp.ICON)
        kmlline("")

    kmlline("    </Document>")
    kmlline("</kml>")

#
# Main code for generating a KML map
#
def make_kml_map(args, group_name):
    location_dictionary = read_dict(group_name + '.ldic')
    merge_duplicate_locations(location_dictionary)
    fix_url_quotes(location_dictionary)
    mp = mapping_parms()
    get_stats(mp, location_dictionary)
    start_kml(group_name)

    # If the user specified "by location" we'll do that. Otherwise
    # we'll default to sorting by number of members per location.

    if args.byloc:
        for item in sorted(location_dictionary.items()):
            map_location_kml(mp, item[0], item[1])

    else:
        # We're doing --bynum here ...
        for item in sorted(
            location_dictionary.items(),
            key=mykey, reverse=True):
         map_location_kml(item[0], item[1])

    end_kml(mp)

#
# Map a single KML location
#
def map_location_kml(location, item):
    lon = item.longitude
    lat = item.latitude

    # Skip this item if we never found the coordinates
    if lon == '' or lat == '':
        debug('Skipping: %s (%s members)'%(location, len(item.members)), 20)
        return

    members = item.members
    coords = '<coordinates>%s,%s,0.0</coordinates>'%(lon,lat)

    N = len(members)
    data = ''
    for n in range(N):
        if n != 0: data += "<br>"
        data += members[n]

    if item.zip != '':
        loc = item.zip
    else:
        loc = item.city[0].upper() + item.city[1:] + ', ' + item.country.upper()

    icon_name = str(N)
    kmlline("        <Placemark>")
    kmlline("            <name>Location: %s (%s members)</name>"%(loc, N))
    kmlline("            <description><![CDATA[%s]]></description>"%data)
    kmlline("            <styleUrl>#icon-%s</styleUrl>"%icon_name)
    kmlline("            <Point>")
    kmlline("                %s"%coords)
    kmlline("            </Point>")
    kmlline("        </Placemark>")
    kmlline("")

#############################################################################
#                                                                           #
#                        Leaflet Map File                                   #
#                                                                           #
#############################################################################

# Note that the current version just blindly writes a page full of javascript
# statements, with code being generated for each location. There is nothing
# intelligent going on here with the javascript. This should probably be
# changed.
#
# I've got a file called "leaflet-start" which has javascript that needs to
# be written to the page first. It has a couple of parameters which are re-
# written in the "start_leaflet" function. Then after all the other script is
# generated, the "end_leaflet" function will paste on whatever's in the
# "leaflet-end" file.

def start_leaflet(mp, group_name):
    global leaflet_page
    title = 'Leaflet Meetup Map'
    heading = group_name
    leaflet_page = open(group_name + '.html', 'w')
    leaflet_start = open('leaflet-start', 'r')
    lstart = leaflet_start.read()
    leaflet_page.write(lstart%(title, heading, mp.low_lat, mp.low_lon, mp.high_lat, mp.high_lon))
    leaflet_start.close()

def leafln(text):
    global leaflet_page
    leaflet_page.write(text + '\n')

def end_leaflet():
    global leaflet_page
    leaflet_end = open('leaflet-end', 'r')
    leaflet_page.write(leaflet_end.read())
    leaflet_end.close()
    leaflet_page.close()

#
# Helper function to sort by number of members in a location
#
def mykey(x):
    # x[0] is the key (the "raw" location)
    # x[1] is a location_dict_item
    return(len(x[1].members))

#
# Here's the main code for making a leaflet map.
#
def make_leaflet_map(args, group_name):
    location_dictionary = read_dict(group_name + '.ldic')
    merge_duplicate_locations(location_dictionary)
    fix_url_quotes(location_dictionary)
    mp = mapping_parms()
    get_stats(mp, location_dictionary)
    start_leaflet(mp, group_name)

    # If the user specified "by location" we'll do that. Otherwise
    # we'll default to sorting by number of members per location.

    if args.byloc:
        for item in sorted(location_dictionary.items()):
            map_location_leaflet(mp, item[0], item[1])

    else:
        # We're doing --bynum here ...
        for item in sorted(
            location_dictionary.items(),
            key=mykey, reverse=True):
         map_location_leaflet(mp, item[0], item[1])

    end_leaflet()
 
#
# Write out the script for a single location on the map
#
def map_location_leaflet(mp, location, item):
    lon = item.longitude
    lat = item.latitude
    debug('map_location_leaflet(): lat=%s, lon=%s' %(lat, lon), 30)

    # Skip this item if we never found the coordinates
    if lon == '' or lat == '':
        debug('Skipping: %s (%s members)'%(location, len(item.members)), 30)
        return

    if item.zip != '':
        loc = item.zip
    else:
        debug('City="%s", Country="%s"'%(item.city, item.country), 30)
        loc = item.city[0].upper() + item.city[1:] + ', ' + item.country.upper()

    leafln('    L.marker([%s, %s]).addTo(mymap)' %(lat, lon))
    leafln('        .bindPopup(')

    # With location
    #members_string = 'Location: %s'%loc
    members_string = '<b>%s</b>'%loc
    for n in range(len(item.members)):
        members_string += '<br>'
        members_string += '%s'%item.members[n]

    """
    # Without location
    members_string = ''
    for n in range(len(item.members)):
        if n != 0: members_string += '<br>'
        members_string += '%s'%item.members[n]
    """

    leafln('            "%s")' %members_string)

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

