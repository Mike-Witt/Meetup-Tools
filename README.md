# Meetup-Tools

First of all: <b>THIS CODE IS NOT READY FOR USE YET!</b>

But if you want to help me test it out:

### Before Using:
```
pip install pyzipcode
pip install mechanize
pip install geopy
```

### To a make .kml file for the group called my-group-name:
```
./make-map -D my-group-name
```
Then upload my-group-name.kml to Google Maps

### Other:
```
./make-map my-group-name # will build everything if the member dictionary exists
./make-map -dm my-group-name # shows the member dictionary
./make-map -dl my-group-name # shows the location dictionary
```
