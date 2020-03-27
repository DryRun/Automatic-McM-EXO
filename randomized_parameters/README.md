## Randomized parameters

A "randomized parameter" request generates a whole signal grid in one dataset. At the beginning of each lumisection (i.e. in beginLumiSection()), the job will select a new random grid point to generate for that LS. The grid point name (a string) is saved in the GenLumiInfoHeader, and should be used by the analyzer to sort out the grid points in their ntuple maker. 

For more documentation, see the [PDMV tutorial](https://monte-carlo-production-tools.gitbook.io/project/mccontact/signal-mass-points-in-single-ticket) or this [example fragment](https://cms-pdmv.cern.ch/mcm/public/restapi/requests/get_fragment/EXO-RunIIFall17GS-04839) from the Higgs to XX to 4b analysis ([EXO-RunIIFall17GS-04839](https://cms-pdmv.cern.ch/mcm/requests?prepid=EXO-RunIIFall17GS-04839&page=0)). 

This package provides a script that makes a randomized parameter request starting from the standard EXO spreadsheet. `makeRPRequest.py` makes the randomized parameter "superfragment." It will also generate the `uploadRPRequest.py` command used to upload the request to MCM. From there, follow the usual procedure for a *GS* request (i.e. run the local validation with `testRequests.py` etc.). Note: always use GS, not wmLHEGS! The randomized parameter code takes care of the LHE step by itself.

### Example use
```
# Add Automatic-McM-EXO to your path, get cookie
export PATH=~/MCI/Automatic-McM-EXO:$PATH
Cookies.sh

# Setup CMSSW. This is needed read the CMSSW objects inside the fragments. It doesn't really matter which version.
cd ~/MCI
cmsrel CMSSW_10_2_0
cd CMSSW_10_2_0/src
cmsenv

# Go to working directory with spreadsheet
lxplus770:~/MCI/ --> cd ~/MCI/submissions/testRP

# Here's an example of a spreadsheet
lxplus770:~/MCI/submissions/testRP --> cat spreadsheet.csv 

Dataset name,Total events,Generator fragment name,Generator,Gridpack location,Gridpack cards URL,Tag
ZH_HToSSTobbbb_ZToLL_MH-125_MS-15_ctauS-0_TuneCP5_13TeV-powheg-pythia8,50000,/afs/cern.ch/user/d/dryu/MCI/submissions/HiggsLLP/fragments2018/NLO_HToSSTobbbb_MH125_MS15_ctauS0_13TeV.py,powheg pythia8,/cvmfs/cms.cern.ch/phys_generator/gridpacks/2017/13TeV/powheg/V2/HZJ_HanythingJ_NNPDF31_13TeV_M125_Vleptonic/v1/HZJ_HanythingJ_NNPDF31_13TeV_M125_Vleptonic.tgz,https://github.com/cms-sw/genproductions/blob/51d57507cb4efb9b4554beb636d97219f63da6b8/bin/Powheg/production/VH_from_Hbb/HZJ_HanythingJ_NNPDF30_13TeV_M125_Vleptonic.input,b60203839319d9acb0a5047aa0401aee70e5a90e
ZH_HToSSTobbbb_ZToLL_MH-125_MS-15_ctauS-0p05_TuneCP5_13TeV-powheg-pythia8,50000,/afs/cern.ch/user/d/dryu/MCI/submissions/HiggsLLP/fragments2018/NLO_HToSSTobbbb_MH125_MS15_ctauS0p05_13TeV.py,powheg pythia8,/cvmfs/cms.cern.ch/phys_generator/gridpacks/2017/13TeV/powheg/V2/HZJ_HanythingJ_NNPDF31_13TeV_M125_Vleptonic/v1/HZJ_HanythingJ_NNPDF31_13TeV_M125_Vleptonic.tgz,https://github.com/cms-sw/genproductions/blob/51d57507cb4efb9b4554beb636d97219f63da6b8/bin/Powheg/production/VH_from_Hbb/HZJ_HanythingJ_NNPDF30_13TeV_M125_Vleptonic.input,b60203839319d9acb0a5047aa0401aee70e5a90e
ZH_HToSSTobbbb_ZToLL_MH-125_MS-15_ctauS-1_TuneCP5_13TeV-powheg-pythia8,50000,/afs/cern.ch/user/d/dryu/MCI/submissions/HiggsLLP/fragments2018/NLO_HToSSTobbbb_MH125_MS15_ctauS1_13TeV.py,powheg pythia8,/cvmfs/cms.cern.ch/phys_generator/gridpacks/2017/13TeV/powheg/V2/HZJ_HanythingJ_NNPDF31_13TeV_M125_Vleptonic/v1/HZJ_HanythingJ_NNPDF31_13TeV_M125_Vleptonic.tgz,https://github.com/cms-sw/genproductions/blob/51d57507cb4efb9b4554beb636d97219f63da6b8/bin/Powheg/production/VH_from_Hbb/HZJ_HanythingJ_NNPDF30_13TeV_M125_Vleptonic.input,b60203839319d9acb0a5047aa0401aee70e5a90e
ZH_HToSSTobbbb_ZToLL_MH-125_MS-15_ctauS-10_TuneCP5_13TeV-powheg-pythia8,50000,/afs/cern.ch/user/d/dryu/MCI/submissions/HiggsLLP/fragments2018/NLO_HToSSTobbbb_MH125_MS15_ctauS10_13TeV.py,powheg pythia8,/cvmfs/cms.cern.ch/phys_generator/gridpacks/2017/13TeV/powheg/V2/HZJ_HanythingJ_NNPDF31_13TeV_M125_Vleptonic/v1/HZJ_HanythingJ_NNPDF31_13TeV_M125_Vleptonic.tgz,https://github.com/cms-sw/genproductions/blob/51d57507cb4efb9b4554beb636d97219f63da6b8/bin/Powheg/production/VH_from_Hbb/HZJ_HanythingJ_NNPDF30_13TeV_M125_Vleptonic.input,b60203839319d9acb0a5047aa0401aee70e5a90e

# Make the superfragment
# Note 1: the -n argument sets the dataset name!
# Note 2: -c sets the campaign. This needs to be GS, not wmLHEGS; the randomized parameter code takes care of the LHE step. 
# Note 3: add -f to overwrite a previous attempt.
lxplus770:~/MCI/submissions/testRP --> makeRPRequest.py -s spreadsheet.csv -n ZH_HToSSTobbbb_ZToLL_MH-125_TuneCP5_13TeV_powheg_pythia8 -c RunIIFall17GS
mkdir: created directory 'ZH_HToSSTobbbb_ZToLL_MH-125_TuneCP5_13TeV_powheg_pythia8_RunIIFall17GS'

*********************
RP request created. To upload to MCM:
uploadRPRequest.py ZH_HToSSTobbbb_ZToLL_MH-125_TuneCP5_13TeV_powheg_pythia8_RunIIFall17GS/ZH_HToSSTobbbb_ZToLL_MH-125_TuneCP5_13TeV_powheg_pythia8.pkl --eventsPerLS 500 [-t tag] [--dev]
*********************

# Make a new shell. CMSSW breaks the MCM tools, unfortunately. 
lxplus770: logout
my-computer: ssh lxplus

# Setup MCM tools again
lxplus757: export PATH=~/MCI/Automatic-McM-EXO:$PATH
lxplus757: Cookies.sh

# Upload the fragment to MCM. 
lxplus757: uploadRPRequest.py ZH_HToSSTobbbb_ZToLL_MH-125_TuneCP5_13TeV_powheg_pythia8_RunIIFall17GS/ZH_HToSSTobbbb_ZToLL_MH-125_TuneCP5_13TeV_powheg_pythia8.pkl --eventsPerLS 500 -t EXO-SomeTagName

Namespace(dev=True, eventsPerLS='500', pkl='ZH_HToSSTobbbb_ZToLL_MH-125_TuneCP5_13TeV_powheg_pythia8_RunIIFall17GS/ZH_HToSSTobbbb_ZToLL_MH-125_TuneCP5_13TeV_powheg_pythia8.pkl', tag='EXO-SomeTagName')
Found a cookie file at /afs/cern.ch/user/d/dryu/private/dev-cookie.txt. Make sure it's not expired!
Using sso-cookie file /afs/cern.ch/user/d/dryu/private/dev-cookie.txt
Success!
EXO-RunIIFall17GS-04948

# Run local validation, MCM validation, and ticket creation as usual.


```

Some tips:

- Randomized parameter jobs all go into GS campaigns, not wmLHEGS, regardless of gridpack usage. The LHE step is run by the randomized parameter infrastructure inside CMSSW, rather than as a dedicated step in the campaign. 
- The number of events per lumisection controls how often the job picks a new lumisection, and therefore how many times each grid point is chosen by the random rotation, and therefore the final variance in the number of points per grid point. To get less than 10% variance, we want at least each grid point to have at least 100 LSes. `makeRPRequest.py` calculates this for you, and then `uploadRPRequest.py` sets the "Events per lumi" field on MCM accordingly.
- The "Events per lumi" field control central production. However, the validation jobs use a different parameter to set the events per lumi: the cmsDriver sequence on MCM. By setting this to a small number (around 25), this allows you to run a decent number of grid points in your validation job, without having to run many thousands of events. `uploadRPRequest.py` adds the following to the sequence:

```
--customise_commands "process.source.numberEventsInLuminosityBlock = cms.untracked.uint32(25)"
```

- The MCM validation might be annoying, because the validation parameters like time/event and filter efficiency might be different depending on which random grid points are used in the validation job. We don't have a good solution for this yet... so, do your best to get it validated, and don't be afraid to ask for advice!
