#!/usr/bin/env python

# Read a location dictionary, sort it in the specified way, and output
# a .kml file that can be uploaded to (for example google maps).

import pickle
import sys
import urllib2
from mtlib import location_dict_item

# This is a dictionary where the key is the number of members and
# the values is the number of locations which have that many members.
number_table = {}
# This is a dictionary where the key is the number of members and
# the values is the color for locations with that many members
color_table = {}

# Specific icons that can be used. Select one below

DEFAULT='http://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png'
STAR   ='http://www.gstatic.com/mapspro/images/stock/960-wht-star-blank.png'
HOUSE  = 'http://www.gstatic.com/mapspro/images/stock/1197-fac-headquarters.png'

#
# Parameters currently selected by editing the file
#

# Which icon to use. See defs above
ICON = STAR

# Intensity for locations with most members (0 is the most intensity)
high_color = 0
# Intensity for locations with least members
low_color = 200

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

def usage():
    print('Usage %s -bynum group-name'%argv[0])
    print('Usage %s -bynum group-name'%argv[0])
    exit(0)

def get_stats(location_dictionary):
    global location_dionary, number_table, color_table
    for item in sorted(location_dictionary.items(), key=mykey, reverse=True):
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

def map_location(location, item):
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

def get_dict(group_name):
    file = open(group_name + '.ldic', 'r')
    location_dictionary = pickle.load(file)
    file.close()
    return(location_dictionary)

def merge_locations(location_dictionary, target, source, coords):
    # Target and source are raw location (indices in the location_dictionary).
    # Merge all the members from source into target
    print('  %s and %s have the same geographic coordinates: %s'
        %(target, source, coords))
    print('    Merging members from %s into %s and deleting %s'
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
            print('  Fixing: %s --> %s'%(city, new_city))
            item[1].city = new_city
            location_dictionary[item[0]] = item[1]

def sort_common(group_name):
    location_dictionary = get_dict(group_name)

    print('Eliminating duplicate locations:')
    merge_duplicate_locations(location_dictionary)
    print('Fixing city names:')
    fix_url_quotes(location_dictionary)

    get_stats(location_dictionary)
    start_kml(group_name)
    return(location_dictionary)

def sort_by_location(group_name):
    location_dictionary = sort_common(group_name)
    for item in sorted(location_dictionary.items()):
        map_location(item[0], item[1])
    end_kml()

def mykey(x):
    # x[0] is the key (the "raw" location)
    # x[1] is a location_dict_item
    return(len(x[1].members))

def sort_by_number(group_name):
    location_dictionary = sort_common(group_name)
    for item in sorted(location_dictionary.items(), key=mykey, reverse=True):
         map_location(item[0], item[1])
    end_kml()

def main(argv):
    # If the user just enters the groupname, we'll assume -bynum
    if len(argv) == 2:
        if argv[1] == 'help': usage()
        if argv[1] == '-help': usage()
        if argv[1] == '--help': usage() 
        sort_by_number(argv[1])
    elif len(argv) != 3: usage()
    elif argv[1] == '-bynum': sort_by_number(argv[2])
    elif argv[1] == '-byloc': sort_by_location(argv[2])
    else: usage

main(sys.argv)
