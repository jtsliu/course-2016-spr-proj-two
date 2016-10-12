"""
File: crime_knn.py

Description: Classifying crime areas of Boston with k-nearest neighbors
Author(s): Raaid Arshad and Michael Clawar

Notes:
"""

import datetime
import numpy as np
import pandas
import prov
import uuid

from mjclawar_rarshad.reference import mcra_structures as mcras
from mjclawar_rarshad.reference.mcra_structures import MCRASProcessor, MCRASSettings, MCRASProvenance
from mjclawar_rarshad.tools.database_helpers import DatabaseHelper
from mjclawar_rarshad.tools.provenance import ProjectProvenance
from mjclawar_rarshad.tools.mcras_plotting import MCRASPlotting

from sklearn import neighbors
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
import mplleaflet


class CrimeKNNSettings(MCRASSettings):
    @property
    def data_namespace(self):
        return mcras.DAT_NAMESPACE

    @property
    def data_entity(self):
        return 'crime_knn'

    @property
    def agent(self):
        return '%s:%s' % (mcras.ALG_NAMESPACE.name, self.data_entity)

    @property
    def base_url(self):
        return 'crime_incidents'


class CrimeKNNProvenance(MCRASProvenance):
    def __init__(self, settings, database_helper):
        assert isinstance(settings, CrimeKNNSettings)
        assert isinstance(database_helper, DatabaseHelper)
        self.settings = settings
        self.database_helper = database_helper

    def update_provenance(self, full_provenance=False, start_time=None, end_time=None):
        """
        Writes a ProvDoc for the crime_knn.py script and saves to the collection

        Parameters
        ----------
        full_provenance: bool
        start_time: datetime.datetime
        end_time: datetime.datetime

        Returns
        -------
        """
        prov_obj = ProjectProvenance(database_helper=self.database_helper, full_provenance=full_provenance)
        prov_doc = prov_obj.prov_doc
        this_script = prov_doc.agent(self.settings.agent, mcras.PROVENANCE_PYTHON_SCRIPT)

        resource = prov_doc.entity('%s:%s' % (self.settings.data_namespace.name, self.settings.base_url))

        if full_provenance:
            this_run = prov_doc.activity('%s:a%s' % (mcras.LOG_NAMESPACE.name, str(uuid.uuid4())))
            prov_doc.used(this_run, resource)
        else:
            this_run = prov_doc.activity('%s:a%s' % (mcras.LOG_NAMESPACE.name, str(uuid.uuid4())), start_time, end_time,
                                         {prov.model.PROV_TYPE: mcras.PROV_ONT_EXTENSION})

        prov_doc.wasAssociatedWith(this_run, this_script)

        data_doc = prov_doc.entity('%s:%s' % (mcras.DAT_NAMESPACE.name, self.settings.data_entity),
                                   {prov.model.PROV_LABEL: 'Crime KNN',
                                    prov.model.PROV_TYPE: mcras.PROV_ONT_DATASET})

        prov_doc.wasAttributedTo(data_doc, this_script)
        if full_provenance:
            prov_doc.wasGeneratedBy(data_doc, this_run)
        else:
            prov_doc.wasGeneratedBy(data_doc, this_run, end_time)

        prov_doc.wasDerivedFrom(data_doc, resource, this_run)

        if full_provenance:
            prov_obj.write_provenance_json()
        else:
            self.database_helper.record(prov_doc.serialize())


class CrimeKNNProcessor(MCRASProcessor):
    def __init__(self, settings, database_helper):
        assert isinstance(settings, CrimeKNNSettings)
        assert isinstance(database_helper, DatabaseHelper)
        self.settings = settings
        self.database_helper = database_helper

    def run_processor(self, full_provenance=False):
        print('Estimating knn for crime data')
        start_time = datetime.datetime.now()
        df = self._load_prep_df()

        # Boundaries for subset of Boston
        x_min, x_max = -71.1, -71.0475
        y_min, y_max = 42.34, 42.369
        bounds = ((x_min, y_min), (x_max, y_max))

        df = df[(df['LONGITUDE'] < x_max) & (df['LONGITUDE'] > x_min) &
                (df['LATITUDE'] < y_max) & (df['LATITUDE'] > y_min)].copy()

        self._knn_weekday_analysis(df, bounds)

        end_time = datetime.datetime.now()

        crime_provenance = \
            CrimeKNNProvenance(self.settings, database_helper=self.database_helper)
        crime_provenance.\
            update_provenance(full_provenance=full_provenance, start_time=start_time, end_time=end_time)

        print('Done estimating knn for crime data')

    def _load_prep_df(self):
        """
        Reads the pandas.DataFrame from the MongoDB collection, cleans it up, and returns it

        Returns
        -------
        pandas.DataFrame
        """
        df = self.database_helper.load_permanent_pandas('crime_incidents', cols=['location', 'day_week'])
        df = df.merge(df['location'].apply(lambda x: pandas.Series({'NEEDS_RECODE': x['needs_recoding'],
                                                                    'LONGITUDE': float(x['longitude']),
                                                                    'LATITUDE': float(x['latitude'])})),
                      left_index=True, right_index=True)
        df = df[(df['LONGITUDE'] != 0) & (df['LATITUDE'] != 0)].copy()

        return df

    @staticmethod
    def _knn_weekday_analysis(df, bounds):
        X = df[['LATITUDE', 'LONGITUDE']].values
        y = (1 * df['day_week'].isin(['Friday', 'Saturday', 'Sunday'])).astype(int)

        neighbors_numbers = np.arange(10, 55, 1)
        clf = neighbors.KNeighborsClassifier(10, weights='distance')
        max_score = 0
        for n_neighbors in neighbors_numbers:
            clf = neighbors.KNeighborsClassifier(n_neighbors, weights='distance')
            clf.fit(X, y)
            if max_score + .001 > clf.score(X, y):
                break

        h = .0003  # step size in the mesh

        # Plot the decision boundary. For that, we will assign a color to each
        # point in the mesh [x_min, m_max]x[y_min, y_max].
        yy, xx = np.meshgrid(np.arange(bounds[0][0], bounds[1][0], h),
                             np.arange(bounds[0][1], bounds[1][1], h))
        Z = clf.predict(np.c_[xx.ravel(), yy.ravel()])

        # Put the result into a color plot
        Z = Z.reshape(xx.shape)

        MCRASPlotting.leaflet_heatmap(yy=yy, xx=xx, Z=Z, bounds=bounds, map_path='crime_knn_weekday.html',
                                      legend_text='Weekday (0) vs Weekend (1)', tiles='osm_mapnik',
                                      description_title='Predicting weekend vs weekday crimes in Boston',
                                      description_text='Using <a target="_blank" '
                                                       'href="http://scikit-learn.org/stable/modules/generated'
                                                       '/sklearn.neighbors.KNeighborsClassifier.html">k-nearest '
                                                       'neighbors classification</a>, we fit a model over '
                                                       'the area of downtown Boston with latitude and longitude as '
                                                       'predictors and all crimes from January to August 2015, '
                                                       'flagged with day of the week they were committed.')
