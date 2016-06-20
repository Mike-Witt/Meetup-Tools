#!/usr/bin/env python

#
# Add geographic coordinates to the location dictionary
#

import sys
import pickle
from geopy.geocoders import Nominatim
from pyzipcode import ZipCodeDatabase
from mtlib import location_dict_item

geolocator = Nominatim()
zcdb = ZipCodeDatabase()
n_attempted = 0
n_found = 0
good_zips = 0
bad_zips = 0
good_cities = 0
bad_cities = 0

def get_location_info(location, item):
    global n_attempted, n_found, good_zips, bad_zips, good_cities, bad_cities
    #debug
    #print('Location: %s'%location)
    #print('item: %s'%item.show())

    n_attempted += 1

    # Split the location string up, eliminating the nulls on both ends
    foo = location.split('/')[1:-1]
    item.country = foo[0]
    if item.country == 'us':
        item.zip = foo[1]
        try: place = zcdb[item.zip]
        except: 
            print('Can\'t find zip code %s'%item.zip)
            bad_zips += 1
            return
        if place == None or place == '':
            print('Can\'t find zip code %s'%item.zip)
            bad_zips += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        n_found += 1
        good_zips += 1

    elif item.country == 'gb' or item.country == 'ca':
        if len(foo) != 3:
            print('Country is %s but we don\'t have a region code'%item.country)
            bad_cities += 1
            return
        item.city = foo[2] 
        lookup_string = item.city + ', ' + item.country
        try:
            place = geolocator.geocode(lookup_string)
        except:
            e = sys.exc_info()[0]
            print('Looking up: %s'%lookup_string);
            print('Geocoder error: %s'%e)
            place = None
        if place == None or place == '':
            print('Can\'t find coords of country = "%s", city = "%s"'\
                %(item.country, item.city))
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
            print('Country is %s. Can\'t parse: %s'
                %(item.country, location))
            bad_cities += 1
            return
        item.city = foo[1] 
        lookup_string = item.city + ', ' + item.country
        try:
            place = geolocator.geocode(lookup_string)
        except:
            e = sys.exc_info()[0]
            print('Looking up: %s'%lookup_string);
            print('Geocoder error: %s'%e)
            place = None
        if place == None or place == '':
            print('Can\'t find coords of country = "%s", city = "%s"'\
                %(item.country, item.city))
            bad_cities += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        good_cities += 1
        n_found += 1

def main(argv):
    if len(argv) < 2:
        print('Usage: %s group-name'%argv[0])
        exit(0)

    group_name = argv[1]
    file = open(group_name + '.ldic', 'r')
    location_dictionary = pickle.load(file)
    file.close()

    for record in location_dictionary.items():
        location = record[0]
        item = record[1]
        get_location_info(location, item)
        location_dictionary[location] = item

    file = open(group_name + '.ldic', 'w')
    pickle.dump(location_dictionary, file)
    file.close()

    print('We attempted to process %s locations'%n_attempted)
    print('We were able to find    %s locations'%n_found)
    print('Good zips: %s, bad zips: %s'%(good_zips, bad_zips))
    print('Good cities: %s, bad cities: %s'%(good_cities, bad_cities))

main(sys.argv)
