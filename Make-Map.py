#!/usr/bin/env python

#
# Build a KML file based on a location dictionary of members. 
#

import pickle
import sys

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

def out(msg): sys.stdout.write(msg)

if len(sys.argv) < 2:
    print('Usage: %s flags GROUP_NAME'%sys.argv[0])
    print(' %s -help for more information'%sys.argv[0])
    exit()

if sys.argv[1] == '-help':
    print('%s -byloc GROUP_NAME'%sys.argv[0])
    print('  Sort by location')
    print('%s -bynum GROUP_NAME'%sys.argv[0])
    print('  Sort by number of members')
    print('%s -stats GROUP_NAME'%sys.argv[0])
    print('  Just print statistics')
    exit()

if len(sys.argv) >= 3: opt = sys.argv[1]
else:
    print('Need to specify group name')
    exit()

group_name = sys.argv[2]
dict_name = group_name + '.dic'
kml_name = group_name + '.kml'
kml = 0

# This is a dictionary where the key is the number of members and
# the values is the number of locations which have that many members.
number_table = {}
# This is a dictionary where the key is the number of members and
# the values is the color for locations with that many members
color_table = {}

#
# Load the group's dictionary
#

f = open(dict_name, 'r')
member_dictionary = pickle.load(f)
f.close()

#
# These functions are for writing the .kml file
#

def start_kml():
    global kml, group_name
    kml = open(kml_name, 'w')
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

def map_location(item):
    global kml

    location = item[1][0]
    people = item[1][1]
    coords = location[4] 
    N = len(people)
    data = ''
    for n in range(N):
        if n != 0: data += "<br>"
        data += people[n]

    icon_name = str(N)
    kmlline("        <Placemark>")
    country = location[0].upper() # Make country code upper case
    town = location[1]
    zipcode = location[2]
    if zipcode != '': LOC = zipcode + ', ' + country
    else: LOC = town + ', ' + country
    kmlline("            <name>Location: %s (%s members)</name>"%(LOC, N))
    kmlline("            <description><![CDATA[%s]]></description>"%data)
    kmlline("            <styleUrl>#icon-%s</styleUrl>"%icon_name)
    kmlline("            <Point>")
    kmlline("                %s"%coords)
    kmlline("            </Point>")
    kmlline("        </Placemark>")
    kmlline("")

def sort_by_location():
    global member_dictionary
    for item in sorted(member_dictionary.items()):
        map_location(item)

def mykey(x):
    # We want to key on the number of people. 
    # key = x[0]
    # location, people = x[1]
    # people = x[1][1]
    return(len(x[1][1]))

def sort_by_number():
    global member_dictionary
    for item in sorted(member_dictionary.items(), key=mykey, reverse=True):
        map_location(item)

# Get statistics about the group and members
# Right now we just build a table of the "grouping" of members in locations

def get_stats():
    global member_dictionary, number_table, color_table
    for item in sorted(member_dictionary.items(), key=mykey, reverse=True):
        location = item[0]
        people = item[1][1]
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

if opt == '-byloc':
    start_kml()
    get_stats()
    sort_by_location()
    end_kml()
elif opt == '-bynum':
    start_kml()
    get_stats()
    sort_by_number()
    end_kml()
elif opt == '-stats':
    get_stats()
else:
    print('Option %s not recognized'%opt)

