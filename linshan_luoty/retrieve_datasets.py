import urllib.request
import json
import datetime
import dml
import sys
import prov
import provenance
import uuid


datasets = {
	'crime_incident_reports':'https://data.cityofboston.gov/resource/7cdf-6fgx.json?year=2014&$limit=50000',
	'employee_earnings_report_2014':'https://data.cityofboston.gov/resource/4swk-wcg8.json?$limit=50000',
	'approved_building_permits':'https://data.cityofboston.gov/resource/msk6-43c6.json?$limit=50000'
}

#auth
client = dml.pymongo.MongoClient()
repo = client.repo
repo.authenticate('linshan_luoty','linshan_luoty')
auth = json.loads(open(sys.argv[1]).read())

# Retrieve some data sets.
startTime = datetime.datetime.now()

for title in datasets:
	url = datasets[title]
	response = urllib.request.urlopen(url).read().decode("utf-8")
	r = json.loads(response)
	#s = json.dumps(r, sort_keys=True, indent=2)
	repo.dropPermanent(title)
	repo.createPermanent(title)
	repo['linshan_luoty'+'.'+title].insert_many(r)

endTime = datetime.datetime.now()

startTime = None
endTime = None

# Create the provenance document describing everything happening
# in this script. Each run of the script will generate a new
# document describing that invocation event. This information
# can then be used on subsequent runs to determine dependencies
# and "replay" everything. The old documents will also act as a
# log.
'''
doc = provenance.init()

this_script = doc.agent('alg:retrieve_datasets', {prov.model.PROV_TYPE:prov.model.PROV['SoftwareAgent'], 'ont:Extension':'py'})

# crime incidents
crime_resource = doc.entity('bdp:7cdf-6fgx', {'prov:label':'311, Service Requests', prov.model.PROV_TYPE:'ont:DataResource', 'ont:Extension':'json'})
get_crime = doc.activity('log:a'+str(uuid.uuid4()), startTime, endTime, {prov.model.PROV_LABEL: "Retrieve datasets."})
doc.wasAssociatedWith(get_crime, this_script)
doc.usage(get_crime, crime_resource, startTime, None,
        {prov.model.PROV_TYPE:'ont:Retrieval',
         'ont:Query':'?year=2014&$limit=50000'
        }
    )

crime = doc.entity('dat:crime_incident_reports', {prov.model.PROV_LABEL:'Crime Incident Reports', prov.model.PROV_TYPE:'ont:DataSet'})
doc.wasAttributedTo(crime, this_script)
doc.wasGeneratedBy(crime, get_crime, endTime)
doc.wasDerivedFrom(crime, crime_resource, get_crime, get_crime, get_crime)

# employee earnings
earning_resource = doc.entity('bdp:4swk-wcg8', {'prov:label':'311, Service Requests', prov.model.PROV_TYPE:'ont:DataResource', 'ont:Extension':'json'})
get_earning = doc.activity('log:a'+str(uuid.uuid4()), startTime, endTime)
doc.wasAssociatedWith(get_earning, this_script)
doc.usage(get_earning, earning_resource, startTime, None,
        {prov.model.PROV_TYPE:'ont:Retrieval',
         'ont:Query':'?$limit=50000'
        }
    )

earning = doc.entity('dat:employee_earnings_report_2014', {prov.model.PROV_LABEL:'Employee Earnings Report 2014', prov.model.PROV_TYPE:'ont:DataSet'})
doc.wasAttributedTo(earning, this_script)
doc.wasGeneratedBy(earning, get_earning, endTime)
doc.wasDerivedFrom(earning, earning_resource, get_earning, get_earning, get_earning)

# building permits
building_resource = doc.entity('bdp:msk6-43c6', {'prov:label':'311, Service Requests', prov.model.PROV_TYPE:'ont:DataResource', 'ont:Extension':'json'})
get_building = doc.activity('log:a'+str(uuid.uuid4()), startTime, endTime)
doc.wasAssociatedWith(get_building, this_script)
doc.usage(get_building, building_resource, startTime, None,
        {prov.model.PROV_TYPE:'ont:Retrieval',
         'ont:Query':'?$limit=50000'
        }
    )

building = doc.entity('dat:approved_building_permits', {prov.model.PROV_LABEL:'Approved Building Permits', prov.model.PROV_TYPE:'ont:DataSet'})
doc.wasAttributedTo(building, this_script)
doc.wasGeneratedBy(building, get_building, endTime)
doc.wasDerivedFrom(building, building_resource, get_building, get_building, get_building)

repo.record(doc.serialize()) # Record the provenance document.
provenance.update(doc)

print(doc.get_provn())
'''
repo.logout()
