# Go Report
##### A GoPhish reporting tool

This script accepts your GoPhish campaign ID as a parameter and then collects your campaign results and performs user-agent parsing and geo IP lookups. It also generates lists of IP addresses, operating systems, browser types and versions, and locations with counts for the number of times each one was seen throughout the campaign.

## GoReport Requirements
This script requires GoPhish, of course, and the API key for your GoPhish application. Get this key by clicking the Settings tab. The API key will be found on the first page.

These Python libraries are required as well:
* gophish
* requests
* maxminddb-geolite2
* configparser
* python-docx

## GoReport Setup
You need to do a few things to get started:

* Run `pip install -r requirements.txt`.
* Download a fresh and up-to-date copy of the free MaxMind Geo IP database (see below).
* Edit/create a gophish.ini configuration file that looks like the one below.
  * Note: The full host URL is required, so provide http://IP:PORT or https://IP:PORT.
* Get your campaign ID number by clicking your campaign results and referencing the URL (it's the number at the end).
* Drop a "template.docx" template file into the GoReport directory if you want to create Word document reports (more information below in Selecting Report Output).

## Basic Usage


### Sample Usage

Assuming GoPhish was on another server and you are using SSH port forwarding with port 8080:

<b>gophish.ini</b>

>[GoPhish]

>gp_host: http://127.0.0.1:8080

>api_key: YOUR_API_KEY

<b>Command</b>

`python goreport.py 26 csv`

That would fetch the results of campaign 26 from https://localhost:8080/api/campaigns/26/?api_key=<Your_API_Key> and output the results in a csv file.

### Switching Report Output

GoReport can output either a csv file or a Word document (docx). Simply provide your preferred format as your second command line argument, as shown above in the Sample Usage section. There is not much to say about the csv format. It's your basic comma delimited file. The Word document, however, is a bit more than that.

The Word document is built from a template, template.docx. Place your template file, named template.docx, into the GoReport directory with main script. Your template should include a table style you want to use and heading styles for Heading 1 and Heading 1. Name your preferred table style "GoReport" and setup your Heading 1 and 2 styles. The headings do not need to be named, but can be renamed to "GoReport" as well as a reminder for yourself.

Feel free to create a custom style or use an existing style. The only thing that matters is a template.docx file exists and it has a "GoReport" table style.

To rename a style, right-click the style, select Modify Table Style, and set a new name.

## Additional Information

GoPhish performs it's own geo IP lookups and returns latitude and longitude. This works alright, but geo IP is often unreliable as IPs change hands or are reallocated.

GoPhish uses free lookup tools that are generally accurate or close, but sometimes get things very wrong. I can't give specific examples because they are all IPs tied to various clients, but there is the general situation you may run into. GoPhish might identify an IP as being related to Kansas. With this IP, GoPhish's location lookup will be verified by a number of geo IP tools. However, it is quite wrong. This IP now belongs to an organization in Massachusetts.

This script utilizes two tools to get a more reliable location: Google and MaxMind GeoIP. First, we use MaxMind GeoIP to match the IP address to coordinates. This requires a copy of MaxMind's free "geolite" database:

* Library:
  * https://github.com/rr2do2/maxminddb-geolite2
* MMDB Download:
  * http://dev.maxmind.com/geoip/geoip2/geolite2/

Then the script uses the Google Maps API to look-up the coordinates and return detailed location data. The URL looks like this:

http://maps.googleapis.com/maps/api/geocode/json?latlng=38,-97&sensor=false

I have found this to be more reliable, but it's always best to verify the locations, especially if location might matter to a client or your own analysis.
