#!/usr/bin/env python

#
# Build a KML file based on a zipcode dictionary of members. 
#
# I'm saving all the "print" code and putting in the PRINT flag so that
# I can ultimately just use this program and get rid of SortDictFile.py

import pickle
import sys
from geopy.geocoders import Nominatim

# Specific icons that can be used. Select one below

DEFAULT='http://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png'
STAR   ='http://www.gstatic.com/mapspro/images/stock/960-wht-star-blank.png'
HOUSE  = 'http://www.gstatic.com/mapspro/images/stock/1197-fac-headquarters.png'

#
# Parameters currently selected by editing the file
#

# PRINT = True means don't product the file, just print debug stuff
PRINT = False 

# Which icon to use. See defs above
ICON = STAR

# Intensity for zip codes with most members (0 is the most intensity)
high_color = 0
# Intensity for zip codes with least members
low_color = 200

def out(msg): sys.stdout.write(msg)

if len(sys.argv) < 2:
    print('Usage: %s flags GROUP_NAME'%sys.argv[0])
    print(' %s -help for more information'%sys.argv[0])
    exit()

if sys.argv[1] == '-help':
    print('%s -byzip GROUP_NAME'%sys.argv[0])
    print('  Sort by zip code')
    print('%s -bynum GROUP_NAME'%sys.argv[0])
    print('  Sort by number of members')
    print('%s -stats GROUP_NAME'%sys.argv[0])
    print('  Just print statistics')
    print('%s -sum GROUP_NAME'%sys.argv[0])
    print('  Summarize by popular zip codes')
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
# the values is the number of zipcodes which have that many members.
number_table = {}
# This is a dictionary where the key is the number of members and
# the values is the color for zipcodes with that many members
color_table = {}

#
# Load the group's dictionary
#

f = open(dict_name, 'r')
zip_dict = pickle.load(f)
f.close()

#
# Load the zip code / coordinate database
#

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

def map_zip(zipcode, people):
    global kml, zip_dict, zcdb

    geolocator = Nominatim()
    try:
        location = geolocator.geocode(zipcode)
    except:
        print('Don\'t know zip code: "%s"'%zipcode)
        return # Just skip members with unknown zip code
    if location == None:
        print('Don\'t know zip code: "%s"'%zipcode)
        return

    lat = location.latitude
    lon = location.longitude
    coords = '<coordinates>%s,%s,0.0</coordinates>'%(lon, lat)

    people = zip_dict[zipcode]
    N = len(people)
    data = ''
    for n in range(N):
        if n != 0: data += "<br>"
        data += people[n]

    icon_name = str(N)
    kmlline("        <Placemark>")
    kmlline("            <name>Zip Code: %s (%s members)</name>"%(zipcode, N))
    kmlline("            <description><![CDATA[%s]]></description>"%data)
    kmlline("            <styleUrl>#icon-%s</styleUrl>"%icon_name)
    kmlline("            <Point>")
    kmlline("                %s"%coords)
    kmlline("            </Point>")
    kmlline("        </Placemark>")
    kmlline("")

def print_zip(z, people):
    out('%s: '%z)
    first = True
    for person in people:
        if not first: out(', ')
        out(person)
        first = False
    print

def sort_by_zip():
    global zip_dict
    for z in sorted(zip_dict):
        people = zip_dict[z]
        if PRINT: print_zip(z, people)
        else: map_zip(z, people)

def mykey(x):
    #print('mykey: x[0]=%s, x[1]=%s'%( (x[0]), (x[1]) ))
    #print('len(x[1]=%s' %len(x[1]))
    return(len(x[1]))

def sort_by_number():
    global zip_dict
    for item in sorted(zip_dict.items(), key=mykey, reverse=True):
        zip = item[0]
        people = item[1]
        if PRINT: print_zip(zip, people)
        else: map_zip(zip, people)

# Summarize popular zip codes only. This just prints them with population.
def summarize():
    global zip_dict
    with_one = 0
    for item in sorted(zip_dict.items(), key=mykey, reverse=True):
        zip = item[0]

        ### CHECK FOR VALID ZIPCODE - SHOULD DO THIS WHEN BUILDING FILE! ###
        try: 
            foo = int(zip)
        except:
            continue
        if len(zip) != 5:
            continue
        people = item[1]
        n = len(people)
        if n > 1: print('%s: has %s members'%(zip, n))
        else: with_one += 1
    print('In addition, there are %s zipcodes with only one member'%with_one)

# Get statistics about the group and members
# Right now we just build a table of the "grouping" of members in zipcodes

def get_stats():
    global zip_dict, number_table, color_table
    #print('get_stats:')
    for item in sorted(zip_dict.items(), key=mykey, reverse=True):
        zip = item[0]
        people = item[1]
        n_members = len(people)
        #print('  Zipcode: %s, n_people: %s'%(zip, n_members))
        try:
            n_zipcodes = number_table[n_members]
            number_table[n_members] = n_zipcodes + 1
        except:
            number_table[n_members] = 1
            color_table[n_members] = 0
    print('get_stats:')
    print('The number_table has %s entries'%len(number_table))
    division = (low_color - high_color) / (len(number_table) - 1)
    current_color = high_color
    print('A color division is: %s'%division)
    for n_members in sorted(number_table, reverse=True):
        n_zipcodes = number_table[n_members]
        color_table[n_members] = current_color
        current_color += division

        #debug
        msg = '  There are %s zip codes with %s members'%(n_zipcodes, n_members)
        msg += ', color: %s'%color_table[n_members]
        print(msg)

if opt == '-byzip':
    if PRINT == False: start_kml()
    get_stats()
    sort_by_zip()
    if PRINT == False: end_kml()
elif opt == '-bynum':
    if PRINT == False: start_kml()
    get_stats()
    sort_by_number()
    if PRINT == False: end_kml()
elif opt == '-sum':
    summarize()
elif opt == '-stats':
    get_stats()
else:
    print('Option %s not recognized'%opt)

