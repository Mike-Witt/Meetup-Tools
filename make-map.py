#!/usr/bin/env python

import argparse
import pickle
import sys
import os.path
import mechanize
import urllib2
from time import sleep
import geopy
from geopy.geocoders import Nominatim
from pyzipcode import ZipCodeDatabase

#############################################################################
#                                                                           #
#           Argument parsing with "argparse"                                #
#                                                                           #
#############################################################################

parser = argparse.ArgumentParser(description='Map a meetup group')
parser.add_argument('group_name', 
    help='the name of the meetup group')
parser.add_argument('--byloc', action='store_true', 
    help='map by location')
parser.add_argument('--bynum', action='store_true', 
    help='map by number of members in location')
parser.add_argument('-dm', '--disp_members', action='store_true', 
    help='display a member dictionary')
parser.add_argument('-dl', '--disp_locations', action='store_true', 
    help='display a location dictionary')
parser.add_argument('-D', '--download', action='store_true', 
    help='scrape meetup to download new information')
parser.add_argument('--make_ldic', action='store_true', 
    help='make a location dictionary from the member data')
parser.add_argument('-l', '--leaflet', action='store_true', 
    help='create a leaflet javascript page')
parser.add_argument('-d', '--debug_level', type=int,
    help='debug level - higher for more messages')

#############################################################################
#                                                                           #
#           Miscellaneous and Debug functions                               #
#                                                                           #
#############################################################################

debug_level = 10

def debug(msg, level=20, nl=True):
    global debug_level
    if level > debug_level: return
    if nl: print(msg)
    else: print(msg),
    sys.stdout.flush()

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
    f = open(dict_name, 'r')
    dict = pickle.load(f)
    f.close()
    debug('Loaded dictionary: %s'%dict_name, 10)
    return(dict)

#
# Save a dictionary file for future use.
#
def write_dict(dict_name, dict):
    f = open(dict_name, 'w')
    pickle.dump(dict, f)
    f.close()
    debug('Saved dictionary: %s'%dict_name, 10)

#############################################################################
#                                                                           #
#           Creating and displaying Member Dictionaries                     #
#                                                                           #
#############################################################################

#
# Display the contents of a Member Dictionary
#
def display_member_dictionary(group_name):
    dict = read_dict(group_name + '.mdic')
    for item in dict.items():
        print('Member: %s'%item[0])
        print('  Name:: %s'%item[1][0])
        print('  Location: %s'%item[1][1])

#
# Process a single member's page
#
def do_member(mem_link, member_dictionary):
    # We'll use the (string) member number as the key to the dictionary
    member_number = mem_link.split('/')[-2]
    debug('Member: %s,'%member_number, 10, nl=False),

    # Get the member's page
    mem_page = get_page(mem_link)

    # Get their first name
    mem_page, first_name = \
        locate_and_extract(mem_page, '<head>', '<title>', ' ')
    debug('name: %s,'%first_name, 10, nl=False),

    SCHEMA = 'http://schema.org/'
    mem_page, schema = \
        locate_and_extract(mem_page, 'Location:', SCHEMA, '">')
    debug('schema: %s,'%(SCHEMA + schema), 10, nl=False),

    PREFIX = 'http://www.meetup.com/'
    # Get their location
    mem_page, location = \
        locate_and_extract(mem_page, 'href', PREFIX, '">')
    if location[:6] != 'cities':
        print('ERROR: Location for was not ' + PREFIX + 'cities')
        exit(0)

    location = location[6:]
    member_dictionary[member_number] = [first_name, location]
    debug('location: %s'%location, 10)

    sys.stdout.flush()
    if schema != 'PostalAddress':
        print('ERROR: Schema was not "PostalAddress"')
        exit(0)

#
# Create a Member Dictionary
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
    n_members_read = 0
    while True:
        # Locate the next member link on the current members page
        page, mem_link = locate_and_extract(page, 'mem-photo', 'href="', '"')

        # If there isn't one, try to fetch the next members page
        if mem_link == '':
            debug('Fetching the next page ...')
            nplink = next_link%n_members_read
            page = get_page(nplink)
            debug('  Link is: %s'%nplink)
            page, mem_link \
                = locate_and_extract(page, 'mem-photo', 'href="', '"')
            debug(mem_link)

        # It there's no next page then we're done
        if mem_link == '': break

        # Download and process the page for this member
        do_member(mem_link, member_dictionary)
        n_members_read += 1
        if n_members_read == n_members_total: break

    debug('Expected to find %s members'%n_members_total, 10)
    debug('Read pages for   %s members' %n_members_read, 10)
    write_dict(dict_name, member_dictionary)

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

#
# Display the contents of a Location Dictionary
#
def display_location_dictionary(group_name):
    dict = read_dict(group_name + '.ldic')
    for item in dict.items():
       print('Location: %s'%item[0])
       print('  %s'%item[1].show())

#
# Sort a single member into the proper location
#
def sort_member(member_info, location_dictionary):
    name = member_info[0]
    location = member_info[1]
    debug('sort_member:')
    debug('  name:      %s'%name)
    debug('  location:  %s'%location)

    if location_dictionary.get(location) == None:
        debug('Adding %s to the location dictionary'%location)
        location_dictionary[location] = location_dict_item()
    item = location_dictionary[location]
    item.members += [ name, ]
    debug('  Added member "%s" to location "%s"'%(name, location))

# geo_lookup(), get_location_info(), and fill_in_geo_locations are all
#   used to put the actual geograhic coordinates (longitude and latidude)
#   into the Location Dictionary.

def geo_lookup(lookup_string):
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
        except:
            e = sys.exc_info()[0]
            print(location)
            print('Looking up: %s'%lookup_string);
            print('UNEXPECTED Geocoder error: %s'%e)
            return(None)

n_attempted = 0
good_zips = 0
bad_zips = 0
good_cities = 0
bad_cities = 0
n_found = 0
geolocator = Nominatim()
zcdb = ZipCodeDatabase()

def get_location_info(location, item):
    global n_attempted, n_found, good_zips, bad_zips, good_cities, bad_cities
    n_attempted += 1

    # Split the location string up, eliminating the nulls on both ends
    foo = location.split('/')[1:-1]
    item.country = foo[0]
    if item.country == 'us':
        item.zip = foo[1]
        try: place = zcdb[item.zip]
        except:
            debug(location, 10)
            debug('Can\'t find zip code %s'%item.zip, 10)
            bad_zips += 1
            return
        if place == None or place == '':
            debug(location, 10)
            debug('Can\'t find zip code %s'%item.zip, 10)
            bad_zips += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        n_found += 1
        good_zips += 1

    elif item.country == 'gb' or item.country == 'ca':
        if len(foo) != 3:
            debug(location, 10)
            debug('Country is %s but we don\'t have a region code'%item.country, 10)
            bad_cities += 1
            return
        item.city = foo[2]
        lookup_string = item.city + ', ' + item.country
        place = geo_lookup(lookup_string)

        if place == None or place == '':
            debug(location, 10)
            debug('Can\'t find coords of country = "%s", city = "%s"'\
                %(item.country, item.city), 10)
            bad_cities += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        good_cities += 1
        n_found += 1

    else:
        # So far, it *appears* the countries other than GB, CA and US
        # follow the format /COUNTRY/CITY
        if len(foo) != 2:
            debug('Country is %s. Can\'t parse: %s'
                %(item.country, location), 10)
            bad_cities += 1
            return
        item.city = foo[1]
        lookup_string = item.city + ', ' + item.country
        place = geo_lookup(lookup_string)

        if place == None or place == '':
            debug('Can\'t find coords of country = "%s", city = "%s"'\
                %(item.country, item.city), 10)
            bad_cities += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        good_cities += 1
        n_found += 1

def fill_in_geo_locations(location_dictionary):

    for record in location_dictionary.items():
        location = record[0]
        item = record[1]
        get_location_info(location, item)
        location_dictionary[location] = item

    print('We attempted to process %s locations'%n_attempted)
    print('We were able to find    %s locations'%n_found)
    print('Good zips: %s, bad zips: %s'%(good_zips, bad_zips))
    print('Good cities: %s, bad cities: %s'%(good_cities, bad_cities))

#
# Create a Location Dictionary
#
# Read a member dictionary (which has every member listed separately with
# their corresponding "raw" locations) and create a location dictionary
# which has unique entries for each location, and a list of members in that
# location.
#
def create_location_dictionary(group_name):
    dict_name = group_name + '.ldic'
    print('Creating: %s' %dict_name)
    member_dictionary = read_dict(group_name + '.mdic')    
    location_dictionary = {}
    for item in member_dictionary.items():
        sort_member(item[1], location_dictionary)

    # Now fill in the actual geographic coordinates
    fill_in_geo_locations(location_dictionary)

    # And write the dictionary out to disk
    write_dict(dict_name, location_dictionary)

#############################################################################
#                                                                           #
#                        KML File Code                                      #
#                                                                           #
#############################################################################
#
# The functions below are involved in reading the location dictionary, 
# sorting it in the specified way, and then ouputing a Keyhole Markup
# Language (.kml) file, which can be uploaded to (for example) google maps.

# This is a dictionary where the key is the number of members and
# the values is the number of locations which have that many members.

number_table = {}

# This is a dictionary where the key is the number of members and
# the values is the color for locations with that many members

color_table = {}

# These are the extremes of the geographic coordinates encountered.
# This information is used to center the map and determine the zoom
#  factor (for leaflets only.)

high_lat = -91; high_lon = -181; low_lat = 91; low_lon = 181

# Specific icons that can be used. Select one below

DEFAULT='http://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png'
STAR   ='http://www.gstatic.com/mapspro/images/stock/960-wht-star-blank.png'
HOUSE  = 'http://www.gstatic.com/mapspro/images/stock/1197-fac-headquarters.png'

#
# Some parameters are currently selected by editing the variables below.
#

# Which icon to use. See defs above

ICON = STAR

# Intensity for locations with most members (0 is the most intensity)

high_color = 0

# Intensity for locations with least members

low_color = 200

#
# These functions assist with creating a leaflet map
#

def start_leaflet(group_name):
    global leaflet_page, high_lat, low_lat, high_lon, low_lon
    title = 'Leaflet Meetup Map'
    heading = group_name
    leaflet_page = open(group_name + '.html', 'w')
    leaflet_start = open('leaflet-start', 'r')
    lstart = leaflet_start.read()
    leaflet_page.write(lstart%(title, heading, low_lat, low_lon, high_lat, high_lon))
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
# These functions are for writing the .kml file
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

def kmlline(text):
    global kml
    kml.write(text + '\n')

def kmlicon(name, value, type=ICON):
    kmlline("        <Style id='icon-%s'>"%name)
    kmlline("            <IconStyle>")
    kmlline("                <color>ff%02x%02xff</color>"%(value,value))
    kmlline("                <scale>1.1</scale>")
    kmlline("                <Icon>")
    kmlline("                    <href>%s</href>"%type)
    kmlline("                </Icon>")
    kmlline("                <hotSpot x='16' y='31' xunits='pixels' yunits='insetPixels'>")
    kmlline("                </hotSpot>")
    kmlline("            </IconStyle>")
    kmlline("            <LabelStyle>")
    kmlline("                <scale>0.0</scale>")
    kmlline("            </LabelStyle>")
    kmlline("        </Style>")

def end_kml():
    global kml, number_table
    kmlline("        </Folder>")
    kmlline("")

    # Make an icon for each color needed
    print('end_kml():')
    for n_members in sorted(number_table, reverse=True):
        color = color_table[n_members]
        icon_name = str(n_members)
        print('icon_name: %s, color: %s'%(icon_name, color))
        kmlicon(icon_name, color)
        kmlline("")

    kmlline("    </Document>")
    kmlline("</kml>")

def get_stats(location_dictionary):
    global number_table, color_table, high_lat, low_lat, high_lon, low_lon
    for item in sorted(location_dictionary.items(), key=mykey, reverse=True):

        # If we've got good coordinates, then save the highs and lows
        try:
            lon = float(item[1].longitude)
            lat = float(item[1].latitude)
            if lon > high_lon: high_lon = lon
            if lat > high_lat: high_lat = lat
            if lon < low_lon: low_lon = lon
            if lat < low_lat: low_lat = lat
        except ValueError: pass

        location = item[0]
        people = item[1].members
        n_members = len(people)
        try:
            n_locations = number_table[n_members]
            number_table[n_members] = n_locations + 1
        except:
            number_table[n_members] = 1
            color_table[n_members] = 0
    print('get_stats:')
    print('The number_table has %s entries'%len(number_table))
    division = (low_color - high_color) / (len(number_table) - 1)
    current_color = high_color
    print('A color division is: %s'%division)
    for n_members in sorted(number_table, reverse=True):
        n_locations = number_table[n_members]
        color_table[n_members] = current_color
        current_color += division

        #debug
        msg = '  There are %s locations with %s members'%(n_locations, n_members)
        msg += ', color: %s'%color_table[n_members]
        print(msg)
    print('Latitude: (%s, %s), Longitude: (%s, %s)' %(low_lat, high_lat, low_lon, high_lon))

def map_location(args, location, item):
    if args.leaflet: map_location_leaflet(location, item)
    else: map_location_kml(location, item)

def map_location_leaflet(location, item):
    lon = item.longitude
    lat = item.latitude
    debug('map_location_leaflet(): lat=%s, lon=%s' %(lat, lon))

    # Skip this item if we never found the coordinates
    if lon == '' or lat == '':
        debug('Skipping: %s (%s members)'%(location, len(item.members)))
        return

    if item.zip != '':
        loc = item.zip
    else: 
        #print('City="%s", Country="%s"'%(item.city, item.country))
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

def map_location_kml(location, item):
    lon = item.longitude
    lat = item.latitude

    # Skip this item if we never found the coordinates
    if lon == '' or lat == '':
        print('Skipping: %s (%s members)'%(location, len(item.members)))
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

def merge_locations(location_dictionary, target, source, coords):
    # Target and source are raw location (indices in the location_dictionary).
    # Merge all the members from source into target
    debug('  %s and %s have the same geographic coordinates: %s'
        %(target, source, coords))
    debug('    Merging members from %s into %s and deleting %s'
        %(source, target, source))
    target_item = location_dictionary[target]
    source_item = location_dictionary[source]
    target_item.members += source_item.members
    del location_dictionary[source]

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
        #if we get a hit, merge the two in the original location dict.
        if key in geo_dict:
            merge_locations(location_dictionary, geo_dict[key], item[0], key)
        # Otherwise add it to the temp dict
        else:
            geo_dict[key] = item[0]

def fix_url_quotes(location_dictionary):
    for item in location_dictionary.items():
        city = item[1].city
        if '%' in city:
            new_city = urllib2.unquote(city)
            debug('  Fixing: %s --> %s'%(city, new_city))
            item[1].city = new_city
            location_dictionary[item[0]] = item[1]

def sort_common(args, group_name):
    location_dictionary = read_dict(group_name + '.ldic')

    print('Eliminating duplicate locations:')
    merge_duplicate_locations(location_dictionary)
    print('Fixing city names:')
    fix_url_quotes(location_dictionary)

    get_stats(location_dictionary)
    if args.leaflet: start_leaflet(group_name)
    else: start_kml(group_name)
    return(location_dictionary)

def sort_by_location(args, group_name):
    location_dictionary = sort_common(args, group_name)
    for item in sorted(location_dictionary.items()):
        map_location(args, item[0], item[1])
    if args.leaflet: end_leaflet()
    else: end_kml()

def mykey(x):
    # x[0] is the key (the "raw" location)
    # x[1] is a location_dict_item
    return(len(x[1].members))

def sort_by_number(args, group_name):
    location_dictionary = sort_common(args, group_name)
    for item in sorted(location_dictionary.items(), key=mykey, reverse=True):
         map_location(args, item[0], item[1])
    if args.leaflet: end_leaflet()
    else: end_kml()

def make_map(args, group_name):
    if args.byloc: sort_by_location(args, group_name)
    else: sort_by_number(args, group_name)

#############################################################################
#                                                                           #
#                        Mainline Code                                      #
#                                                                           #
#############################################################################

def main(args):

    group_name = args.group_name

    # Potentially set the debug level
    debug_level = args.debug_level

    # Now see if we're instructed to dump a dictionary. If so, 
    # that's the only thing we'll do. Other flags will be ignored.

    if args.disp_members:
        display_member_dictionary(group_name)    
        exit(0)

    if args.disp_locations:
        display_location_dictionary(group_name)    
        exit(0)

    # See if we're just supposed to make a location dictionary
    if args.make_ldic:
        if not os.path.isfile(group_name + '.mdic'):
            print('Location dict requested, but no member dict present')
            print('Quitting.')
            exit(0)
        create_location_dictionary(group_name)
        exit(0)

    # Then see if a leaflet page was requested. We won't do this unless
    # there is already a location dictionary available.

    if args.leaflet:
        if not os.path.isfile(group_name + '.ldic'):
            print('Leaflet page requested, but have no location dictionary.')
            print('Quitting.')
            exit(0)
        print('Making leaflet page ...')
        make_map(args, group_name)
        exit(0)

    # Processing from this point on will depend on which dictionary files
    # already exist. If we have a Location Dictionary (.ldic file) then
    # we will proceed to generate a map (.kml file). If we don't have the
    # locations, we will check to see if we have a Member Dictionary, from
    # which the locations can be generated. If we don't have that, then
    # we will find the Members by scraping the meetup group -- but ONLY if
    # the user has entered the download flag. (This is to avoid needless
    # downloading of information from meetup, by accident.)

    # If there's already a map file, make sure the user wanted to change it.
    if os.path.isfile(group_name + '.kml'):
        ans = ''
        while ans not in ['Y', 'N', 'y', 'n']:
            ans = raw_input('The map file: %s already exists, overwrite? [y/n] ')
        if ans == 'n':
            print('Quitting.')
            exit(0)

    # If there's no location dict, make one before creating the map file
    if not os.path.isfile(group_name + '.ldic'):
        # If there's no Member dict, download - but only if the flag is true
        if not os.path.isfile(group_name + '.mdic'):
            if not args.download:
                print('We need a Member Dictionary but none exists')
                print('include the -D flag to download new member info')
                print('Quitting')
                exit(0)
            create_member_dictionary(group_name)
        create_location_dictionary(group_name)
   
    # Now we can create the actual map, which for the time being at least
    # is a Keyhole Markup Language (.kml) file.

    print('Mapping "%s"' %group_name),
    if args.bynum: print('by number of members')
    elif args.byloc: print('by location')
    else: print('by number of members')
    make_map(args, group_name)

main(parser.parse_args())

