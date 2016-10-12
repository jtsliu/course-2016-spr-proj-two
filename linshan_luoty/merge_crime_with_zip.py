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


crime_db = repo['linshan_luoty'+'.'+'crime_incident_reports']
zip_db	 = repo['linshan_luoty'+'.'+'zips_locations']

startTime = datetime.datetime.now()

# go through every entry in crime_incident_reports, and associate it with a zipcode.
crime_zips = []
project_set = {'_id': False, 'shooting': True, 'day_week': True, 'fromdate': True, 'location': True}
for document in crime_db.find({}, project_set):
	zipcode = zip_db.find_one({'longitude': document['location']['longitude'],
								 'latitude': document['location']['latitude']}, {'_id': False, 'zip': True})
	if zipcode is None: 
		continue
	else:
		document['zip'] = zipcode['zip']
		crime_zips.append(document)

# save it to a temporary folder
repo.dropPermanent("crime_zips")
repo.createPermanent("crime_zips")
repo['linshan_luoty.crime_zips'].insert_many(crime_zips)

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

this_script = doc.agent('alg:merge_crime_with_zip', {prov.model.PROV_TYPE:prov.model.PROV['SoftwareAgent'], 'ont:Extension':'py'})

crime = doc.entity('dat:crime_incident_reports', {prov.model.PROV_LABEL:'Crime Incident Reports', prov.model.PROV_TYPE:'ont:DataSet'})
zip_location = doc.entity('dat:zips_locations', {prov.model.PROV_LABEL:'Zips Locations', prov.model.PROV_TYPE:'ont:DataSet'})

merge_crime_with_zip = doc.activity('log:a'+str(uuid.uuid4()), startTime, endTime, {prov.model.PROV_LABEL: "Merge crimes with zips."})
doc.wasAssociatedWith(merge_crime_with_zip, this_script)
doc.usage(merge_crime_with_zip, crime, startTime, None,
        {prov.model.PROV_TYPE:'ont:Computation'
        }
    )
doc.usage(merge_crime_with_zip, zip_location, startTime, None,
        {prov.model.PROV_TYPE:'ont:Computation'
        }
    )

crime_zip = doc.entity('dat:crime_zips', {prov.model.PROV_LABEL:'Crime Zips', prov.model.PROV_TYPE:'ont:DataSet'})
doc.wasAttributedTo(crime_zip, this_script)
doc.wasGeneratedBy(crime_zip, merge_crime_with_zip, endTime)
doc.wasDerivedFrom(crime_zip, crime, merge_crime_with_zip, merge_crime_with_zip, merge_crime_with_zip)
doc.wasDerivedFrom(crime_zip, zip_location, merge_crime_with_zip, merge_crime_with_zip, merge_crime_with_zip)

repo.record(doc.serialize()) # Record the provenance document.
provenance.update(doc)

print(doc.get_provn())

repo.logout()
