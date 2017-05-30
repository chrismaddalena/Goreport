# Go Report
##### A GoPhish reporting tool

This script accepts your GoPhish campaign ID(s) as a parameter and then collects the campaign results to present the statistics and perform user-agent parsing and geo IP lookups. GoReport generates lists of IP addresses, operating systems, browser types and versions, and locations with counts for the number of times each one was seen throughout the campaign.

A note on statistics: GoReport will report the total number of events and the number of email recipients that participated in each event. In other words, GoReport will how many times GoPhish recorded a "Clicked Link" event and how many recipients clicked a link. These are very different numbers. A campaign sent to 10 people could have 9 Clicked Link events when only 3 recipients clicked a link. Knowing that recipients clicked a link or submitted data more than once is valuable information, but make sure you keep the numbers staright.

## GoReport Requirements
This script requires GoPhish, of course, and the API key for your GoPhish application. Get this key by clicking the Settings tab. The API key will be found on the first page. Each GoPhish user account has its own API key which acts as the method of authentication for that user to the GoPhish API. If you use multiple accounts with GoPhish, make sure you grab that user's API key.

These Python libraries are required as well:
* gophish
* requests
* maxminddb-geolite2
* configparser
* python-docx
* click
* user-agents
* python-dateutil (Required by the gophish library)

## GoReport Setup
You need to do a few things to get started:

* Run `pip install -r requirements.txt`.
* Download a fresh and up-to-date copy of the free MaxMind Geo IP database (see below).
* Edit/create a gophish.config configuration file that looks like the one below.
  * Note: The full host URL is required, so provide http://IP:PORT or https://IP:PORT.
	* Be aware of using HTTP vs HTTPS. If you type in the wrong one you'll receive connection errors.
* Get your campaign ID(s) by clicking your campaign(s) and referencing the URL(s) (it's the number at the end).
* If you want to be able to create Word docx reports, drop a "template.docx" template file into the GoReport directory (more information below in Selecting Report Output).

## Basic Usage
This example will assume GoPhish is on another server and HTTPS is being used. To access the API endpoint, you will need to use SSH port forwarding with port 3333 (or any other local port you wish to use):

<b>gophish.config</b>

>[GoPhish]

>gp_host: https://127.0.0.1:3333

>api_key: <YOUR_API_KEY>

<b>Command</b>

`python3 goreport.py --id 26 --format csv`

That would fetch the results of campaign 26 from https://localhost:3333/api/campaigns/26/?api_key=<Your_API_Key> and output the results to a csv file.

Multiple IDs can be provided at one time for multiple reports. The IDs can be provided using a comma-separated list, a range, or both.

Example: `python3 goreport.py --id 26,29-33,54 --format csv`

###Changing Config Files
If you use multiple GoPhish user accounts or servers, then you will have multiple API keys. To make it easier to switch between keys, GoReport's `--config` option enables you to override the default config file, gophish.config, with a config file you name. If this argument is provided with a valid, readable config file, GoReport will use it instead of gophish.config to setup the API connection.

You might use this option if you have, for example, three phishing servers running GoPhish. You could setup three config files, each with a different API key, and then use them as needed.

Example: `python3 goreport.py --id 26,29-33,54 --format csv --config phish_server_2.config`

### Combining reports
If you ran multiple campaigns using the same settings for different target groups, you may wish to run GoReport against these campaigns all at once and then combine the results into one report. This can be accomplished by adding GoReports `--combine` flag.

Example: `python3 goreport.py --id 26,29-33,54 --format csv --combine`

This command will collect the results for campaigns 26, 29, 30, 31, 32, 33, and 54. Normally, GoReport would output seven csv files, but addition of `--combine` tells GoReport to combine the results and output just one report as if they were all one large campaign.

### Switching Report Output
GoReport can output either a csv file or a Word document (docx). There is also a "quick" report option. Simply select your preferred format using the `--format` command line argument, as shown above in the Sample Usage section. There is not much to say about the csv format. It's your basic comma delimited file. The Word document, however, is a bit more than that.

The Word document is built from a template, template.docx. Place your template file, named template.docx, into the GoReport directory with main script. Your template should include a table style you want to use and heading styles for Heading 1 and Heading 1. Name your preferred table style "GoReport" and setup your Heading 1 and 2 styles. The headings do not need to be named, but can be renamed to "GoReport" as well as a reminder for yourself.

Feel free to create a custom style or use an existing style. The only thing that matters is a template.docx file exists and it has a "GoReport" table style.

To rename a style, right-click the style, select Modify Table Style, and set a new name.

Finally, there is a "quick report" option. This does not generate a report document. Instead of a report, it outputs basic information about the campaign to your terminal. This is handy for quickly checking campaign progress or referencing results after campaign completion.

### Marking Campaigns as Complete
If you want to set the status of a campaign to "Complete" when you run your report, GoReport can help you do this automatically with the `--complete` flag. If you provide this flag, GoReport will use the API to mark each campaign ID s "Complete" to end the campaign and update the status in GoPhish.

## Additional Information
GoPhish performs it's own geo IP lookups and returns latitude and longitude. This works alright, but geo IP is often unreliable as IPs change hands or are reallocated.

GoPhish uses free lookup tools that are generally accurate or close, but sometimes get things very wrong. GoReport utilizes two tools to double-check the location data: Google and MaxMind GeoIP. First, we use MaxMind GeoIP to match the IP address to coordinates. This requires a copy of MaxMind's free "geolite" database:

* Library:
  * https://github.com/rr2do2/maxminddb-geolite2
* MMDB Download:
  * http://dev.maxmind.com/geoip/geoip2/geolite2/

Then the script uses the Google Maps API to look-up the coordinates and return detailed location data. The URL looks like this:

http://maps.googleapis.com/maps/api/geocode/json?latlng=38,-97&sensor=false

This has proven to be more reliable, but it's always best to verify the locations, especially if location might matter to your client or your own analysis.

## Technical Information
If you'd like to review the code, here is a basic outline of the process:

GoReport.py uses Python 3 and the Command Line Interface Creation Kit (CLICK) library. When the script is run, a new GoReport object is created. The __init__ function for the GoReport class creates a connection to your GoPhish server using the provided API key for authentication. Then the run() function is called.

Run() uses the command line options to kick-off reporting. A For loop is used to loop through all campaign IDs provided with `--id`. Your GoPhish server is contacted for campaign details for each individual ID.

First, collect_all_campaign_info() is called to stash basic campaign information in variables. This includes data like the campaign's name, when it was run, it's status, the SMTP server used, the template's name, and more.

Second, process_timeline_events() is called to get GoPhish's timeline model for the ID. This includes the events recorded by GoPhish. This function runs second because it fills-in some lists that are reviewed by process_results().

Third, process_results() is called to get GoPhish's results model for the ID. This provides data like the number of targets in the campaign.

GoReport uses these steps to setup some lists to determine the basic results for the campaign, e.g. who was successfully sent an email, which recipients clicked a linked, and which recipients provided data.

With this foundation, GoReport can arrange the data in any number of ways for a report. At any time, the lists can be queried to check if a certain email address in the results model appears in the targets_clicked list to confirm if that recipient clicked a link. That can then kick-off a review of the timeline model to collect details. GoPhish keeps the details like IP address and user-agent in the timeline model and basic information in the results model.

## Change Log
May 30, 2017
* Added `--verbose` to clean-up terminal output without removing the optional feedback.
* Fixed a "NoneType + str" bug in the geolocation lookups.
* Added more feedback during report writing so user can see some progress being made during big reports.
* Duplicate campaign IDs are now trimmed in case `--combine` is used with duplicate IDs and to avoid wasted processing time.
* Fixed-up the display of which campaign IDs will be processed.
* ASCII art!

May 27, 2017
* Added `--config` option to allow for config files to be named to support multiple servers and API keys.
* Cleaned-up some code.

May 25, 2017
* Added `--complete` option to enable user's to mark a campaign as "Complete" when reporting.
* Modified `--id` argument to accept comma-separated strings of IDs or a range of IDs.
* Added `--combine` option to allow for combining campaigns results into a single report when multiple IDs are provided.
