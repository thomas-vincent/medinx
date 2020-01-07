import unittest
import tempfile
import shutil
import os.path as op
import os
import iso8601
from iso8601 import parse_date
from itertools import chain

import medinx
import medinx.ui as mdx_ui

import logging
import sys
logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger('medinx')

class TableEditorTest(unittest.TestCase):
    def setUp(self):
        if '-v' in sys.argv:
            logger.setLevel(10)
            self.verbose = True
        else:
            self.verbose = False  

        self.tmp_dir = tempfile.mkdtemp(prefix='medinx_tmp_')
        self.clean_tmp = True

        self.test_data = [
            ('research/bibliography/movies/interstellar_wormhole_james.pdf',
             {'author': ['olivier_james', 'eugenie_von_tunzelmann',
                         'paul_franklin'],
              'journal': ['american_journal_of_physics'],
              'publication_date' : ['#2015-03'],
              'reviewed' : [False],
              'impact' : [5.6],
              'doc_type': ['scientific_article'],
              'keyword' : ['physics', 'einstein_ring', 'relativity', 'cgi']}),
            ('research/bibliography/movies/goofiest_movies_of_all_times.pdf',
             {'author': ['george_abitbol', 'relativity',
                         'jean-philippe_herbien'],
              'doc_type':['scientific_article'],
              'publication_year': [2005]}),
            ('research/bibliography/music/goofiest_music_of_all_times.pdf',
             {'author': ['jean-philippe_herbien'],
              'publication_year': [2009]}),
            ('research/projects/big_one/bibliography/.pdf', {}),
            ('administration/condo_NY/meetings/annual_assembly_2017_09_01.docx',
             {'date': ['#2017-09-01T18:30']}),
            ('administration/condo/meetings/annual_assembly_2016_08_27.docx',
             {'date': ['#2016-08-27T20:00']}),
            ('administration/condo/meetings/annual_assembly_2015_08_29.docx',
             {'date': ['#2015-08-29T19:00']}),
            ('administration/condo/contracts/gaz_2014.doc',
             {'doc_type': ['contract'], 'date': ['#2014-01-10']}),
            ('administration/condo/contracts/phone_cie_2011.doc', {}),
            ('administration/condo/contracts/the_cleaning_guys.doc', {}),
            ('administration/condo/contracts/letter_phone_cie.doc',
             {'author': ['me'], 'date': ['#2016-09-10']}),
            ('administration/condo/bills/the_cleaning_guys.doc', {}),
            ('administration/condo/bibliography/DIY_garage_digging.pdf', {}),
            ('administration/condo/bibliography/DIY_gaz_pipes.pdf', {}),
            ('administration/condo/bibliography/admin_of_the_year.pdf', {}),
            ('personal/visit_card.svg', {}),
            ('personal/visit_card.pdf', {}),
            ('personal/photo_id.png', {'rating': [9.9]}),
            ('personal/CV/cv_long_en.doc', {}),
            ('personal/CV/cv_long_fr.doc', {}),
            ('personal/jobs/applications/motivation_letter_big_cie.doc', {}),
            ('personal/jobs/applications/motivation_letter_awesome_cie.doc',{}),
            ]
        
    def tearDown(self):
        if self.clean_tmp:
            shutil.rmtree(self.tmp_dir)

    def test_table_creation(self):
        test_data = [('average_doc.doc', {'rating':[5.0, 4.4], 'reviewed':[True],
                                          'review_date':[parse_date('2016')]}),
                     ('poor_table.csv', {'rating':[2.0]}),
                     ('great_image.jpg', {'rating':[10.0]}),
                     ('mixed_image.jpg', {'rating':[1.5, 11.5]}),
                     ('unrated_image.jpg', {'author':['me']})]
        index_main = medinx.MetadataIndex(test_data)

        table_model = mdx_ui.MdataTableModel(index_main)

        indexed_fns = index_main.get_files()
        indexed_attrs = index_main.get_attributes() # To implement and test in TopLevelAPI
        
        self.assertEqual(table_model.rowCount(), len(indexed_fns))
        self.assertEqual(table_model.columnCount(), len(indexed_attrs))

        for ifile, (file_fn, mdata) in enumerate(test_data): # row
            for iattr, attr in enumerate(indexed_attrs): # column
                qt_index = table_model.index(ifile, iattr)
                self.assertEqual(table_model.data(qt_index),
                                 medinx.format_values(test_data[ifile][1].get(attr, [])))

    def test_table_edition(self):
        test_data = [('average_doc.doc', {'rating':[5.0, 4.4], 'reviewed':[True],
                                          'review_date':[parse_date('2016')]}),
                     ('poor_table.csv', {'rating':[2.0]}),
                     ('great_image.jpg', {'rating':[10.0]}),
                     ('mixed_image.jpg', {'rating':[1.5, 11.5]}),
                     ('unrated_image.jpg', {'author':['me']})]
        index_main = medinx.MetadataIndex(test_data)

        table_model = mdx_ui.MdataTableModel(index_main)

        attr_to_edit = 'rating'
        new_values = [4.1]
        attributes = index_main.get_attributes()
        iattr = attributes.index(attr_to_edit)
        qt_index = table_model.index(0, iattr)
        table_model.setData(qt_index, medinx.format_values(new_values))

        self.assertEqual(index_main.get_metadata(test_data[0][0])[attr_to_edit],
                         new_values)

        new_values = []
        table_model.setData(qt_index, medinx.format_values(new_values))
        self.assertEqual(index_main.get_metadata(test_data[0][0])[attr_to_edit],
                         new_values)

        attr_to_edit = 'author'
        new_values = ['nobody', 'them']
        attributes = index_main.get_attributes()
        iattr = attributes.index(attr_to_edit)
        ifile = 4
        qt_index = table_model.index(ifile, iattr)
        table_model.setData(qt_index, medinx.format_values(new_values))

        self.assertEqual(index_main.get_metadata(test_data[ifile][0])[attr_to_edit],
                         new_values)

        attr_to_edit = 'review_date'
        new_values = [parse_date('2020-01-02')]
        attributes = index_main.get_attributes()
        iattr = attributes.index(attr_to_edit)
        ifile = 4
        qt_index = table_model.index(ifile, iattr)
        table_model.setData(qt_index, medinx.format_values(new_values))

        self.assertEqual(index_main.get_metadata(test_data[ifile][0])[attr_to_edit],
                         new_values)

        attr_to_edit = 'reviewed'
        new_values = [False]
        attributes = index_main.get_attributes()
        iattr = attributes.index(attr_to_edit)
        ifile = 0
        qt_index = table_model.index(ifile, iattr)
        table_model.setData(qt_index, medinx.format_values(new_values))

        self.assertEqual(index_main.get_metadata(test_data[ifile][0])[attr_to_edit],
                         new_values)

    def test_table_save(self):
        raise NotImplementedError()
