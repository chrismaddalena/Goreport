# Go Report
##### A GoPhish reporting tool

This script accepts your GoPhish campaign ID and IP:port as its only parameter and then performs user-agent parsing, geo IP lookups, and table creation for you.

## GoPhish's API
This script requires the API key for your GoPhish application. Get this key by clicking the Settings tab. The API key will be found on the first page.

## Script Setup

You need to do a few things to get started:

* Run pip install -r requirements.txt
* Download a fresh and up-to-date copy of the free MaxMind Geo IP database
* Get your campaign ID number by clicking your campaign results and referencing the URL (it's the number at the end)

## Additional Information

GoPhish performs it's own geo IP lookups and returns latitude and longitude. This works alright, but geo IP is often unreliable as IPs change hands or are reallocated.

GoPhish uses free lookup tools that are generally accurate or close, but sometimes get things very wrong. I can't give specific examples because they are all IPs tied to various clients, but there is the general situation you may run into. GoPhish might identify an IP as being related to Kansas. With this IP, GoPhish's location lookup will be verified by a number of geo IP tools. However, it is quite wrong. This IP now belongs to an organization in Massachusetts.

This script utilizes two tools to get a more reliable location: Google and MaxMind GeoIP. First, we use MaxMind GeoIP to match the IP address to coordinates. This requires a copy of MaxMind's free "geolite" database:

http://dev.maxmind.com/geoip/geoip2/geolite2/

Then the script uses the Google Maps API to look-up the coordinates and return detailed location data. The URL looks like this:

http://maps.googleapis.com/maps/api/geocode/json?latlng=38,-97&sensor=false

I have found this to be more reliable, but it's always best to verify the locations, especially if location might matter to a client or your own analysis.
