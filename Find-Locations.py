#!/usr/bin/env python

#
# Add geographic coordinates to the location dictionary
#

import sys
import pickle
from time import sleep
import geopy
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

def dbg(msg):
    print(msg)
    sys.stdout.flush()

def geo_lookup(lookup_string):
    sleep_time = 5
    # We'll potentially keep trying until we get either the answer or
    # an error other than timeout, etc.
    while(True):
        try:
            place = geolocator.geocode(lookup_string)
            return(place)
        except geopy.exc.GeocoderTimedOut:
            dbg('GeocoderTimedOut, sleep %s seconds and retry ...'%sleep_time)
            sleep(sleep_time)
            continue
        except geopy.exc.GeocoderUnavailable:
            dbg('GeocoderUnavailable, sleep %s seconds and retry ...'%sleep_time)
            sleep(sleep_time)
            continue
        except:
            e = sys.exc_info()[0]
            dbg(location)
            dbg('Looking up: %s'%lookup_string);
            dbg('UNEXPECTED Geocoder error: %s'%e)
            return(None)

def get_location_info(location, item):
    global n_attempted, n_found, good_zips, bad_zips, good_cities, bad_cities
    #debug
    #dbg('Location: %s'%location)
    #dbg('item: %s'%item.show())

    n_attempted += 1

    # Split the location string up, eliminating the nulls on both ends
    foo = location.split('/')[1:-1]
    item.country = foo[0]
    if item.country == 'us':
        item.zip = foo[1]
        try: place = zcdb[item.zip]
        except: 
            dbg(location)
            dbg('Can\'t find zip code %s'%item.zip)
            bad_zips += 1
            return
        if place == None or place == '':
            dbg(location)
            dbg('Can\'t find zip code %s'%item.zip)
            bad_zips += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        n_found += 1
        good_zips += 1

    elif item.country == 'gb' or item.country == 'ca':
        if len(foo) != 3:
            dbg(location)
            dbg('Country is %s but we don\'t have a region code'%item.country)
            bad_cities += 1
            return
        item.city = foo[2] 
        lookup_string = item.city + ', ' + item.country
        place = geo_lookup(lookup_string)

        if place == None or place == '':
            dbg(location)
            dbg('Can\'t find coords of country = "%s", city = "%s"'\
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
            dbg('Country is %s. Can\'t parse: %s'
                %(item.country, location))
            bad_cities += 1
            return
        item.city = foo[1] 
        lookup_string = item.city + ', ' + item.country
        place = geo_lookup(lookup_string)

        if place == None or place == '':
            dbg('Can\'t find coords of country = "%s", city = "%s"'\
                %(item.country, item.city))
            bad_cities += 1
            return
        item.latitude = place.latitude
        item.longitude = place.longitude
        good_cities += 1
        n_found += 1

def main(argv):
    if len(argv) < 2:
        dbg('Usage: %s group-name'%argv[0])
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

    dbg('We attempted to process %s locations'%n_attempted)
    dbg('We were able to find    %s locations'%n_found)
    dbg('Good zips: %s, bad zips: %s'%(good_zips, bad_zips))
    dbg('Good cities: %s, bad cities: %s'%(good_cities, bad_cities))

main(sys.argv)
