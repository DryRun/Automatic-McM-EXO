#!/usr/bin/env python
import os
import sys
import csv
import pickle
import math
sys.path.append("/afs/cern.ch/user/d/dryu/workspace/private/MCI/Automatic-McM-EXO")
sys.path.append("/afs/cern.ch/user/d/dryu/workspace/private/MCI/Automatic-McM-EXO/randomized_parameters")
from manageRequests import getFields
from request import RandomizedParameterRequest


if __name__ == "__main__":
  # Require CMSSW (the fragments are imported directly to extract the configurations)
  if not os.getenv("CMSSW_BASE"):
    print "ERROR : CMSSW is not setup."
    sys.exit(1)


  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("-s", "--spreadsheet", type=str, required=True, help="Path to spreadsheet")
  parser.add_argument("-n", "--name", type=str, required=True, help="Name of dataset")
  parser.add_argument("-c", "--campaign", type=str, required=True, help="Name of campaign")
  parser.add_argument("-f", "--overwrite", action="store_true", help="Overwrite existing files")
  args = parser.parse_args()

  # Determine if gridpacks are used
  use_gridpack = False
  with open(args.spreadsheet, 'rb') as spreadsheet:
    header_line = spreadsheet.readline()
    if "gridpack" in header_line.lower():
      use_gridpack = True

  output_dir = "{}_{}".format(args.name, args.campaign)
  os.system("mkdir -pv {}".format(output_dir))
  rp_request = RandomizedParameterRequest(dataset_name=args.name, campaign=args.campaign, output_dir=output_dir, overwrite=args.overwrite, use_gridpack=use_gridpack)
  min_nevents = 1.e20
  with open(args.spreadsheet, 'rb') as spreadsheet1:
    fields = getFields(spreadsheet1) # Dict {column name : column index}

  with open(args.spreadsheet, 'rb') as spreadsheet2:
    params = {}
    csv_reader = csv.reader(spreadsheet2)
    for i, row in enumerate(csv_reader):
      if i == 0:
        continue
      for field, index in fields.iteritems():
        params[field] = row[index]

      req_kwargs = {
        "grid_point_name":params["dataset"], 
        "fragment_path":params["fragment"], 
        "nevents":int(params["events"]), 
        "generator_name":params["generator"], 
      }
      if rp_request.type() == "gridpack":
        req_kwargs["gridpack_path"] = params["gridpack"]
      rp_request.add_request(**req_kwargs)

      if req_kwargs['nevents'] < min_nevents:
        min_nevents = req_kwargs['nevents']
    rp_request.finalize()

  # Compute the recommended number of events per LS. 
  # - For a given point, <nLS> = eventsPerPoint / eventsPerLS
  # - Want <10% variance on number of events => at least 100 LSes. So 100 < eventsPerPoint / eventsPerLS
  # - => eventsPerLS < eventsPerPoint / 100
  # - Finally, MCM requires 100 < eventsPerLS < 1000. 
  eventsPerLS = int(math.floor(min_nevents / 100))
  if eventsPerLS < 100:
    print "WARNING : Min nEvents = {} => eventsPerLS = {} is below 100".format(min_nevents, eventsPerLS)
    eventsPerLS = 100
  elif eventsPerLS > 1000:
    print "WARNING : Min nEvents = {} => eventsPerLS = {} is above 1000".format(min_nevents, eventsPerLS)
    evnetsPerLS = 1000

  eventsPerLS = min(max(100, eventsPerLS), 1000)

  # Create a dictionary with all the info needed for the MCM upload
  with open("{}/{}.py".format(output_dir, args.name), 'r') as fragment:
    fragment_str = fragment.read()

  request = {
    "pwg":"EXO",
    "member_of_campaign":args.campaign,
#    "mcdb_id":0,
    "dataset_name":args.name,
    "total_events":rp_request.total_nevents(),
    "fragment":fragment_str,
    "generators":["pythia"] if rp_request.type() == "pythia" else ["madgraph", "pythia"],
    "generator_parameters": [{'match_efficiency_error': 0.0,
                              'match_efficiency': 1.0,
                              'filter_efficiency': 1.0,
                              'version': 0,
                              'cross_section': 1.0,
                              'filter_efficiency_error': 0.0}],
    
  }
  with open("{}/{}.pkl".format(output_dir, args.name), 'w') as reqpkl:
    pickle.dump(request, reqpkl)
  print "\n*********************"
  print "RP request created. To upload to MCM:"
  print "uploadRPRequest.py {}/{}.pkl --eventsPerLS {} [-t tag] [--dev]".format(output_dir, args.name, eventsPerLS)
  print "*********************\n"
