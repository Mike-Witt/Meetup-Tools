# Meetup-Tools

(TBD)

THIS CODE IS NOT READY FOR USE YET!


<h2>Summary</h2>

Before Using:
```
pip install pyzipcode
pip install mechanize
pip install geopy
```

To a make .kml file for the group called My-Group-Name:
```
./pyzipcode-Make-Dictionary.py My-Group-Name
./pyzipcode-Make-Map.py -bynum My-Group-Name
```
Then upload My-Group-Name.kml to Google Maps

For groups that have members ONLY in US zip codes, this is faster:
```
./Make-Dictionary.py My-Group-Name
./Make-Map.py -bynum My-Group-Name
```
## Things to do before this is at all ready to use:
* Do the geo lookups in just one place. Probably make-dic
* Geo lookups when the location first goes in the dict
