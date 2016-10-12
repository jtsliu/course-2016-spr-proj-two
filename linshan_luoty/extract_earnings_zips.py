import json
import datetime
import dml
import prov.model
import provenance
import uuid
import sys

#auth
client = dml.pymongo.MongoClient()
repo = client.repo
repo.authenticate('linshan_luoty','linshan_luoty')
auth = json.loads(open(sys.argv[1]).read())

# Set up the database connection.
db = repo['linshan_luoty'+'.'+'employee_earnings_report_2014']

startTime = datetime.datetime.now()

# update extract earnings and zips info
earnings_zips = []
for document in db.find({}, {'zip': True,'total_earnings':True, '_id': False}):	# only project zips and earnings
	if 'zip' in document:
		earnings_zips.append( {'zip': document['zip'], 'total_earnings': float(document['total_earnings'])} )

# save it to a temporary folder
repo.dropTemporary("earnings_zips")
repo.createTemporary("earnings_zips")
repo['linshan_luoty.earnings_zips'].insert_many(earnings_zips)

endTime = datetime.datetime.now()
	
startTime = None
endTime = None

# Create the provenance document describing everything happening
# in this script. Each run of the script will generate a new
# document describing that invocation event. This information
# can then be used on subsequent runs to determine dependencies
# and "replay" everything. The old documents will also act as a
# log.
doc = provenance.init()
doc.add_namespace('alg', 'https://data-mechanics.s3.amazonaws.com/linshan_luoty/algorithm/') # The scripts in <folder>/<filename> format.
doc.add_namespace('dat', 'https://data-mechanics.s3.amazonaws.com/linshan_luoty/data/') # The data sets in <user>/<collection> format.
doc.add_namespace('ont', 'https://data-mechanics.s3.amazonaws.com/ontology#') # 'Extension', 'DataResource', 'DataSet', 'Retrieval', 'Query', or 'Computation'.
doc.add_namespace('log', 'https://data-mechanics.s3.amazonaws.com/log#') # The event log.
doc.add_namespace('bdp', 'https://data.cityofboston.gov/resource/')

this_script = doc.agent('alg:extract_earnings_zips', {prov.model.PROV_TYPE:prov.model.PROV['SoftwareAgent'], 'ont:Extension':'py'})

earning = doc.entity('dat:employee_earnings_report_2014', {prov.model.PROV_LABEL:'Employee Earnings Report 2014', prov.model.PROV_TYPE:'ont:DataSet'})

extract_earning_zip = doc.activity('log:a'+str(uuid.uuid4()), startTime, endTime, {prov.model.PROV_LABEL: "Extract earnings and zips."})
doc.wasAssociatedWith(extract_earning_zip, this_script)
doc.usage(extract_earning_zip, earning, startTime, None,
        {prov.model.PROV_TYPE:'ont:Computation'
        }
    )

earning_zip = doc.entity('dat:earnings_zips', {prov.model.PROV_LABEL:'Earnings Zips', prov.model.PROV_TYPE:'ont:DataSet'})
doc.wasAttributedTo(earning_zip, this_script)
doc.wasGeneratedBy(earning_zip, extract_earning_zip, endTime)
doc.wasDerivedFrom(earning_zip, earning, extract_earning_zip, extract_earning_zip, extract_earning_zip)

repo.record(doc.serialize()) # Record the provenance document.
provenance.update(doc)
print(doc.get_provn())

repo.logout()
