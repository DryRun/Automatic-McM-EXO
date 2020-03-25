import os
import sys
import abc
import re
import json

def format_fragment(fragment):
	return re.sub(
		"pythia8(.*)Settings = cms.vstring\([^\)]*\)", 
		r"pythia8\1SettingsBlock",
		fragment)

# Individual request (one grid point)
class Request():
	__metaclass__ = abc.ABCMeta
	def __init__(self, grid_point_name, fragment_path, nevents, generator_name):
		self._grid_point_name = grid_point_name
		self._fragment_path = fragment_path
		self._nevents = nevents
		self._generator_name = generator_name
		if not os.path.exists(self._fragment_path):
			raise ValueError("Fragment {} doesn't exist".format(self._fragment_path))

	def grid_point_name(self):
		return self._grid_point_name

	def fragment_path(self):
		return self._fragment_path

	def nevents(self):
		return self._nevents

	def generator_name(self):
		return self._generator_name

# Individual gridpack request (one grid point). 
# Extends class Request, adding field for gridpack.
class GridpackRequest(Request):
	def __init__(self, grid_point_name, fragment_path, nevents, generator_name, gridpack_path):
		super(GridpackRequest, self).__init__(grid_point_name, fragment_path, nevents, generator_name)

		self._gridpack_path = gridpack_path
		if not os.path.exists(self._gridpack_path):
			raise ValueError("Gridpack {} doesn't exist".format(self._gridpack_path))

	def gridpack_path(self):
		return self._gridpack_path

# Randomized parameter request = whole signal grid. 
class RandomizedParameterRequest():
	def __init__(self, dataset_name, campaign, output_dir=".", use_gridpack=False, overwrite=False):
		self._superfragment_path = "{}/{}.py".format(output_dir, dataset_name)
		if os.path.isfile(self._superfragment_path):
			if overwrite:
				print "[RandomizedParameterRequest::__init__] WARNING : Overwriting old fragment at {}".format(self._superfragment_path)
			else:
				raise ValueError("Output fragment {} already exists. Please move it out of the way first.".format(self._superfragment_path))

		self._dataset_name = dataset_name
		self._type = "gridpack" if use_gridpack else "pythia"
		self._requests = []

	def type(self):
		return self._type

	def requests(self):
		return self._requests

	def total_nevents(self):
		return sum([x.nevents() for x in self._requests])

	def add_request(self, *args, **kwargs):
		if self._type == "pythia":
			self._requests.append(Request(*args, **kwargs))
		elif self._type == "gridpack":
			self._requests.append(GridpackRequest(*args, **kwargs))


	def finalize(self):
		# Calculate weights
		total_events = sum([request._nevents for request in self._requests])

		# Create list of grid points
		# (Each element is a dictionary which will get printed using json.dumps)
		grid_point_list = []
		for request in self._requests:
			grid_point_list.append({})
			grid_point_list[-1]['name'] = request.grid_point_name()
			grid_point_list[-1]['weight'] = 1. * request._nevents / total_events

			# Import request fragment
			frag_dir = os.path.dirname(request.fragment_path())
			frag_name = os.path.basename(request.fragment_path())
			if not frag_dir in sys.path:
				sys.path.insert(0, frag_dir)
			print("DEBUG : Importing fragment {}".format(frag_name[:-3]))
			module = __import__(frag_name[:-3])
			useProcessParameters = False
			if hasattr(module.generator.PythiaParameters, "processParameters"):
				useProcessParameters = True
				grid_point_list[-1]['processParameters'] = [x for x in module.generator.PythiaParameters.processParameters]
			#grid_point_list[-1]['fragment'] = format_fragment(module.generator.PythiaParameters.dumpPython())

			if self._type == "gridpack":
				grid_point_list[-1]['gridpack_path'] = request.gridpack_path()
		 
		# Extract imports and PDF
		re_imports = re.compile("from.*import.*\n")
		re_pdf = re.compile("pythia8(?P<pdf>CUETP8M1|CUEP8M1|CP2|CP3|CP5)SettingsBlock")
		re_sblock = re.compile("(?P<sblock>pythia8.*Block)")
		imports = []
		sblocks = []
		sblock_strings = []
		pdf_block = None
		with open(self._requests[0].fragment_path(), 'r') as cfg_example:
			for line in cfg_example:
				match_imports = re_imports.search(line)
				if match_imports:
					this_import = match_imports.group().rstrip()
					imports.append(this_import)
				match_pdf = re_pdf.search(line)
				if match_pdf:
					pdf_block = match_pdf.group("pdf")
				match_sblock = re_sblock.search(line)
				if match_sblock:
					this_sblock = match_sblock.group("sblock").rstrip()
					sblocks.append(this_sblock)
					sblock_strings.append("\"{}\"".format(this_sblock.replace("Block", "")))
		if useProcessParameters:
			sblocks.append("processParameters = cms.vstring(grid_point['processParameters'])")
			sblock_strings.append("'processParameters'")
		#print "Including the following imports:"
		#for importt in imports:
		#	print "\t" + importt
		#print "Including the following settings blocks:"
		#for sblock in sblocks:
		#	print "\t" + sblock
		if not pdf_block:
			raise ValueError("Didn't find PDF string in file {}".format(self._requests[0].fragment_path()))

		if self._type == "gridpack":
			gridpack_string = "\n		GridpackPath = cms.string(grid_point['gridpack_path']),\n"
		else:
			gridpack_string = "\n"

		#print "[debug] sblocks:"
		#print "\n\t".join(sblocks)
		#print "[debug] sblock strings:"
		#print "\n\t\t".join(sblock_strings)
		#print "[debug] gridpack_string:"
		#print gridpack_string

		with open(self._superfragment_path, 'w') as superfragment:
			superfragment.write("""import FWCore.ParameterSet.Config as cms

{imports}

generator = cms.EDFilter("Pythia8GeneratorFilter",
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(13000.),
    RandomizedParameters = cms.VPSet(),
)

grid_points = {points}

for grid_point in grid_points:
	basePythiaParameters = cms.PSet(
		{settings_blocks},
		parameterSets = cms.vstring(
			{settings_strings},
		),
	)

	generator.RandomizedParameters.append(
		cms.PSet(
            ConfigWeight = cms.double(grid_point['weight']),
            ConfigDescription = cms.string(grid_point['name']),
            PythiaParameters = basePythiaParameters,{gridpack_string}
		)
	)

ProductionFilterSequence = cms.Sequence(generator)          
""".format(
	points=json.dumps(grid_point_list), 
	imports="\n".join(imports), 
	settings_blocks=",\n\t\t".join(sblocks), 
	settings_strings=",\n\t\t\t".join(sblock_strings), 
	gridpack_string=gridpack_string))

if __name__ == "__main__":
	# Test
	rp_request = RandomizedParameterRequest(dataset_name="testRPDataset", campaign="RunIIFall18wmLHEGS")
	import glob
	fragments = glob.glob("/afs/cern.ch/user/d/dryu/workspace/private/MCI/Automatic-McM-EXO/randomized_parameters/test/LO*py")
	for fragment in fragments[:3]:
		rp_request.add_request(
			grid_point_name=os.path.basename(fragment)[:-3],
			fragment_path=fragment,
			nevents=10000,
			generator_name="powheg",
			gridpack_path="/cvmfs/cms.cern.ch/phys_generator/gridpacks/slc6_amd64_gcc481/13TeV/powheg/V2/HWplusJ_HanythingJ_NNPDF30_13TeV_M125_Vleptonic/v2/HWplusJ_HanythingJ_NNPDF30_13TeV_M125_Vleptonic_tarball.tar.gz",
		)
	rp_request.finalize("/afs/cern.ch/user/d/dryu/workspace/private/MCI/Automatic-McM-EXO/randomized_parameters/test/outputs")
