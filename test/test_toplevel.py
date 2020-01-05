"""
Run unit tests from package root:

# all unit tests:
$ python -m unittest test.test_toplevel

# one single test:
$ python -m unittest test.test_toplevel.TopLevelAPITest.test_load_folder

# one single test and invoke ipython debugger on expection:
$ ipytest3 test.test_toplevel.TopLevelAPITest.test_load_folder

Run main:
$ python medinx.py


TODO: use pretty indentation when dumping json
"""
import unittest
import tempfile
import shutil
import os.path as op
import os
import json
import jsonschema
import iso8601
from iso8601 import parse_date

import medinx
from medinx._medinx import MDF_JSON_SCHEMA
from medinx._medinx import PREDICATE_RE, VALUE_REGEXP

import logging
import sys
logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger('medinx')

class TopLevelAPITest(unittest.TestCase):

    DEFAULT_FILE_SIZE = 512 #bytes
    
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
        
    def test_load_folder(self):
        test_data = self._dump_test_files(self.test_data)
        index_main = medinx.parse_folder(self.tmp_dir)

        for file_fn, mdata in test_data:
            for a,values in mdata.items():
                for iv, v in enumerate(values):
                    if isinstance(v, str) and v.startswith('#'):
                        values[iv] = parse_date(v[1:])
                    
            self.assertTrue(op.exists(file_fn))
            if len(mdata)>0:
                self.assertEqual(index_main.get_metadata(file_fn), mdata)

    def test_filter_equality(self):
        test_data = [('doc1.doc', {'author':['me'],
                                   'reviewed':[True],
                                   'rating':[1.2],
                                   'review_date':[parse_date('2016-02-01')]}),
                     ('table.csv', {'author':['somebody'],
                                    'rating':[5.0],
                                    'reviewed':[False],
                                    'review_date':[parse_date('2016-02-01T12:12')]})]
        index_main = medinx.MetadataIndex(test_data)

        # Check string
        test_author = 'me'
        selection = index_main.filter('author=%s' % test_author)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if test_author in md.get('author', [])))

        # Check boolean
        reviewed = True
        selection = index_main.filter('reviewed=%s' % reviewed)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if 'reviewed' in md and md['reviewed'][0] == reviewed))
        reviewed = False
        selection = index_main.filter('reviewed=%s' % reviewed)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if 'reviewed' in md and md['reviewed'][0] == reviewed))
        
        # Check number
        rating = 5.5
        selection = index_main.filter('rating=%s' % rating)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if 'rating' in md and md['rating'][0] == rating))

        rating = 5
        selection = index_main.filter('rating=%s' % rating)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if 'rating' in md and md['rating'][0] == rating))

        # Check date
        rev_date = '#2016-02-01'
        selection = index_main.filter('review_date=%s' % rev_date)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if 'review_date' in md and \
                             md['review_date'][0] == parse_date(rev_date[1:])))
        
    def test_filter_comparison_float(self):
        test_data = [('average_doc.doc', {'rating':[5.0, 4.4], 'reviewed':[True],
                                          'review_date':[parse_date('2016')]}),
                     ('poor_table.csv', {'rating':[2.0]}),
                     ('great_image.jpg', {'rating':[10.0]}),
                     ('mixed_image.jpg', {'rating':[1.5, 11.5]}),
                     ('unrated_image.jpg', {'author':['me']})]
        index_main = medinx.MetadataIndex(test_data)

        threshold = 5.0
        selection = index_main.filter('rating<%f' % threshold)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any(v < threshold for v in md.get('rating', [100]))))

        selection = index_main.filter('rating>%f' % threshold)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any(v > threshold for v in md.get('rating', [0]))))

        selection = index_main.filter('rating>=%f' % threshold)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any(v >= threshold for v in md.get('rating', [0]))))

        selection = index_main.filter('rating<=%f' % threshold)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any(v <= threshold for v in md.get('rating', [100]))))
        
    def test_filter_comparison_str(self):
        test_data = [('repport.doc', {'author':['me', 'myself'],
                                      'location':['paris', 'new-york']}),
                     ('spec.doc', {'author':['group'],
                                   'location':['london']}),
                     ('unrelated.doc', {'rating': [5]})]
        index_main = medinx.MetadataIndex(test_data)

        ref_str = 'm'
        selection = index_main.filter('author<=%s' % ref_str)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v <= ref_str for v in md.get('author', ['zzz'])])))

        ref_str = 'me'
        selection = index_main.filter('author<%s' % ref_str)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v < ref_str for v in md.get('author', ['zzz'])])))
        
        ref_str = 'm'
        selection = index_main.filter('author>=%s' % ref_str)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v >= ref_str for v in md.get('author', [''])])))

        ref_str = 'me'
        selection = index_main.filter('author>%s' % ref_str)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v > ref_str for v in md.get('author', [''])])))


    def test_filter_comparison_date(self):
        test_data = [('very_old.doc', {'rev_date':[parse_date('1949-05-23'),
                                                   parse_date('2016-04-01')],
                                       'location':['paris', 'new-york']}),
                     ('early_doc.doc', {'rev_date':[parse_date('2017-03-31'),
                                                    parse_date('2016-04')],
                                   'location':['london']}),
                     ('unrelated.doc', {'rating': [5]})]
        index_main = medinx.MetadataIndex(test_data)


        
        ref_sdate = '2016-04'
        ref_date = parse_date(ref_sdate)

        min_date = parse_date('1900')
        max_date = parse_date('2100')
                
        selection = index_main.filter('rev_date>%s' % ref_sdate)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v > ref_date for v in md.get('rev_date', [min_date])])))

        selection = index_main.filter('rev_date>=%s' % ref_sdate)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v >= ref_date for v in md.get('rev_date', [min_date])])))

        
        selection = index_main.filter('rev_date<%s' % ref_sdate)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v < ref_date for v in md.get('rev_date', [max_date])])))

        selection = index_main.filter('rev_date<=%s' % ref_sdate)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v <= ref_date for v in md.get('rev_date', [max_date])])))

        
    def test_filter_comparison_bool(self):
        test_data = [('validated.doc', {'approved':[True],
                                       'reviewed':[True]}),
                     ('rejected.doc', {'approved':[False],
                                       'location':['london']}),
                     ('mixed_feelings.doc', {'approved':[False, True]}),
                     ('unrelated.doc', {'rating': [5]})]

        index_main = medinx.MetadataIndex(test_data)

        ref_val = True
        selection = index_main.filter('approved>%s' % ref_val)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v > ref_val for v in md.get('approved', [-1])])))

        selection = index_main.filter('approved>=%s' % ref_val)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v >= ref_val for v in md.get('approved', [-1])])))

        selection = index_main.filter('approved<%s' % ref_val)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v < ref_val for v in md.get('approved', [2])])))

        selection = index_main.filter('approved<=%s' % ref_val)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([v <= ref_val for v in md.get('approved', [2])])))
        
    def test_filter_value(self):
        test_data = [('report.doc', {'tag':['nice', 'specification', 'data']}),
                     ('summary.doc', {'keyword':['data', 'specification']}),
                     ('mixed_feelings.doc', {'qualifier':['specification', 'algorithm']}),
                     ('unrelated.doc', {'rating': [5]})]

        index_main = medinx.MetadataIndex(test_data)

        term = 'specification'
        selection = index_main.filter('%s' % term)
        self.assertEqual(set(selection.get_files()),
                         set(fn for fn, md in test_data
                             if any([term in vals for vals in md.values() \
                                     if isinstance(vals[0], str)])))



    def test_filter_not_value(self):
        """ 
        Not yet supported -> requires to change how predicate is coded.
        Maybe it's not that needed...
        """
#        test_data = [('report.doc', {'tag':['nice', 'specification', 'data']}),
#                     ('summary.doc', {'keyword':['data', 'specification']}),
#                     ('mixed_feelings.doc', {'qualifier':['specification', 'algorithm']}),
#                    ('unrelated.doc', {'rating': [5]})]
#
#        index_main = medinx.MetadataIndex(test_data)
#
#        term = 'data'
#        selection = index_main.filter('!%s' % term)
#        self.assertEqual(set(selection.get_files()),
#                         set(fn for fn, md in test_data
#                             if all([term not in vals for vals in md.values() \
#                                     if isinstance(vals[0], str)])))
        pass
    
    def test_bad_queries(self):
        #TODO
        pass
    
    ##
    ## Not top-level -> to put somewhere else
    ##

    def test_predicate_regexp(self):

        self.assertIsNone(VALUE_REGEXP.match('=me'))
        
        result = PREDICATE_RE.search('attr=me')
        self.assertIsNotNone(result)
        self.assertEqual(result.group('attr'), 'attr')
        self.assertEqual(result.group('op_bin'), '=')
        self.assertEqual(result.group('aval'), 'me')

        result = PREDICATE_RE.search('attr<=5')
        self.assertIsNotNone(result)
        self.assertEqual(result.group('attr'), 'attr')
        self.assertEqual(result.group('op_bin'), '<=')
        self.assertEqual(result.group('aval'), '5')

        result = PREDICATE_RE.search('attr>5')
        self.assertIsNotNone(result)
        self.assertEqual(result.group('attr'), 'attr')
        self.assertEqual(result.group('op_bin'), '>')
        self.assertEqual(result.group('aval'), '5')

        result = PREDICATE_RE.search('attr!=#2016')
        self.assertIsNotNone(result)
        self.assertEqual(result.group('attr'), 'attr')
        self.assertEqual(result.group('op_bin'), '!=')
        self.assertEqual(result.group('aval'), '#2016')

        result = PREDICATE_RE.search('!#2016')
        self.assertIsNotNone(result)
        self.assertEqual(result.group('op_una'), '!')
        self.assertEqual(result.group('val'), '#2016')

        result = PREDICATE_RE.search('me')
        self.assertIsNotNone(result)
        self.assertEqual(result.group('op_una'), '')
        self.assertEqual(result.group('val'), 'me')
        
        # Bad criteria
        for bad in ['=me', 'attr>', '<attr', '!!val', '@me=4', 'val!']:
            result = PREDICATE_RE.search(bad)
            self.assertIsNone(result)
        
    def test_mdf_schema(self):
        jsonschema.Draft3Validator.check_schema(MDF_JSON_SCHEMA)

        mdata = {'astr':['s1', 's2'], 'anum':[1, 2.5, 3], 'abool':[True],
                 'adate':['#2019-03']}
        jsonschema.validate(mdata, MDF_JSON_SCHEMA)

        jsonschema.validate({}, MDF_JSON_SCHEMA)

    def test_mdf_schema_on_bad_entry(self):
        for bad_mdata in [{'s': 1}, {'o': {'yo':'mama'}}, {'n': None}]:
            self.assertRaises(jsonschema.exceptions.ValidationError,
                              jsonschema.validate, bad_mdata, MDF_JSON_SCHEMA)
        
    def test_load_single_file(self):
        mdata = {'astr':['s1'], 'anum':[1, 2.5, 3], 'abool':[True],
                 'adate':['#2019-03']}
        test_data = self._dump_test_files([('test.doc', mdata)])

        afile, loaded_mdata = medinx._load_metadata(test_data[0][0] + '.mdf')
        
        self.assertEqual(afile, test_data[0][0])
        self.assertTrue(set(mdata.keys()).issubset(loaded_mdata.keys()))
        for attr in ['astr', 'anum', 'abool']:
            self.assertEqual(loaded_mdata[attr], mdata[attr])
            
        self.assertEqual(loaded_mdata['adate'],
                         [parse_date(mdata['adate'][0][1:])])

    ##
    ## Helper methods
    ##

    def _dump_test_files(self, data_list):
        return [(self._create_tmp_mdf_file(fn, md), md) for fn, md in data_list]
    
    def _create_tmp_mdf_file(self, fn, metadata):
        """
        Create a mdf file named after the name of the given file or folder *fn* 
        and store the content of given metadata in it.
        The mdf file name is the given *fn* with the extra extension .mdf

        Args:
             - fn (string): existing file path
             - metadata (dict):
               Dictionary mapping string attributes to a primary type or
               an homogeneous list of primary type.

        Output: abs path of temporary file created from *fn*
        """
        
        if not fn.endswith('/'):
            file_size = TopLevelAPITest.DEFAULT_FILE_SIZE
            if len(metadata)>0:
                self._create_tmp_files([fn+'.mdf'],
                                       contents=[json.dumps(metadata)])
            return self._create_tmp_files([fn], contents=['dummy_content'])[0]
        else:
            dname = op.join(self.tmp_dir, fn)
            if not op.exists(dname):
                os.makedirs(dname)
            if len(metadata)>0:
                self._create_tmp_files([fn[:-1]+'.mdf'],
                                       contents=[json.dumps(metadata)])            
            return dname
        
    def _create_tmp_files(self, fns, size=DEFAULT_FILE_SIZE, contents=None):
        """
        Create files from given filenames in the current temporary directory
        (see self.tmp_dir).
        If *contents* is None then file content is filled with random bytes up 
        to given *size* in bytes.
        """
        if contents is not None:
            assert(len(contents) == len(fns))
            open_mode = 'w'
        else:
            contents = [os.urandom(size) for fn in fns]
            open_mode = 'wb'

        fns = [op.join(self.tmp_dir,fn) for fn in fns]
        for fn, content in zip(fns, contents):
            d = op.dirname(fn)
            if not op.exists(d):
                os.makedirs(d)
            with open(fn, open_mode) as fout:
                fout.write(content)

        return fns

if __name__ == "__main__":
    # logger.setLevel(0) #TODO: add command option?
    unittest.main()
