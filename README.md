# Meetup (mapping) tools

First of all: 
<font color='red'><b>THIS CODE IS NOT READY FOR USE YET!</b></font>

It has a number of bugs, and places where you need to tweak things by hand to get it to work right.

Also, see "limitations" below.

If you decide to try it, despite all this, please let me know what happens!

Email me at: msg2mw@gmail.com

### Before Using:
```
pip install pyzipcode
pip install mechanize
pip install geopy
./make-map.py --help
```

### To make a .kml file for the group called my-group-name:
```
./make-map --download my-group-name
./make-map --geo my-group-name
./make-map --kml my-group-name
```
Then upload my-group-name.kml to Google Maps

### To examine the dictionaries:
```
./make-map --disp_members my-group-name # shows the member dictionary
./make-map --disp_locs my-group-name # shows the location dictionary
```

### Limitations:
* Only works with Python 2.7
* May only work on linux(?)
* Meetup can change the format of their pages at any time.

### Feedback or questions:
* msg2mw@gmail.com
