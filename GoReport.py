#!/usr/bin/env python3
"""
Name:	GoReport v2.0
Author:	Christopher Maddalena

This is part script and part class for interfacing with the GoPhish API. You provide
an API key and host (e.g. http://ip:port) in a gophish.ini file for the connection.

Then provide a campaign ID as a command line argument: python3 goreport.py 36

The results will be fetched and parsed for additional processing. A csv OR Word .docx
file is created with all of the campaign details and some of the settings that
may be of interest (e.g. SMTP hostname). The class also performs some analysis
data points, like the browser user-agents and IP addresses, to generate statistics
for browser versions, operating systems, and locations.
"""

# Basic imports
from gophish import Gophish
import sys
import csv
import configparser

# Imports for statistics, e.g. browsera and operating systems
from user_agents import parse
from collections import Counter

# Imports for web requests, e.g. Google Maps API for location data
# Disables the insecure HTTPS warning for the self-signed GoPhish certs
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Import the MaxmInd's GeoLite for IP address GeoIP look-ups
from geolite2 import geolite2

# Imports for writing the Word.doc report
from docx import *
from docx.shared import *
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.shared import OxmlElement, qn


usage = "Usage: goreport.py Campaign_ID OUTPUT_TYPE -- e.g. gophish.py 26 csv"

# Collect the command line arguments for campaign ID and report type
if len(sys.argv) > 2:
	CAM_ID = sys.argv[1] # Campaign ID for the report
	OUTPUT_TYPE = sys.argv[2]
	try:
		CAM_ID = int(CAM_ID)
	except:
		print("[!] You entered an invalid campaign ID! {} will not do!".format(CAM_ID))
		print(usage)
		sys.exit()

	if OUTPUT_TYPE == "csv" or OUTPUT_TYPE == "word":
		pass
	else:
		print("[!] Invalid output type sepcified, {}. Select either csv or word.".format(OUTPUT_TYPE))
else:
	print(usage)
	sys.exit()

# Open the config file to make sure it exists and is readable
try:
	config = configparser.ConfigParser()
	config.read('gophish.ini')
except Exception as e:
	print("[!] Could not open the /gophish.ini config file -- make sure it exists and is readable.")
	print("[!] Details: {}".format(e))
	sys.exit()


def set_column_width(column, width):
	"""Custom function for quickly and easily setting the width of a table's
	column in the Word docx output.

	An option missing from the basic Python docx library.
	"""
	for cell in column.cells:
		cell.width = width


def ConfigSectionMap(section):
    """This function helps by reading accepting a config file section, from gophish.ini,
    and returning a dictionary object that can be referenced for configuration settings.
    """
    section_dict = {}
    options = config.options(section)
    for option in options:
        try:
            section_dict[option] = config.get(section, option)
            if section_dict[option] == -1:
                DebugPrint("[-] Skipping: {}".format(option))
        except:
            print("[!] There was an error with: {}".format(option))
            section_dict[option] = None
    return section_dict


# Read in the values from the config file
try:
	GP_HOST = ConfigSectionMap("GoPhish")['gp_host']
	API_KEY = ConfigSectionMap("GoPhish")['api_key']
	MMDB = ConfigSectionMap("GeoIP")['mmdb_path']
except Exception as e:
	print("[!] There was a problem reading values from the gophish.ini file!")
	print("[!] Details: {}".format(e))
	sys.exit()


class GPCampaign(object):
	"""This class uses the GoPhish library to create a new GoPhish API connection
	and queries GoPhish for information and results related to the specified
	campaign.
	"""
	# Variables for holding GoPhish models
	campaign = None
	results = None
	timeline = None

	# Variables for holding campaign information
	cam_id = None
	cam_name = None
	cam_status = None
	created_date = None
	launch_date = None
	completed_date = None
	cam_url = None
	cam_redirect_url = None
	cam_from_address = None
	cam_subject_line = None
	cam_template_name = None
	cam_capturing_passwords = None
	cam_capturing_credentials = None
	cam_page_name = None
	cam_smtp_host = None

	# Variables and lists for tracking event numbers
	total_targets = None
	total_sent = None
	total_opened = None
	total_clicked = None
	total_submitted = None
	targets_opened = []
	targets_clicked = []
	targets_submitted = []

	# Lists for holding totals for statistics
	browsers = []
	operating_systems = []
	locations = []
	ip_addresses = []

	# Output filename
	output_csv_report = None
	output_word_report = None

	def __init__(self):
		"""Initiate the connection to the GoPhish server with the provided host, port, and API key"""
		# Connect to API
		try:
			print("[+] Connecting to GoPhish at {}".format(GP_HOST))
			self.api = Gophish(API_KEY, host=GP_HOST, verify=False)
			# Request campaign details
			print("[+] We will be fetching results for Campaign ID {}...".format(CAM_ID))
			self.campaign = self.api.campaigns.get(campaign_id=CAM_ID)
		except Exception as e:
			print("[!] There was a problem rconnecting to GoPhish! Check your gophish.ini to confirm host, port, annd API key.")
			print("[!] Details: {}".format(e))
			sys.exit()

		# Create the MaxMInd GeoIP reader for the CeoLite2-City.mmdb database file
		self.geoip_reader = geolite2.reader()

	def run(self):
		"""Run everything to process the target campaign."""
		# Collect campaign details and process data
		self.collect_campaign_details()
		self.parse_results()
		self.parse_timeline_events()
		# Generate the report
		if OUTPUT_TYPE == "csv":
			self.output_csv_report = self._build_output_csv_file_name()
			self.write_csv_report()
		else:
			self.output_word_report = self._build_output_word_file_name()
			self.write_word_report()

	def _build_output_csv_file_name(self):
		"""A helper function to create the output report name."""
		csv_report = "GoPhish Results for Campaign - {}.csv".format(self.cam_name)
		return csv_report

	def _build_output_word_file_name(self):
		"""A helper function to create the output report name."""
		word_report = "GoPhish Results for Campaign - {}.docx".format(self.cam_name)
		return word_report

	def collect_campaign_details(self):
		"""Collect the campaign's details set values for each of the declared variables."""
		# Collect the basic campaign details
		# Plus a quick and dirty check to see if the campaign ID is valid
		try:
			self.cam_id = self.campaign.id
		except:
			print("[!] Looks like that campaign ID does not exist!")
			sys.exit()

		self.cam_name = self.campaign.name
		self.cam_status = self.campaign.status
		self.created_date = self.campaign.created_date
		self.launch_date = self.campaign.launch_date
		self.completed_date = self.campaign.completed_date
		self.cam_url = self.campaign.url

		# Collect the results and timeline, lists
		self.results = self.campaign.results
		self.timeline = self.campaign.timeline

		# Collect SMTP information
		self.smtp = self.campaign.smtp
		self.cam_from_address = self.smtp.from_address
		self.cam_smtp_host = self.smtp.host

		# Collect the template and landing page information
		self.template = self.campaign.template
		self.page = self.campaign.page

		self.cam_subject_line = self.template.subject
		self.cam_template_name = self.template.name
		self.cam_template_attachments = self.template.attachments
		self.cam_page_name = self.page.name
		self.cam_redirect_url = self.page.redirect_url
		self.cam_capturing_passwords = self.page.capture_passwords
		self.cam_capturing_credentials = self.page.capture_credentials

	def parse_results(self):
		"""Process the results model to collect basic data, like total targets.

		The results model can provide:
		first_name, last_name, email, position, and IP address
		"""
		# Total length of results gives us the total number of targets
		self.total_targets = len(self.results)

		# Go through all results and extract data for statistics
		for x in self.results:
			if not x.ip == "":
				self.ip_addresses.append(x.ip)

	def parse_timeline_events(self):
		"""Process the timeline model to colelct basic data, like total clicks.

		The timeline model contains all events that occured during the campaign.
		"""
		# Create counters for enumeration
		sent_counter = 0
		opened_counter = 0
		click_counter = 0
		submitted_counter = 0
		# Run through all events and count each of the four basic events
		for x in self.timeline:
			if x.message == "Email Sent":
				sent_counter += 1
			elif x.message == "Email Opened":
				opened_counter += 1
				self.targets_opened.append(x.email)
			elif x.message == "Clicked Link":
				click_counter += 1
				self.targets_clicked.append(x.email)
			elif x.message == "Submitted Data":
				submitted_counter += 1
				self.targets_submitted.append(x.email)
		# Assign the counter values to
		self.total_sent = sent_counter
		self.total_opened = opened_counter
		self.total_clicked = click_counter
		self.submitted_counter = submitted_counter

	def lookup_ip(self, ip):
		"""Check the GeoLite database for a location for the provided IP address.

		This returns a large dict with more data than is probably needed for
		a report. This gets continent, country, registered_country, and location.
		Also, this dict includes multiple languages.

		You may wonder why get_google_location_data() is needed if this provides
		a lot of data from MaxMind. Unfortunately, the MaxMind database will not
		always have the data needed most for the report (city, state, country).
		It may only have the continent name. Luckily, it seems to always have coordinates
		that can be compared to GoPhish's coordinates and passed to get_google_location_data().
		"""
		match  = self.geoip_reader.get(ip)
		if match is not None:
			return match
		else:
			# return "No match"
			return None

	def get_google_location_data(self, lat, lon):
		"""Use Google's Maps API to collect GeoIP info for the provided latitude
		and longitude.

		Google returns a bunch of JSON with a variety of location data.
		This function sticks to the first set of "address_components" for the
		country, locality (city), and administrative_level_1 (state).

		Ex: http://maps.googleapis.com/maps/api/geocode/json?latlng=35,-93&sensor=false
		"""
		url = "http://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&sensor=false".format(lat, lon)
		v = requests.get(url)
		j = v.json()
		try:
			components = j['results'][0]['address_components']
			country = town = None
			for c in components:
				if "country" in c['types']:
					country = c['long_name']
				if "locality" in c['types']:
					town = c['long_name']
				if "administrative_area_level_1" in c['types']:
					state = c['long_name']
			return "{}. {}. {}".format(town, state, country)
		except:
			# return "None"
			return None

	def compare_ip_addresses(self, target_ip, browser_ip):
		"""Compare the IP addresses of the target to that of an event. The goal:
		Looking for a mismatch that might identify some sort of interesting event.
		This might indicate an email was forwarded, a VPN was switched on/off, or
		maybe the target is at home.
		"""
		if target_ip == browser_ip:
			return target_ip
		else:
			# We have an IP mismatch! Hard to tell what this might be.
			print("[!] Interesting Event: Browser and target IP address do not match!")
			print("L.. This target's ({}) URL was clicked from a browser at {} -- email may have been forwarded or the target is home/using VPN/etc. Interesting!".format(target_ip, browser_ip))
			# This is an IP address not included in the results model, so we add it to our list here
			self.ip_addresses.append(browser_ip)
			return browser_ip

	def compare_ip_coordinates(self, target_latitude, target_longitude, mmdb_latitude, mmdb_longitude, ip_address):
		"""Compare the IP address cooridnates reported by MaxMind and GoPhish.
		If they do not match, some additional -- manual -- investigation should
		be done for any client-facing deliverables.
		"""
		if target_latitude == mmdb_latitude and target_longitude == mmdb_longitude:
			# Coordinates match what GoPhish recorded, so query Google Maps for details
			coordinates_location = self.get_google_location_data(target_latitude, target_longitude)
			self.locations.append(coordinates_location)
			return coordinates_location
		else:
			# MaxMind and GoPhish have different coordinates, so this is a tough spot
			# Both locations can be recorded for investigation, but what to do for location statistics?
			# It was decided both would be recorded as one location with an asterisk, flagged for investigation
			print("[!] Warning: Location coordinates mis-match between MaxMind and GoPhish for {}. Look for location with * to investigate and pick the right location.".format(ip_address))
			coordinates_location = self.get_google_location_data(target_latitude, target_longitude)
			coordinates_location += "     ALTERNATE:" + self.get_google_location_data(mmdb_latitude, mmdb_longitude)
			self.locations.append(coordinates_location + " *")
			return "{}".format(coordinates_location + " *")

	def write_csv_report(self):
		"""Assemble and output the csv file report."""
		with open(self.output_csv_report, 'w') as csvfile:
			# Create csv writer
			writer = csv.writer(csvfile, dialect='excel', delimiter=',', quotechar="'", quoting=csv.QUOTE_MINIMAL)

			# Write a campaign summary at the top of the report
			writer.writerow(["CAMPAIGN RESULTS FOR:", "{}".format(self.cam_name)])
			writer.writerow(["Status", "{}".format(self.cam_status)])
			writer.writerow(["Created", "{}".format(self.created_date)])
			writer.writerow(["Started", "{}".format(self.launch_date)])
			if self.cam_status == "Completed":
				writer.writerow(["Completed", "{}".format(self.completed_date)])
			# Write the campaign details -- email details and template settings
			writer.writerow("")
			writer.writerow(["CAMPAIGN DETAILS"])
			writer.writerow(["From", "{}".format(self.cam_from_address)])
			writer.writerow(["Subject", "{}".format(self.cam_subject_line)])
			writer.writerow(["Phish URL", "{}".format(self.cam_url)])
			if self.cam_redirect_url == "":
				writer.writerow(["Redirect URL", "Not Used"])
			else:
				writer.writerow(["Redirect URL", "{}".format(self.cam_redirect_url)])
			if self.cam_template_attachments == []:
				writer.writerow(["Attachment(s)", "None"])
			else:
				writer.writerow(["Attachment(s)", "{}".format(self.cam_template_attachments)])
			writer.writerow(["Captured Credentials", "{}".format(self.cam_capturing_credentials)])
			writer.writerow(["Stored Passwords", "{}".format(self.cam_capturing_passwords)])
			# Write a high level summary for stats
			writer.writerow("")
			writer.writerow(["HIGH LEVEL RESULTS"])
			writer.writerow(["Total Targets", "{}".format(self.total_targets)])
			writer.writerow(["Opened", "{}".format(self.total_opened)])
			writer.writerow(["Clicked", "{}".format(self.total_clicked)])
			writer.writerow(["Entered Data", "{}".format(self.total_submitted)])

			# End of the campaign summary and beginning of the event summary
			writer.writerow("")
			writer.writerow(["SUMMARY OF EVENTS"])
			writer.writerow(["Email Address", "Open", "Click", "Phish"])
			# Add targets to the results table
			for target in self.results:
				result = target.email

				if target.email in self.targets_opened:
					result += ",Y"
				else:
					result += ",N"

				if target.email in self.targets_clicked:
					result += ",Y"
				else:
					result += ",N"

				if target.email in self.targets_submitted:
					result += ",Y"
				else:
					result += ",N"

				writer.writerow(["{}".format(result)])

			# End of the event summary and beginning of the detailed results
			for target in self.results:
				writer.writerow("")
				writer.writerow(["{} {}".format(target.first_name, target.last_name, target.email)])
				writer.writerow(["{}".format(target.email)])
				# Parse each timeline event
				# Timestamps are parsed to get date and times by splitting date
				# and time and dropping the milliseconds and timezone
				# Ex: 2017-01-30T14:31:22.534880731-05:00
				for event in self.timeline:
					if event.message == "Email Sent" and event.email == target.email:
						# Parse the timestamp into separate date and time variables
						temp = event.time.split('T')
						sent_date = temp[0]
						sent_time = temp[1].split('.')[0]
						# Record the email sent date and time in the report
						writer.writerow(["Sent on {} at {}".format(sent_date.replace(",", ""), sent_time)])

					if event.message == "Email Opened" and event.email == target.email:
						# Parse the timestamp
						temp = event.time.split('T')
						# Record the email preview date and time in the report
						writer.writerow(["Email Preview",  "{} {}".format(temp[0], temp[1].split('.')[0])])

					if event.message == "Clicked Link" and event.email == target.email:
						# Parse the timestmap and add the time to the results row
						temp = event.time.split('T')
						result = temp[0] + " " + temp[1].split('.')[0]

						# Add the IP address to the results row
						# Sanity check to see if browser IP matches the target's recorded IP
						result += ",{}".format(self.compare_ip_addresses(target.ip, event.details['browser']['address']))

						# Get the location data and add to results row
						# This is based on the IP address pulled from the browser for this event
						# Start by getting the coordinates from GeoLite2
						mmdb_location = self.lookup_ip(event.details['browser']['address'])
						if not mmdb_location == None:
							mmdb_latitude, mmdb_longitude = mmdb_location['location']['latitude'], mmdb_location['location']['longitude']
							# Check if GoPhish's coordinates agree with these MMDB results
							result += ",{}".format(self.compare_ip_coordinates(target.latitude, target.longitude, mmdb_latitude, mmdb_longitude, event.details['browser']['address']))
						else:
							result += "IP address look-up returned None"

						# Parse the user-agent string and add browser and OS details to the results row
						user_agent = parse(event.details['browser']['user-agent'])

						browser_details = user_agent.browser.family + " " + user_agent.browser.version_string
						result += ",{}".format(browser_details)
						self.browsers.append(browser_details)

						os_details = user_agent.os.family + " " + user_agent.os.version_string
						result += ",{}".format(os_details)
						self.operating_systems.append(os_details)

						# Write the results row to the report for this target
						writer.writerow(["Email Link Clicked"])
						writer.writerow(["Time", "IP", "City", "Browser", "Operating System"])
						writer.writerow([result])

					# Now we have events for submitted data. A few notes on this:
					# There is no epxectation of data being submitted without a Clicked Link event
					# Assuming that, the following process does NOT flag IP
					# mismatches or add to the list of seen locations, OSs, IPs, or browsers.
					if event.message == "Submitted Data" and event.email == target.email:
						# Parse the timestmap and add the time to the results row
						temp = event.time.split('T')
						result += temp[0] + " " + temp[1].split('.')[0]

						# Add the IP address to the results row
						result += ", {}".format(event.details['browser']['address'])

						# Get the location data and add to results row
						# This is based on the IP address pulled from the browser for this event
						# Start by getting the coordinates from GeoLite2
						mmdb_location = self.lookup_ip(event.details['browser']['address'])
						if not mmdb_location == None:
							mmdb_latitude, mmdb_longitude = mmdb_location['location']['latitude'], mmdb_location['location']['longitude']
							# Check if GoPhish's coordinates agree with these MMDB results
							result += self.compare_ip_coordinates(target.latitude, target.longitude, mmdb_latitude, mmdb_longitude)
						else:
							result += "IP address look-up returned None"

						# Parse the user-agent string and add browser and OS details to the results row
						user_agent = parse(event.details['browser']['user-agent'])

						browser_details = user_agent.browser.family + " " + user_agent.browser.version_string
						result += ",{}".format(browser_details)

						os_details = user_agent.os.family + " " + user_agent.os.version_string
						result += ",{}".format(os_details)

						data_payload = events.details # TODO: Test with submitted data for this
						result += ",{}".format(data_payload.group())

						# Write the results row to the report for this target
						writer.writerow(["Submitted Data Captured"])
						writer.writerow(["Time", "IP", "City", "Browser", "Operating System", "Data Captured"])
						writer.writerow([result])

			# End of the detailed results and the beginning of browser, location, and OS stats
			# Counter is used to count all elements in the lists to create a unique list with totals
			writer.writerow("")
			writer.writerow(["RECORDED BROWSERS BY UA:"])
			writer.writerow(["Browser", "Seen"])

			counted_browsers = Counter(self.browsers)
			for key, value in counted_browsers.items():
				writer.writerow(["{},{}".format(key, value)])

			writer.writerow("")
			writer.writerow(["RECORDED OP SYSTEMS:"])
			writer.writerow(["Operating System", "Seen"])

			counted_os = Counter(self.operating_systems)
			for key, value in counted_os.items():
				writer.writerow(["{},{}".format(key, value)])

			writer.writerow([" "])
			writer.writerow(["RECORDED LOCATIONS:"])
			writer.writerow(["Location", "Visits"])

			counted_locations = Counter(self.locations)
			for key, value in counted_locations.items():
				writer.writerow(["{},{}".format(key, value)])

			writer.writerow([" "])
			writer.writerow(["RECORDED IP ADDRESSES:"])
			writer.writerow(["IP Address", "Seen"])

			counted_ip_addresses = Counter(self.ip_addresses)
			for key, value in counted_ip_addresses.items():
				writer.writerow(["{},{}".format(key, value)])

			print("[+] Done! Check \'{}\' for your results.".format(self.output_csv_report))

	def write_word_report(self):
		"""Assemble and output the csv file report."""
		# Create document writer using the template and a style editor
		d = Document("template.docx")
		styles = d.styles

		# Create a custom style for table cells
		style = styles.add_style('Cell Text', WD_STYLE_TYPE.CHARACTER)
		cellText = d.styles['Cell Text']
		cellText_font = cellText.font
		cellText_font.name = 'Calibri'
		cellText_font.size = Pt(12)
		cellText_font.bold = True
		cellText_font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

		# Write a campaign summary at the top of the report
		d.add_heading("Executive Summary", 1)
		p = d.add_paragraph()
		run = p.add_run("CAMPAIGN RESULTS FOR: {}".format(self.cam_name))
		run.bold = True

		p.add_run("""
Status: {}
Created: {}
Started: {}
Completed: {}

""".format(self.cam_status, self.created_date, self.launch_date,
		self.completed_date))

		# Write the campaign details -- email details and template settings
		run = p.add_run("CAMPAIGN DETAILS")
		run.bold = True

		p.add_run("""
From: {}
Subject: {}
Phish URL: {}
Redirect URL: {}
Attachment(s): {}
Captured Credentials: {}
Stored Passwords: {}

""".format(self.cam_from_address, self.cam_subject_line, self.cam_url,
		self.cam_redirect_url, self.cam_template_attachments, self.cam_capturing_credentials,
		self.cam_capturing_passwords))

		# Write a high level summary for stats
		run = p.add_run("HIGH LEVEL RESULTS")
		run.bold = True

		p.add_run("""
Total Targets: {}
Opened: {}
Clicked: {}
Entered Data: {}
""".format(self.total_targets, self.total_opened, self.total_clicked,
		self.total_submitted))

		d.add_page_break()

		# End of the campaign summary and beginning of the event summary
		d.add_heading("Summary of Events", 1)
		d.add_paragraph("The table below summarizes who opened and clicked on emails sent in this campaign.")

		# Create a table to hold the event summary results
		table = d.add_table(rows=1, cols=4, style="GoReport")
		set_column_width(table.columns[0], Cm(4.2))
		set_column_width(table.columns[1], Cm(1.4))
		set_column_width(table.columns[2], Cm(1.4))
		set_column_width(table.columns[3], Cm(1.4))

		header1 = table.cell(0,0)
		header1.text = ""
		header1.paragraphs[0].add_run("Email Address", "Cell Text").bold = True

		header2 = table.cell(0,1)
		header2.text = ""
		header2.paragraphs[0].add_run("Open", "Cell Text").bold = True

		header3 = table.cell(0,2)
		header3.text = ""
		header3.paragraphs[0].add_run("Click", "Cell Text").bold = True

		header4 = table.cell(0,3)
		header4.text = ""
		header4.paragraphs[0].add_run("Phish", "Cell Text").bold = True

		# Add targets to the results table
		counter = 1
		for target in self.results:
			table.add_row()
			temp_cell = table.cell(counter,0)
			temp_cell.text = target.email

			if target in self.targets_opened:
				temp_cell = table.cell(counter,1)
				temp_cell.text = "Y"
			else:
				temp_cell = table.cell(counter,1)
				temp_cell.text = "N"

			if target in self.targets_clicked:
				temp_cell = table.cell(counter,2)
				temp_cell.text = "Y"
			else:
				temp_cell = table.cell(counter,2)
				temp_cell.text = "N"

			if target in self.targets_submitted:
				temp_cell = table.cell(counter,3)
				temp_cell.text = "Y"
			else:
				temp_cell = table.cell(counter,3)
				temp_cell.text = "N"

			counter += 1

		d.add_page_break()

		# End of the event summary and beginning of the detailed results
		d.add_heading("Detailed Findings", 1)
		for target in self.results:
			# Create counters that will be used when adding rows
			# We need a counter to track the cell location
			opened_counter = 1
			clicked_counter = 1
			submitted_counter = 1
			# Create a heading 1 for the first and last name and heading 2 for email address
			d.add_heading("{} {}".format(target.first_name, target.last_name), 2)
			p = d.add_paragraph(target.email)

			p = d.add_paragraph()
			# Save a spot to record the email sent date and time in the report
			email_sent_run = p.add_run()

			# Create the Email Opened/Previewed table
			p = d.add_paragraph()
			p.style = d.styles['Normal']
			run = p.add_run("Email Previews")
			run.bold = True

			opened_table = d.add_table(rows=1, cols=1, style="GoReport")
			opened_table.autofit = True
			opened_table.allow_autofit = True

			header1 = opened_table.cell(0,0)
			header1.text = ""
			header1.paragraphs[0].add_run("Time", "Cell Text").bold = True

			# Create the Clicked Link table
			p = d.add_paragraph()
			p.style = d.styles['Normal']
			run = p.add_run("Email Link Clicked")
			run.bold = True

			clicked_table = d.add_table(rows=1, cols=5, style="GoReport")
			clicked_table.autofit = True
			clicked_table.allow_autofit = True

			header1 = clicked_table.cell(0,0)
			header1.text = ""
			header1.paragraphs[0].add_run("Time", "Cell Text").bold = True

			header2 = clicked_table.cell(0,1)
			header2.text = ""
			header2.paragraphs[0].add_run("IP", "Cell Text").bold = True

			header3 = clicked_table.cell(0,2)
			header3.text = ""
			header3.paragraphs[0].add_run("City", "Cell Text").bold = True

			header4 = clicked_table.cell(0,3)
			header4.text = ""
			header4.paragraphs[0].add_run("Browser", "Cell Text").bold = True

			header5 = clicked_table.cell(0,4)
			header5.text = ""
			header5.paragraphs[0].add_run("Operating System", "Cell Text").bold = True

			# Create the Submitted Data table
			p = d.add_paragraph()
			p.style = d.styles['Normal']
			run = p.add_run("Phishgate Data Captured")
			run.bold = True

			submitted_table = d.add_table(rows=1, cols=6, style="GoReport")
			submitted_table.autofit = True
			submitted_table.allow_autofit = True

			header1 = submitted_table.cell(0,0)
			header1.text = ""
			header1.paragraphs[0].add_run("Time", "Cell Text").bold = True

			header2 = submitted_table.cell(0,1)
			header2.text = ""
			header2.paragraphs[0].add_run("IP", "Cell Text").bold = True

			header3 = submitted_table.cell(0,2)
			header3.text = ""
			header3.paragraphs[0].add_run("City", "Cell Text").bold = True

			header4 = submitted_table.cell(0,3)
			header4.text = ""
			header4.paragraphs[0].add_run("Browser", "Cell Text").bold = True

			header5 = submitted_table.cell(0,4)
			header5.text = ""
			header5.paragraphs[0].add_run("Operating System", "Cell Text").bold = True

			header6 = submitted_table.cell(0,5)
			header6.text = ""
			header6.paragraphs[0].add_run("Data Captured", "Cell Text").bold = True
			# Parse each timeline event
			# Timestamps are parsed to get date and times by splitting date
			# and time and dropping the milliseconds and timezone
			# Ex: 2017-01-30T14:31:22.534880731-05:00
			for event in self.timeline:
				if event.message == "Email Sent" and event.email == target.email:
					# Parse the timestamp into separate date and time variables
					temp = event.time.split('T')
					sent_date = temp[0]
					sent_time = temp[1].split('.')[0]
					# Record the email sent date and time in the report, in the run reserved earlier
					email_sent_run.text = "Sent on {} at {}".format(sent_date, sent_time)

				if event.message == "Email Opened" and event.email == target.email:
					# Always begin by adding a row to the appropriate table
					opened_table.add_row()
					# Parse the timestamp for and add it to column 0
					# Target the cell located at (counter, 0)
					timestamp = opened_table.cell(opened_counter,0)
					# Get the value for the table cell
					temp = event.time.split('T')
					# Write the value to the table cell
					timestamp.text = temp[0] + " " + temp[1].split('.')[0]
					# Finally, increment the counter to track the row for adding new rows
					# for any addiitonal event sof this type
					opened_counter += 1

				if event.message == "Clicked Link" and event.email == target.email:
					clicked_table.add_row()
					timestamp = clicked_table.cell(clicked_counter,0)
					temp = event.time.split('T')
					timestamp.text = temp[0] + " " + temp[1].split('.')[0]

					ip_add = clicked_table.cell(clicked_counter,1)
					ip_add.text = self.compare_ip_addresses(target.ip, event.details['browser']['address'])

					event_location = clicked_table.cell(clicked_counter,2)
					# Get the location data and add to results row
					# This is based on the IP address pulled from the browser for this event
					# Start by getting the coordinates from GeoLite2
					mmdb_location = self.lookup_ip(event.details['browser']['address'])
					if not mmdb_location == None:
						mmdb_latitude, mmdb_longitude = mmdb_location['location']['latitude'], mmdb_location['location']['longitude']
						# Check if GoPhish's coordinates agree with these MMDB results
						event_location.text = "{}".format(self.compare_ip_coordinates(target.latitude, target.longitude, mmdb_latitude, mmdb_longitude, event.details['browser']['address']))
					else:
						print("[!] MMDB lookup returned no location results!")
						event_location.text = "IP address look-up returned None"

					# Parse the user-agent string and add browser and OS details to the results row
					user_agent = parse(event.details['browser']['user-agent'])

					browser = clicked_table.cell(clicked_counter, 3)
					browser_details = user_agent.browser.family + " " + user_agent.browser.version_string
					browser.text = browser_details
					self.browsers.append(browser_details)

					op_sys = clicked_table.cell(clicked_counter, 4)
					os_details = user_agent.os.family + " " + user_agent.os.version_string
					op_sys.text = os_details
					self.operating_systems.append(os_details)

					clicked_counter += 1

				if event.message == "Submitted Data" and event.email == target.email:
					submitted_table.add_row()
					timestamp = table.cell(counter, 0)
					temp = event.time.split('T')
					timestamp.text = temp[0] + " " + temp[1].split('.')[0]

					ip_add = submitted_table.cell(submitted_counter, 1)
					ip_add.text = event.details['browser']['address']

					event_location = submitted_table.cell(submitted_counter, 2)
					mmdb_location = self.lookup_ip(event.details['browser']['address'])
					if not mmdb_location == None:
						mmdb_latitude, mmdb_longitude = mmdb_location['location']['latitude'], mmdb_location['location']['longitude']
						# Check if GoPhish's coordinates agree with these MMDB results
						event_location.text = "{}".format(self.compare_ip_coordinates(target.latitude, target.longitude, mmdb_latitude, mmdb_longitude))
					else:
						result += "IP address look-up returned None"

					# Parse the user-agent string and add browser and OS details to the results row
					user_agent = parse(event.details['browser']['user-agent'])

					browser = submitted_table.cell(submitted_counter, 3)
					browser_details = user_agent.browser.family + " " + user_agent.browser.version_string
					browser.text = browser_details

					op_sys = submitted_table.cell(submitted_counter, 4)
					os_details = user_agent.os.family + " " + user_agent.os.version_string
					op_sys.text = "{}".format(os_details)

					data = submitted_table.cell(submitted_counter, 5)
					data_payload = events.details # TODO: Test with submitted data for this
					data.text = "{}".format(data_payload.group())

					submitted_counter += 1

		d.add_page_break()

		# End of the detailed results and the beginning of browser, location, and OS stats
		d.add_heading("Statistics", 1)
		p = d.add_paragraph("The following table shows the browsers seen:")
		# Create browser table
		browser_table = d.add_table(rows=1, cols=2, style="GoReport")
		set_column_width(browser_table.columns[0], Cm(7.24))
		set_column_width(browser_table.columns[1], Cm(3.35))

		header1 = browser_table.cell(0,0)
		header1.text = ""
		header1.paragraphs[0].add_run("Browser", "Cell Text").bold = True

		header2 = browser_table.cell(0,1)
		header2.text =""
		header2.paragraphs[0].add_run("Seen", "Cell Text").bold = True

		p = d.add_paragraph("\nThe following table shows the operating systems seen:")

		# Create OS table
		os_table = d.add_table(rows=1, cols=2, style="GoReport")
		set_column_width(browser_table.columns[0], Cm(7.24))
		set_column_width(browser_table.columns[1], Cm(3.35))

		header1 = os_table.cell(0,0)
		header1.text = ""
		header1.paragraphs[0].add_run("Operating System", "Cell Text").bold = True

		header2 = os_table.cell(0,1)
		header2.text =""
		header2.paragraphs[0].add_run("Seen", "Cell Text").bold = True

		p = d.add_paragraph("\nThe following table shows the locations seen:")

		# Create geo IP table
		location_table = d.add_table(rows=1, cols=2, style="GoReport")
		set_column_width(browser_table.columns[0], Cm(7.24))
		set_column_width(browser_table.columns[1], Cm(3.35))

		header1 = location_table.cell(0,0)
		header1.text = ""
		header1.paragraphs[0].add_run("Location", "Cell Text").bold = True

		header2 = location_table.cell(0,1)
		header2.text =""
		header2.paragraphs[0].add_run("Visits", "Cell Text").bold = True

		p = d.add_paragraph("\nThe following table shows the IP addresses captured:")

		# Create IP address table
		ip_add_table = d.add_table(rows=1, cols=2, style="GoReport")
		set_column_width(browser_table.columns[0], Cm(7.24))
		set_column_width(browser_table.columns[1], Cm(3.35))

		header1 = ip_add_table.cell(0,0)
		header1.text = ""
		header1.paragraphs[0].add_run("IP Address", "Cell Text").bold = True

		header2 = ip_add_table.cell(0,1)
		header2.text =""
		header2.paragraphs[0].add_run("Seen", "Cell Text").bold = True

		# Counters are used here again to track rows
		counter = 1
		# Counter is used to count all elements in the lists to create a unique list with totals
		counted_browsers = Counter(self.browsers)
		for key, value in counted_browsers.items():
			browser_table.add_row()
			cell = browser_table.cell(counter, 0)
			cell.text = "{}".format(key)

			cell = browser_table.cell(counter, 1)
			cell.text = "{}".format(value)
			counter += 1

		counter = 1
		counted_os = Counter(self.operating_systems)
		for key, value in counted_os.items():
			os_table.add_row()
			cell = os_table.cell(counter, 0)
			cell.text = "{}".format(key)

			cell = os_table.cell(counter, 1)
			cell.text = "{}".format(value)
			counter += 1

		counter = 1
		counted_locations = Counter(self.locations)
		for key, value in counted_locations.items():
			location_table.add_row()
			cell = location_table.cell(counter, 0)
			cell.text = "{}".format(key)

			cell = location_table.cell(counter, 1)
			cell.text = "{}".format(value)
			counter += 1

		counter = 1
		counted_ip_addresses = Counter(self.ip_addresses)
		for key, value in counted_ip_addresses.items():
			ip_add_table.add_row()
			cell = ip_add_table.cell(counter, 0)
			cell.text = "{}".format(key)

			cell = ip_add_table.cell(counter, 1)
			cell.text = "{}".format(value)
			counter += 1

		# Finalize document and save it as the value of output_word_report
		d.save("{}".format(self.output_word_report))
		print("[+] Done! Check \"{}\" for your results.".format(self.output_word_report))

if __name__ == '__main__':
	gophish = GPCampaign()
	gophish.run()
