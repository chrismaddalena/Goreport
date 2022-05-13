# Goreport v3.0, a Gophish Reporting Tool

This script accepts your Gophish campaign ID(s) as a parameter and then collects the campaign results to present the statistics and perform user-agent parsing and geolocation lookups for IP addresses. Goreport generates lists of IP addresses, operating systems, browser types and versions, and locations with counts for the number of times each one was seen throughout the campaign.

A note on statistics: Goreport will report the total number of events and the number of email recipients that participated in each event. In other words, Goreport will show how many times Gophish recorded a "Clicked Link" event and how many recipients clicked a link. These are very different numbers. A campaign sent to 10 people could have 9 Clicked Link events when only 3 recipients clicked a link. Knowing that recipients clicked a link or submitted data more than once is valuable information, but make sure you keep the numbers straight.

## Goreport Requirements

This script requires a Gophish server, and active or complete campaign, and the API key for your Gophish application. Get this key by clicking the Settings tab. The API key will be found on the first page. Each Gophish user account has its own API key which acts as the method of authentication for that user to the Gophish API. If you use multiple accounts with Gophish, make sure you grab the correct users API key.

These Python libraries are required as well:
* Gophish
* requests
* xlsxwriter
* configparser
* python-docx
* click
* user-agents
* python-dateutil (Required by the Gophish library)

## Goreport Setup

You need to do a few things to get started:

* Run `pip install -r requirements.txt`.
* Edit/create a Gophish.config configuration file that looks like the one below.
  * Note: The full host URL is required, so provide http://IP:PORT or https://IP:PORT.
	* Be aware of using HTTP vs HTTPS. If you type in the wrong one you'll receive connection errors.
* Get your campaign ID(s) by clicking your campaign(s) and referencing the URL(s) (it's the number at the end).
* If you want to be able to create Word docx reports, drop a "template.docx" template file into the Goreport directory (more information below in Selecting Report Output).

## Basic Usage

This example will assume Gophish is on another server and HTTPS is being used. To access the API endpoint, you will need to use SSH port forwarding with port 3333 (or any other local port you wish to use):

### Gophish.config

```
[Gophish]
gp_host: https://127.0.0.1:3333
api_key: <YOUR_API_KEY>

[ipinfo.io]
ipinfo_token: <IPINFO_API_KEY>

[Google]
geolocate_key: <GEOLOCATE_API_KEY>
```

### A Basic Command

`python3 Goreport.py --id 26 --format excel`

That would fetch the results of campaign 26 from https://localhost:3333/api/campaigns/26/?api_key=<Your_API_Key> and output the results to an xlsx file.

Multiple IDs can be provided at one time for multiple reports. The IDs can be provided using a comma-separated list, a range, or both.

Example: `python3 Goreport.py --id 26,29-33,54 --format csv`

### Changing Config Files

If you use multiple Gophish user accounts or servers, then you will have multiple API keys. To make it easier to switch between keys, Goreport's `--config` option enables you to override the default config file, gophish.config, with a config file you name. If this argument is provided with a valid, readable config file, Goreport will use it instead of gophish.config to setup the API connections.

You might use this option if you have, for example, three phishing servers running Gophish. You could setup three config files, each with a different Gophish API key, and then use them as needed.

Example: `python3 Goreport.py --id 26,29-33,54 --format csv --config phish_server_2.config`

### Combining Reports

If you ran multiple campaigns using the same settings for different target groups, you may wish to run Goreport against these campaigns all at once and then combine the results into one report. This can be accomplished by adding Goreports `--combine` flag.

Example: `python3 Goreport.py --id 26,29-33,54 --format excel --combine`

This command would collect the results for campaigns 26, 29, 30, 31, 32, 33, and 54. Normally, Goreport would output seven xlsx files, but the addition of `--combine` tells Goreport to combine the results and output just one report as if they were all one large campaign.

### Switching Report Output

Goreport can output either an Excel spreadsheet (xlsx) or a Word document (docx). There is also a "quick" report option. Simply select your preferred format using the `--format` command line argument, as shown above in the Sample Usage section. There is not much to say about the csv format.

The Word document is built from a template, template.docx. Place your template file, named template.docx, into the Goreport directory with the main script. Your template should include a table style you want to use and heading styles for Heading 1 and Heading 1. Name your preferred table style "Goreport" and setup your Heading 1 and 2 styles.

Feel free to create a custom style or use an existing style. The only thing that matters is a template.docx file exists and it has a "Goreport" table style.

To rename a style, right-click the style, select Modify Table Style, and set a new name.

The Excel option outputs a nicely formatted Excel workbook with multiple worksheets for the different collections of results and statistics. This is a nice option if you want to easily sort or filter result tables.

Finally, there is a "quick" option. This does not generate a report document. Instead of a report, it outputs basic information about the campaign to your terminal. This is handy for quickly checking campaign progress or referencing results after campaign completion.

### Marking Campaigns as Complete

If you want to set the status of a campaign to "Complete" when you run your report, Goreport can help you do this automatically with the `--complete` flag. If you provide this flag, Goreport will use the API to mark each campaign ID as "Complete" to end the campaign and update the status in Gophish.

## Additional Information

Gophish performs it's own geolocation lookups with IP addresses and returns latitude and longitude. This works alright, but may fail and return coordinates of `0,0` or may return old information.

Goreport has two options that might be used to improve location results. The first, and recommended option, is the ipinfo.io API. API access is free as long as you make less than 1,000 queries per 24 hour period. That should not be too difficult for a phishing campaign.

If an ipinfo.io API key is added to the config file Goreport will automatically use ipinfo.io to gather current geolocation information for each unique IP address.

The second option is the Google Maps API. Goreport v1.0 used the Maps API when it was free. Google now charges $0.005/request for the Geolocate API (as it is now called). If you would prefer to not use ipinfo.io, activate the Maps Geolocate API on a Google account and add the API key to the Goreport config file. Then add the `--google` flag to your Goreport command anytime you want Goreport to use the API to lookup Gophish's coordinates to get a formatted address.

## Technical Information

If you'd like to review the code, here is a basic outline of the process:

Goreport.py uses Python 3 and the Command Line Interface Creation Kit (CLICK) library. When the script is run, a new Goreport object is created. The `__init__` function for the Goreport class creates a connection to your Gophish server using the provided API key for authentication. Then the `run()` function is called.

`Run()` uses the command line options to kick-off reporting. A For loop is used to loop through all campaign IDs provided with `--id`. Your Gophish server is contacted for campaign details for each individual ID.

First, `collect_all_campaign_info()` is called to stash basic campaign information in variables. This includes data like the campaign's name, when it was run, its status, the SMTP server used, the template's name, and more.

Second, `process_timeline_events()` is called to get Gophish's timeline model for the ID. This includes the events recorded by Gophish. This function runs second because it fills-in some lists that are reviewed by process_results().

Third, `process_results()` is called to get Gophish's results model for the ID. This provides data like the number of targets in the campaign.

Goreport uses these steps to setup some lists to determine the basic results for the campaign, e.g. who was successfully sent an email, which recipients clicked a linked, and which recipients provided data.

With this foundation, Goreport can arrange the data in any number of ways for a report. At any time, the lists can be queried to check if a certain email address in the results model appears in the `targets_clicked` list to confirm if that recipient clicked a link. That can then kick-off a review of the timeline model to collect details. Gophish keeps the details like IP address and user-agent in the timeline model and basic information in the results model.
