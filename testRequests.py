#!/usr/bin/env python

################################
#
# testRequests.py
#
#  Script to test the time and size per event of
#  requests in McM. Prepares results in a CSV file
#  that can be used by manageRequests.py
#
#  author: David G. Sheffield (Rutgers)
#  maintainer: Jose Ruiz (Vanderbilt)
#
################################

import sys
import os
import subprocess
import argparse
import csv
import re
import glob
import time
import math
sys.path.append('/afs/cern.ch/cms/PPD/PdmV/tools/McM/')
from rest import * # Load class to access McM
from requestClass import * # Load class to store request information

# Regexes
re_filtereff = re.compile("Filter efficiency.*=.*= (?P<n1>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?) \+- (?P<n2>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?).*")
#re_filtereff = re.compile("Filter efficiency.*=.*= (?P<n1>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?) \+- (?P<n2>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?).*\[TO BE USED IN MCM\]")
re_matcheff = re.compile("Matching efficiency = (?P<n1>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?) \+/- (?P<n2>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?).*\[TO BE USED IN MCM\]")
re_totalevents = re.compile("<TotalEvents>(\d*)</TotalEvents>")
re_eventsran = re.compile('(\d*) events were ran')
re_totalsize = re.compile('<Metric Name="Timing-tstoragefile-write-totalMegabytes" Value="(\d*\.\d*)"/>')
re_totalsize2 = re.compile("total (\d*)K")
re_jobTime = re.compile('<Metric Name="(?:TotalJobCPU|TotalJobTime)" Value="(\d*\.\d*)"/>')
re_avgEventTime = re.compile('<Metric Name="(?:AvgEventCPU|AvgEventTime)" Value="(\d*\.\d*)"/>')

re_xml_totalevents = re.compile("<TotalEvents>(\d*)</TotalEvents>")
re_xml_totalsize = re.compile('<Metric Name="Timing-tstoragefile-write-totalMegabytes" Value="(\d*\.\d*)"/>')
re_xml_jobTime = re.compile('<Metric Name="(?:TotalJobCPU|TotalJobTime)" Value="(\d*\.\d*)"/>')
re_xml_avgEventTime = re.compile('<Metric Name="(?:AvgEventCPU|AvgEventTime)" Value="(\d*\.\d*)"/>')

def getArguments():
    parser = argparse.ArgumentParser(description='Test McM requests.')

    # Command line flags
    parser.add_argument('-i', '--ids', dest='ids', help=
                        'List of PrepIDs to be tested. Separate range by >.')
    parser.add_argument('-f', '--extract', action='store_true', help='Extract test results')
    parser.add_argument('-b', '--bsub', dest='bsub', action='store_true', help='Use bsub instead of condor')
    parser.add_argument('-n', dest='nEvents', help='Number of events to test.')
    parser.add_argument('-d', '--dev', action='store_true', help='Use dev instance of MCM')
    parser.add_argument('-D', '--test_dir', type=str, default='test', help='Test directory')
    parser.add_argument("--keep_root", action="store_true", help="Keep ROOT files from tests")

    args_ = parser.parse_args()
    return args_

def fillIDRange(pwg, campaign, first, last):
    first = int(first)
    last = int(last)
    requests = []
    if first > last:
        print "Error: PrepID range out of order. {0}-{1}-{2:05d} > {0}-{1}-{3:05d}".format(
            pwg, campaign, first, last)
        sys.exit(4)

    for number in range(first, last+1):
        tmpReq = Request()
        tmpReq.setPrepId("{0}-{1}-{2:05d}".format(pwg, campaign, number))
        requests.append(tmpReq)
    return requests

def parseIDList(compactList):
    splitList = compactList.split(',')
    requests = []
    for subList in splitList:
        splitSubList = subList.split('-')
        if len(splitSubList) == 3:
            tmpReq = Request()
            tmpReq.setPrepId(subList)
            requests.append(tmpReq)
        elif len(splitSubList) == 4:
            requests = requests + fillIDRange(splitSubList[0], splitSubList[1],
                                              splitSubList[2], splitSubList[3])
        elif len(splitSubList) == 6:
            if splitSubList[0] != splitSubList[3]:
                print "Error: PrepID range must be for the same PWG."
                sys.exit(4)
            if splitSubList[1] != splitSubList[4]:
                print "Error: PrepID range must be for the same campaign."
                sys.exit(4)
            requests = requests + fillIDRange(splitSubList[0], splitSubList[1],
                                              splitSubList[2], splitSubList[5])
        else:
            print "Error: Poorly formed PrepID list."
            print "Exiting with status 3."
            sys.exit(3)
    return requests

def getTestScript(PrepID, nEvents, use_bsub=False, use_dev=False):
    request_type = "requests"
    if "chain_" in PrepID:
        request_type = "chained_requests"

    get_test = ""
    scriptFile = "{}.sh".format(PrepID)

    if use_dev:
        dev_string = "-dev"
    else:
        dev_string = ""

    if nEvents is None:
        get_test =  "curl -s --insecure \
https://cms-pdmv{}.cern.ch/mcm/public/restapi/{}/get_test/{} -o {}".format(
            dev_string, request_type, PrepID, scriptFile)
    else:
        # add "/N" to end of URL to get N events
        get_test =  "curl -s --insecure \
https://cms-pdmv{}.cern.ch/mcm/public/restapi/{}/get_test/{}/{} -o {}".format(
            dev_string, request_type, PrepID, nEvents, scriptFile)
    print get_test
    subprocess.call(get_test, shell=True)

    if request_type == "chained_requests" and nEvents is not None:
        tmpScriptFile = "tmp{}".format(scriptFile)
        inputfile = open(scriptFile, 'r')
        outputfile = open(tmpScriptFile, 'w')
        for line in inputfile:
            outline = re.sub('(.*--eventcontent LHE.*-n) \d*( .*)',
                             r'\1 {0}\2'.format(nEvents), line)
            outline = re.sub('(.*--eventcontent DQM.*-n) \d*( .*)',
                             r'\1 {0}\2'.format(nEvents), outline)
            outline = re.sub('(.*--eventcontent RAWSIM.*-n) \d*( .*)',
                             r'\1 {0}\2'.format(nEvents), outline)
            outputfile.write(outline)
        inputfile.close()
        outputfile.close()
        os.rename(tmpScriptFile, scriptFile)

    subprocess.call("chmod 755 {}".format(scriptFile), shell=True)
    return

def submitToBatch(PrepId):
    batch_command = "bsub -q 8nh {0}.sh".format(PrepId)
    print batch_command
    output = subprocess.Popen(batch_command, stdout=subprocess.PIPE,
                              shell=True).communicate()[0]
    match = re.match('Job <(\d*)> is', output)
    jobID = match.group(1)
    return jobID

#def submitToCondor(PrepId, retry=0):
#    batch_command = "csub {}.sh -t workday -d test_{} --os SLCern6".format(PrepId, PrepId)
#    print batch_command
#    output = subprocess.Popen(batch_command, stdout=subprocess.PIPE,
#                              shell=True).communicate()[0]
#    print output
#    match = re.search('submitted to cluster (\d*)', output)
#    if not match:
#        print "[submitToCondor] ERROR : Couldn't find string 'submitted to cluster' in output line."
#        if retry > 3:
#            return -1
#        else:
#            return submitToCondor(PrepId, retry+1)
#    jobID = match.group(1)
#    return jobID

def submitManyToCondor(reqs, retry=0, keep_root=False):
    scripts = ["{}.sh".format(req.getPrepId()) for req in reqs]
    with open("test_many.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write("scripts=(" + " ".join(scripts) + ")\n")
        f.write("source ${scripts[$1]}\n")
        if not keep_root:
            f.write("mkdir $_CONDOR_SCRATCH_DIR/hide\n")
            f.write("mv $_CONDOR_SCRATCH_DIR/*root $_CONDOR_SCRATCH_DIR/hide\n")

    batch_command = "csub test_many.sh -t workday --queue_n {} -F {}".format(len(scripts), ",".join(scripts))
    # For RunII* jobs, use SLC6
    if "RunIISummer15" in reqs[0].getPrepId() or "RunIIFall17" in reqs[0].getPrepId() or "RunIIFall18" in reqs[0].getPrepId():
        batch_command += " --os SLCern6"
    print batch_command
    output = subprocess.Popen(batch_command, stdout=subprocess.PIPE, shell=True).communicate()[0]
    print output
    match = re.search('submitted to cluster (\d*)', output)
    if not match:
        print "[submitToCondor] ERROR : Couldn't find string 'submitted to cluster' in output line."
        if retry > 3:
            return -1
        else:
            return submitManyToCondor(reqs, retry=retry+1, test_dir=test_dir)
    jobID = match.group(1)
    prepid_jobid_map = {}
    for i, req in enumerate(reqs):
        prepid_jobid_map[req.getPrepId()] = "{}.{}".format(jobID, i)
    return prepid_jobid_map


def createTest(compactPrepIDList, nEvents, use_bsub=False, use_dev=False, test_dir="test", keep_root=False):
    if os.path.isdir(test_dir):
        raise ValueError("Test directory {} already exists.".format(test_dir))

    cwd = os.getcwd()
    os.system("mkdir -pv {}".format(test_dir))
    os.chdir(test_dir)

    requests = parseIDList(compactPrepIDList)

    csvfile = csv.writer(open("testjobs.csv", 'w'))
    csvfile.writerow(['PrepId', 'JobId'])

    print "Testing {0} requests".format(len(requests))
    #if not use_bsub:
    #    os.system("csub_tar --cmssw")
    failed = []
    for req in requests:
        getTestScript(req.getPrepId(), nEvents, use_dev=use_dev)

    prepid_jobid_map = {}
    if use_bsub:
        for req in requests:
            jobID = submitToBatch(req.getPrepId())
            prepid_jobid_map[req.getPrepId()] = jobID
    else:
        prepid_jobid_map = submitManyToCondor(requests, keep_root=keep_root)
        if prepid_jobid_map == -1:
            print "[createTest] ERROR : Condor submission failed!"
            sys.exit(1)

    for req in requests:
        req.setJobID(prepid_jobid_map[req.getPrepId()])
        searched = re.search('chain_', req.getPrepId())
        if searched is None:
            csvfile.writerow([req.getPrepId(), req.getJobID(), "", ""])
        else:
            mcm = McM(dev=use_dev) # Get McM connection
            mcm_req = mcm.get('chained_requests', req.getPrepId())
            wmLHEPrepId = mcm_req['chain'][0]
            GSPrepId = mcm_req['chain'][1]
            csvfile.writerow([wmLHEPrepId, req.getJobID(), "", ""])
            csvfile.writerow([GSPrepId, req.getJobID(), "", ""])

    os.chdir(cwd)
    return

def exitDuplicateField(file_in_,field_):
    print "Error: File {0} contains multiple instances of the field {1}".format(
        file_in_, field_)
    sys.exit(5)

def getFields(csvfile):
    # List of indices for each field in CSV file
    list = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
             -1, -1, -1, -1, -1, -1, -1, -1]
    header = csv.reader(csvfile).next()
    for ind, field in enumerate(header):
        field = field.lower()
        if field in ['dataset name', 'dataset']:
            #ensure no duplicate fields
            if list[0] > -1:
                exitDuplicateField(file_in_, "Dataset name")
            list[0] = ind
        elif field in ['eos', 'mcdbid']:
            if list[1] > -1:
                exitDuplicateField(file_in_, "EOS")
            list[1] = ind
        elif field in ['cross section [pb]', 'cross section',
                       'cross section (pb)', 'cs', 'cs [pb]', 'cs (pb)', 'xsec',
                       'xsec [pb]', 'xsec (pb)']:
            if list[2] > -1:
                exitDuplicateField(file_in_, "Cross section [pb]")
            list[2] = ind
        elif field in ['total events', 'events', 'number of events']:
            if list[3] > -1:
                exitDuplicateField(file_in_, "Total events")
            list[3] = ind
        elif field in ['fragment name', 'generator fragment name', 'fragment']:
            if list[4] > -1:
                exitDuplicateField(file_in_, "Fragment name")
            list[4] = ind
        elif field in ['time per event [s]', 'time per event',
                       'time per event (s)', 'time', 'time [s]', 'time (s)']:
            if list[5] > -1:
                exitDuplicateField(file_in_, "Time per event [s]")
            list[5] = ind
        elif field in ['size per event [kb]', 'size per event',
                       'size per event (kb)', 'size', 'size [kb]', 'size (kb)']:
            if list[6] > -1:
                exitDuplicateField(file_in_, "Size per event [kB]")
            list[6] = ind
        elif field in ['tag', 'fragment tag', 'sha', 'sha-1']:
            if list[7] > -1:
                exitDuplicateField(file_in_, "Fragment tag")
            list[7] = ind
        elif field in ['generator', 'generators']:
            if list[8] > -1:
                exitDuplicateField(file_in_, "Generator")
            list[8] = ind
        elif field in ['filter efficiency']:
            if list[9] > -1:
                exitDuplicateField(file_in_, "Filter efficiency")
            list[9] = ind
        elif field in ['filter efficiency error']:
            if list[10] > -1:
                exitDuplicateField(file_in_, "Filter efficiency error")
            list[10] = ind
        elif field in ['match efficiency']:
            if list[11] > -1:
                exitDuplicateField(file_in_, "Match efficiency")
            list[11] = ind
        elif field in ['match efficiency error']:
            if list[12] > -1:
                exitDuplicateField(file_in_, "Match efficiency error")
            list[12] = ind
        elif field in ['pwg']:
            if list[13] > -1:
                exitDuplicateField(file_in_, "PWG")
            list[13] = ind
        elif field in ['campaign', 'member of campaign']:
            if list[14] > -1:
                exitDuplicateField(file_in_, "Member of campaign")
            list[14] = ind
        elif field in ['prepid']:
            if list[15] > -1:
                exitDuplicateField(file_in_, "PrepID")
            list[15] = ind
        elif field in ['sequences customise', 'sequences customize']:
            if list[16] > -1:
                exitDuplicateField(file_in_, "Sequences customise")
            list[16] = ind
        elif field in ['process string']:
            if list[17] > -1:
                exitDuplicateField(file_in_, "Process string")
            list[17] = ind
        elif field in ['gridpack location', 'gridpack']:
            if list[18] > -1:
                exitDuplicateField(file_in_, "Gridpack location")
            list[18] = ind
        elif field in ['gridpack cards url', 'cards url',
                       'gridpack cards location', 'cards location']:
            if list[19] > -1:
                exitDuplicateField(file_in_, "Gridpack cards URL")
            list[19] = ind
        elif field in ['jobid']:
            if list[20] > -1:
                exitDuplicateField(file_in_, "JobId")
            list[20] = ind
        elif field in ['notes']:
            if list[21] > -1:
                exitDuplicateField(file_in_, "Notes")
            list[21] = ind
        elif field in ['mcm tag', 'mcm tags']:
            if list[22] > -1:
                exitDuplicateField(file_in_, "McM tags")
            list[22] = ind
        elif field in ['sequences beamspot']:
            if list[23] > -1:
                exitDuplicateField(file_in_, "Sequences beamspot")
            list[23] = ind
        elif field in ['sequences magField']:
            if list[24] > -1:
                exitDuplicateField(file_in_, "Sequences magField")
            list[24] = ind
        elif field in ['local gridpack location', 'Local lhe', 'lhe']:
            continue
        else:
            print "Error: The field {0} is not valid.".format(field)
            sys.exit(6)

    return list

def fillFields(csvfile, fields):
    requests = [] # List containing request objects
    num_requests = 0
    for row in csv.reader(csvfile):
        if row[0].startswith("#"):
            continue
        num_requests += 1
        tmpReq = Request()
        if fields[0] > -1:
            tmpReq.setDataSetName(row[fields[0]])
        if fields[1] > -1:
            tmpReq.setMCDBID(row[fields[1]])
        if fields[2] > -1:
            tmpReq.setCS(row[fields[2]])
        if fields[3] > -1:
            tmpReq.setEvts(row[fields[3]])
        if fields[14] > -1:
            campaign = row[fields[14]]
            tmpReq.setCamp(campaign)
        if fields[4] > -1:
            tmpReq.setFrag(formatFragment(row[fields[4]],campaign))
        if fields[5] > -1 and row[fields[5]] != "":
            tmpReq.setTime(row[fields[5]])
        if fields[6] > -1 and row[fields[6]] != "":
            tmpReq.setSize(row[fields[6]])
        if fields[7] > -1:
            tmpReq.setTag(row[fields[7]])
        if fields[8] > -1:
            tmpReq.setGen(row[fields[8]].split(" ")) # Multiple generators separated by spaces
        if fields[9] > -1:
            tmpReq.setFiltEff(row[fields[9]])
        if fields[10] > -1:
            tmpReq.setFiltEffErr(row[fields[10]])
        if fields[11] > -1:
            tmpReq.setMatchEff(row[fields[11]])
        if fields[12] > -1:
            tmpReq.setMatchEffErr(row[fields[12]])
        if fields[13] > -1:
            tmpReq.setPWG(row[fields[13]])
        if fields[15] > -1:
            tmpReq.setPrepId(row[fields[15]])
        if fields[16] > -1:
            tmpReq.setSequencesCustomise(row[fields[16]])
        if fields[17] > -1:
            tmpReq.setProcessString(row[fields[17]])
        if fields[18] > -1:
            if fields[19] > -1:
                tmpReq.setMcMFrag(createLHEProducer(row[fields[18]],
                                                    row[fields[19]]))
            else:
                tmpReq.setMcMFrag(createLHEProducer(row[fields[18]], ""))
        if fields[20] > -1:
            tmpReq.setJobID(row[fields[20]])
        if fields[21] > -1:
            tmpReq.setNotes(row[fields[21]])
        if fields[22] > -1:
            tmpReq.setMcMTag(row[fields[22]].split(" "))
        if fields[23] > -1:
            tmpReq.setSequencesBeamspot(row[fields[23]])
        if fields[24] > -1:
            tmpReq.setSequencesMagField(row[fields[24]])
        requests.append(tmpReq)
    return requests, num_requests

def writeResultsCSV(csvfile, requests, skip=[]):
    csvWriter = csv.writer(csvfile)
    csvWriter.writerow(['PrepId', 'JobId', 'Time per event [s]',
                        'Size per event [kB]', 'match efficiency', 'filter efficiency'])

    for req in requests:
        if req.getPrepId() in skip:
            continue
        if req.getTime() < 0:
            continue
        timePerEvent = ""
        if req.useTime(): 
            timePerEvent = req.getTime()
        sizePerEvent = ""
        if req.useSize(): 
            sizePerEvent = req.getSize()
        matchEff = ""
        if req.useMatchEff(): 
            matchEff = req.getMatchEff()
        filterEff="1.0"
        if req.useFiltEff():
            filterEff= req.getFiltEff()

        csvWriter.writerow([req.getPrepId(), req.getJobID(), timePerEvent,
                            sizePerEvent, matchEff, filterEff])
    return

def getTimeSizeFromFile(stdoutFile, iswmLHE, use_bsub=False, stderrFile=None, xmlFile=None):
    totalSize = 0
    jobTimeCandidates = []
    avgEventTimeCandidates = []
    #nEventsCandidates = []
    totalEvents = -1
    eventsRan = -1
    XsBeforeMatch = 0
    XsAfterMatch = 0
    matchEff = 1.0
    matchEffErr = 0.0
    filterEff = 1.0
    filterEffErr = 0.0

    filesToParse = [stdoutFile]
    if stderrFile:
        filesToParse.append(stderrFile)
    for fileToParse in filesToParse:
        print "Reading {}".format(fileToParse)
        fileContents = open(fileToParse, 'r')
        for line in fileContents:
            match_totalevents = re_totalevents.search(line)
            if match_totalevents is not None:
                totalEvents = float(match_totalevents.group(1))
                continue

            match_eventsran = re_eventsran.search(line)
            if match_eventsran is not None:
                eventsRan = float(match_eventsran.group(1))
                continue

            match_totalsize = re_totalsize.search(line)
            if match_totalsize is not None:
                totalSize = float(match_totalsize.group(1))
                continue

            match_totalsize2 = re_totalsize2.search(line)
            if match_totalsize2 is not None:
                totalSize = float(match_totalsize2.group(1))
                continue

            match_matcheff = re_matcheff.search(line)
            if match_matcheff is not None:
                matchEff = float(match_matcheff.group("n1"))
                matchEffErr = float(match_matcheff.group("n2"))
                if not iswmLHE and matchEff != 1.:
                    raise ValueError("Found matching efficiency of {} for a GS job, which is not supposed to have matching! Something is wrong.")
                continue

            match_filtereff = re_filtereff.search(line)
            if match_filtereff is not None:
                print("Taking filter efficiency from:")
                print(line)
                filterEff = float(match_filtereff.group("n1"))
                filterEffErr = float(match_filtereff.group("n2"))
                continue

            match_jobTime = re_jobTime.search(line)
            if match_jobTime is not None:
                jobTimeCandidates.append(float(match_jobTime.group(1)))
                continue

            match_avgEventTime = re_avgEventTime.search(line)
            if match_avgEventTime is not None:
                avgEventTimeCandidates.append(float(match_avgEventTime.group(1)))

    if xmlFile:
        with open(xmlFile) as xmlContents:
            for line in xmlContents:
                match_totalevents = re_xml_totalevents.search(line)
                if match_totalevents is not None:
                    totalEvents = float(match_totalevents.group(1))
                    continue

                match_jobTime = re_xml_jobTime.search(line)
                if match_jobTime is not None:
                    jobTimeCandidates.append(float(match_jobTime.group(1)))
                    continue

                match_totalsize = re_xml_totalsize.search(line)
                if match_totalsize is not None:
                    totalSize = float(match_totalsize.group(1))
                    continue

                match_avgEventTime = re_xml_avgEventTime.search(line)
                if match_avgEventTime is not None:
                    avgEventTimeCandidates.append(float(match_avgEventTime.group(1)))

    # Fix for randomized parameters requests: matching efficiency is not computed, because requests are GS not wmLHEGS!
    if totalEvents == -1:
        raise ValueError("Didn't find total number of events from log file! I.e. <TotalEvents>###</TotalEvents>")

    totalEff = totalEvents / eventsRan
    totalEffErr = math.sqrt(totalEff * (1. - totalEff) / eventsRan)
    if abs(totalEff - (matchEff * filterEff)) > 0.05:
        print "WARNING : Total efficiency {} doesn't match matchEff*filterEff = {}*{} = {}.".format(totalEff, matchEff, filterEff, matchEff * filterEff)
        if matchEff == 1.:
            print "WARNING : I'm guessing this is randomized parameters, and matchEff just isn't in the log file. Setting matchEff = totalEff / filterEff"
            matchEff = totalEff / filterEff
            matchEffErr = matchEff * math.sqrt((totalEffErr / totalEff)**2 + (filterEffErr / filterEff)**2)

    # Size / event calculation
    if totalEvents != 0:
        sizePerEvent = totalSize * 1024.0 / totalEvents
    else:
        sizePerEvent = -1

    timePerEventCandidates = []
    for jobTime in jobTimeCandidates:
        timePerEventCandidates.append(jobTime / totalEvents)
    for avgEventTime in avgEventTimeCandidates:
        timePerEventCandidates.append(avgEventTime)
    timePerEvent = max(timePerEventCandidates)

    print "Results from file(s) {}:".format(", ".join(filesToParse))
    print "\tTime/event = {}".format(timePerEvent)
    print "\tSize/event = {}".format(sizePerEvent)
    print "\tMatching efficiency = {} +/- {}".format(matchEff, matchEffErr)
    print "\tFilter efficiency = {} +/- {}".format(filterEff, filterEffErr)
    if filterEffErr / filterEff > 0.1:
        print "WARNING: Filter efficiency error {:.3f} > 10%! Consider running more events.".format(filterEffErr / filterEff)
    return timePerEvent, sizePerEvent, matchEff, matchEffErr, filterEff, filterEffErr

def getTimeSize(requests, use_bsub=False, force_update=False):
    number_complete = 0
    successful_jobs = []
    failed_jobs = []
    for req in requests:
        if not req.useTime() or not req.useSize() or force_update:
            if use_bsub:
                stdoutFile = "LSFJOB_{0}/STDOUT".format(req.getJobID())
                stderrFile = None
            else:
                stdoutCandidates = glob.glob("{}/*{}*.stdout".format(os.getcwd(), req.getJobID()))
                if len(stdoutCandidates) == 0:
                    print "[getTimeSize] WARNING : Didn't find output file for request {}".format(req.getJobID())
                    failed_jobs.append(req.getPrepId())
                    continue
                    #sys.exit(1)
                elif len(stdoutCandidates) >= 1:
                    # Multiple attempts: use latest
                    stdoutCandidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                stdoutFile = stdoutCandidates[0]

                stderrCandidates = glob.glob("{}/*{}*.stderr".format(os.getcwd(), req.getJobID()))
                if len(stderrCandidates) == 0:
                    print "[getTimeSize] WARNING : Didn't find output stderr file for request {}".format(req.getJobID())
                elif len(stderrCandidates) >= 1:
                    # Multiple attempts: use latest
                    stderrCandidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                stderrFile = stderrCandidates[0]

                xmlCandidates = glob.glob("{}/*{}*xml".format(os.getcwd(), req.getPrepId()))
                if len(xmlCandidates) == 0:
                    print "[getTimeSize] WARNING : Didn't find output xml file for prepid {}".format(req.getPrepId())
                elif len(xmlCandidates) >= 1:
                    # Multiple attempts: use latest
                    xmlCandidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                xmlFile = xmlCandidates[0]

            if os.path.exists(stdoutFile):
                number_complete += 1
                iswmLHE = False
                searched = re.search('wmLHE', req.getPrepId())
                if searched is not None:
                    iswmLHE = True
                try:
                    timePerEvent, sizePerEvent, matchEff, \
                    matchEffErr, filterEff, filterEffErr = getTimeSizeFromFile(
                        stdoutFile, 
                        iswmLHE, 
                        use_bsub=use_bsub, 
                        stderrFile=stderrFile,
                        xmlFile=xmlFile)
                except ValueError as error:
                    print error
                    timePerEvent = -1
                    sizePerEvent = -1
                    matchEff = -1
                    matchEffErr = 0
                    filterEff = -1
                    filterEffErr = 0

                if timePerEvent == 0:
                    print "[getTimeSize] WARNING : timePerEvent=0 for request {}. Try resubmitting.".format(req.getPrepId())
                    failed_jobs.append(req.getPrepId())
                    continue
                elif timePerEvent < 0:
                    print "[getTimeSize] WARNING : timePerEvent not found for request {}. Try resubmitting.".format(req.getPrepId())
                    failed_jobs.append(req.getPrepId())
                    continue
                else:
                    successful_jobs.append(req.getPrepId())                    

                req.setTime(timePerEvent)
                req.setSize(sizePerEvent)
                req.setMatchEff(matchEff)
                req.setMatchEffErr(matchEffErr)
                if filterEff != 1:
                    req.setFiltEff(filterEff)
                    req.setFiltEffErr(filterEffErr)
        else:
            number_complete += 1

    if number_complete == len(requests):
        print "Extracted info for all {0} requests.".format(len(requests))
    else:
        print "Extracted info for {0} of {1} requests. {2} requests remain.".format(
            number_complete, len(requests), len(requests) - number_complete)
    return successful_jobs, failed_jobs

def extractTest(test_dir, force_update=False, use_bsub=False):
    cwd = os.getcwd()
    os.chdir(test_dir)
    inputCsvFile = open("testjobs.csv", 'r') # Open CSV file
    fields = getFields(inputCsvFile)  # Get list of field indices
    # Fill list of request objects from CSV file and get number of requests
    requests, num_requests = fillFields(inputCsvFile, fields)
    inputCsvFile.close()
    successful_jobs, failed_jobs = getTimeSize(requests, force_update=force_update, use_bsub=use_bsub)

    outputCsvFile = open("testresults.csv", 'w')
    writeResultsCSV(outputCsvFile, requests, skip=failed_jobs)

    os.chdir(cwd)

    if len(failed_jobs) >= 1:
        print "WARNING: some jobs failed! You should either resubmit, or guess the parameters from the successful jobs."
        print "Successful jobs:"
        print successful_jobs
        print "Failed jobs:"
        print failed_jobs
    return

def main():
    args = getArguments() # Setup flags and get arguments
    if args.ids and args.extract:
        print "Error: Cannot use both -i and -f."
        sys.exit(1)
    elif args.ids:
        createTest(args.ids, args.nEvents, use_bsub=args.bsub, use_dev=args.dev, test_dir=args.test_dir, keep_root=args.keep_root)
    elif args.extract:
        extractTest(args.test_dir, use_bsub=args.bsub)
    else:
        print "Error: Must use either -i or -f."
        sys.exit(2)

if __name__ == '__main__':
    main()
