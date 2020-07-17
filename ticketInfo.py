import sys
sys.path.append('/afs/cern.ch/cms/PPD/PdmV/tools/McM/')
from rest import McM

'''
	Parse prepids in list format that MCM returns.
	Example: u'requests': [[u'EXO-RunIIFall18GS-03862', u'EXO-RunIIFall18GS-03875'], u'EXO-RunIIFall18GS-03860']
	Element are either single prepids or ranges.
'''
import re
re_prepid = re.compile("EXO-(?P<campaign>RunII[A-Za-z0-9]*)-(?P<prepidn>\d\d\d\d\d)")
def parse_prepids(prepid_list):
	print("DEBUG : parsing prepid list:")
	print(prepid_list)
	prepid_plist = []
	for prepid_obj in prepid_list:
		print("DEBUG : object = {}".format(prepid_obj))
		if isinstance(prepid_obj, list):
			if not len(prepid_obj) == 2:
				print(prepid_obj)
				raise ValueError("Prepid list has !=2 objects (see previous line)")
			prepid_start = prepid_obj[0]
			print("DEBUG : prepid_start = {}".format(prepid_start))
			match_start = re_prepid.search(prepid_start)
			prepidn_start = int(match_start.group("prepidn"))
			campaign = match_start.group("campaign")
			print("DEBUG : re prepidn_start = {}, campaign = {}".format(prepidn_start, campaign))

			prepid_end = prepid_obj[1]
			match_end = re_prepid.search(prepid_end)
			prepidn_end = int(match_end.group("prepidn"))

			for prepidn in range(prepidn_start, prepidn_end+1):
				prepid_plist.append("EXO-{}-{}".format(campaign, '{0:05d}'.format(prepidn)))
		elif isinstance(prepid_obj, str) or isinstance(prepid_obj, unicode):
			prepid_plist.append(str(prepid_obj))
		else:
			print(type(prepid_obj))
			raise ValueError("Unknown type found in prepid list: {}".format(prepid_obj))
	print("DEBUG : Parsed list = ")
	print(prepid_plist)
	return prepid_plist

import argparse
parser = argparse.ArgumentParser(description="Get ticket information")
parser.add_argument("ticket", type=str, help="Ticket")
args = parser.parse_args()
ticket = args.ticket

mcm = McM(dev=False)
ticket_info = mcm.get('mccms', ticket)
import pprint
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(ticket_info)

prepids = parse_prepids(ticket_info["requests"])
total_events = 0
for prepid in prepids:
	print("Prepid {}".format(prepid))
	request = mcm.get("requests", prepid)
	print(request)
	total_events += request["total_events"]
print("Total events = {}".format(total_events))

