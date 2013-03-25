#!/usr/bin/env python

MAX = 999
MAX = 4

# Walk the CSV skipping various header lines
# Line 1 is bogus, the header fields are on line 2
# Map header field names to RedMine custom field IDs:
# note that the sloppy data here ("60 GB" instead of "60",
# "Intermal" instead of "Internal") means we can't used numeric or
# controlled vocabularies (lists) in our custom field defs.
# Inject the entry with an HTTP POST

# TODO:
# - after initial slurp, we should add follow-up posts based on Questions, Answers, etc.

# Upon creation we get a record back with custom fields filled in, with id:
#
# {"issue":
#  {"id":18,
#   "project": {"id":3,
#               "name":"App Migration"},
#   "tracker":{"id":2,"name":"Feature"},
#   "status":{"id":1,"name":"New"},
#   "priority":{"id":2,"name":"Normal"},
#   "author":{"id":4,"name":"Chris Shenton"},
#   "assigned_to":{"id":4,"name":"Chris Shenton"},
#   "category":{"id":1,"name":"NewCat"},
#   "subject":"www.example.com",
#   "description":"Some description here",
#   "start_date":"2013-03-16",
#   "done_ratio":0,
#   "spent_hours":0.0,
#   "custom_fields":[
#       {"id":1,"name":"Operating System","value":"LUNIX"},
#       {"id":2,"name":"Database","value":"WHORACLE"},
#       {"id":3,"name":"Web Server","value":"NCSA"},
#       {"id":4,"name":"App Server","value":"Railo"},
#       {"id":5,"name":"Memory (GB)","value":"1"},
#       {"id":6,"name":"Disk (GB)","value":"5"},
#       {"id":11,"name":"Internal/External","value":"External"},
#       {"id":12,"name":"URL","value":"http://example.com"},
#       {"id":13,"name":"Tech Stack","value":"cases of beer"}],
#   "created_on":"2013-03-16T16:33:10Z",
#   "updated_on":"2013-03-16T16:33:10Z"}
# }

import base64
import csv
import httplib
import json
import logging
import pprint
import urllib2

logging.basicConfig(level=logging.INFO)

def get_description(row):
    """Return text from various fields to populate Description field.
    """
    format = """
*Purpose:* %(Purpose of App)s

*Customer Org:* %(Customer Organization)s

*POC:* %(POC)s

*Feature Set:* %(Feature Set)s

*External Dependencies:* %(External Dependencies)s

*Bandwidth:* %(Bandwidth (per month))s

*Location:* %(Application Location (AWS, Sungard))s

*Notes from 03/05 Meeting:* %(NOTES from 03/05 Meeting)s

*Questions:* %(?s)s

*Answers:* %(Answers)s
"""
    try: 
        result = format % row
    except KeyError, e:
        import pdb; pdb.set_trace()
    return format % row

CSV = 'Application_Triage_030513_Appendix B - Sheet1.csv'

from redpush_api_key import API_KEY

REDMINE_URL = 'http://ec2-50-17-164-89.compute-1.amazonaws.com/redmine/issues.json'

BASE_ISSUE = {'project_id': 'app-migration',
              'tracker_id': 3,    # Support
              }

stock_map = {
    'Name of Application': 'subject',
    '...': 'description'
    }

custom_map = {
    # These aren't in the spread uniquely or at all :-(
    # '': (1, 'Operating System'),
    # '': (2, 'Database'),
    # '': (3, 'Web Server'),
    # '': (4, 'App Server'),
    # '': (5, 'Memory (GB)'),
    'URL'                                                   : (12, 'URL'),
    'Technology Stack (E.g. Apache, Perl, Myql, Linux)'     : (13, 'Tech Stack'),
    'Disk Space, GB/instance'                               : (14, 'Disk (GB)'),
    'Internal or External?'                                 : (15, 'Internal/External'),
    'Application Responsible Party'                         : (16, 'Responsible Party'),
    }

with open(CSV, 'rb') as f:
    reader = csv.reader(f)
    meta = reader.next()
    headers = reader.next()
    headers = [h.strip() for h in headers]
    reader = csv.DictReader(f, headers)
    for row in reader:
        if MAX < 1:
            break
        MAX = MAX - 1
        url = row['URL'].strip()
        app_name = row['Name of Application']
        if not url:
            logging.warning("Skipping non-url row app_name=%s" % app_name)
            continue
        issue = BASE_ISSUE
        issue.update({'subject': app_name})
        issue.update({'description': get_description(row)})
        custom_fields = []
        for key, (id, name) in custom_map.items():
            custom_fields.append({'id': id, 'name': name, 'value': row[key]})
        issue.update({'custom_fields': custom_fields})

        json_data = json.dumps({'issue': issue}) # need urllib.urlencode ?
        request = urllib2.Request(REDMINE_URL, json_data)
        request.add_header('X-Redmine-API-Key', API_KEY)
        request.add_header('Content-Type', 'application/json')
        logging.info(app_name)
        try:
            response = urllib2.urlopen(request) # PyOST data
        except urllib2.HTTPError, e:
            logging.error('e=%s: %s' % (e, app_name))
            logging.error('JSON: %s' % json_data)
        response.close()
