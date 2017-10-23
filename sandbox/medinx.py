# -*- coding: utf-8 -*-
"""
Dependency: iso8601
Inputs:

Ouputs:

Run unit tests:
# all unit tests:
$ python -m unittest medinx

# one single test:
$ python -m unittest medinx.Test.test_file_selection

# all unit tests and use invoke ipython debugger:
$ ipytest medinx 

Run main:
$ python medinx.py

#TODO: add logging
#TODO: add profiling features
"""
from future.utils import viewitems #dependency: future
import os.path as op
import os
import unittest
import tempfile
import shutil
import re
import json
import copy

import datetime
def s2d(sd):
    """ Convert stat time to datetime """
    return datetime.datetime.fromtimestamp(sd)

import iso8601 # dependency
from six import string_types, itervalues # dependency

import random    

        
class Metadata:
    """
    Top-level metadata container.

    TODO: describe conventions for metadata format, from spec.
    """
    MDF_EXT = '.mdf'

    ATTR_FORMAT = u'@[a-z0-9_]+'
    ATTRIBUTE_RE = re.compile('^%s$' % ATTR_FORMAT)
    VALUE_FORMAT = u'#?[a-z0-9_:TZ+.-]+'
    VALUE_RE = re.compile('^%s$' % VALUE_FORMAT)

    # Filesystem metadata
    FS_STAT_ATTRS = {'@file_type': lambda(fn): ['file', 'folder'][op.isdir(fn)],
                     '@file_modification_date': \
                          lambda(fn): s2d(os.stat(fn).st_mtime)}
    
    def __init__(self):
        # List of (file name (str), metadata (dict)):  
        self._file_table = []

    @staticmethod
    def _is_primary_type(item):
        return isinstance(item, float) or isinstance(item, int) or \
            isinstance(item, bool) or isinstance(item, datetime.datetime) or \
            isinstance(item, string_types)
    
    @staticmethod
    def _iflatten(l):
        """
        Flatten  given list, if necessary. Handle list of list 
        (but not deeper) 
        """
        if not Metadata._is_primary_type(l):
            for e in l: #assume list
                if isinstance(e, list):
                    for se in e:
                        yield se
                else:
                    yield e
        else:
            yield l

        
    @staticmethod
    def from_folder(folder):
        """
        Parse given folder and its subfolders and create a Metadata object with 
        entries corresponding to files that have side-car .mdf files.
        """
        md = Metadata()
        for root, dirs, files in os.walk(folder):
            for item in dirs+files:
                fn = op.join(root, item)
                md_fn = fn + '.mdf'
                if op.exists(md_fn):
                    md.add_entry(fn, md.load_mdf_file(md_fn))
        return md

    def load_mdf_file(self, fn):
        """ 
        Load and check content from given metadata file. 
        Ensure that associated file exists (without the .mdf extension).

        Return a dict mapping attribute names (string) to their values.
        """
        associated_fn = op.splitext(fn)[0]
        if not op.exists(associated_fn):
            raise IOError('Associated file not found: %s' % associated_fn)
        
        with open(fn, 'r') as fin:
            md = self.load_json(fin.read())
        return md

    def add_entry(self, file_name, metadata=None):
        if metadata is None:
            metadata = {}
        # Add filesystem metadata:
        for fs_attr, md_getter in viewitems(Metadata.FS_STAT_ATTRS):
            metadata[fs_attr] = md_getter(file_name)
        self._file_table.append((op.normpath(file_name), metadata))

    def get_entries_by_value(self, value):
        # TODO: test all scenarios
        # TODO: handle attributes associated with list of values
        
        entries = []
        # print 'get_entries_by_value "%s"' % value
        if value.startswith('!'):
            predicate = lambda v,mvs: all(v != mv for mv in Metadata._iflatten(mvs))
            value = value[1:]
        else:
            predicate = lambda v,mvs: any(v == mv for mv in Metadata._iflatten(mvs))
            
        # Systematic non-optimal search:
        value = self._unformat_date_value(value)
        # print 'unformatted value: ', value
        for fn, md in self._file_table:
            # print 'scanning metadata of ', fn, ':'
            # print md
            if predicate(value, itervalues(md)):
                # print "-> it's a match!"
                entries.append(fn)
        return entries

    def get_entries_by_predicate(self, value, attribute, operator='='):
        # print 'get_entries_by_predicate %s%s%s' % (attribute, operator, value)
        entries = []
        # Systematic non-optimal search:
        value = self.value_from_string(value, attribute)
        # print 'unformatted value: ', value
        if operator == '=':
            predicate = lambda v, av: any(a == v for a in Metadata._iflatten(av))
        elif operator == '<':             
            predicate = lambda v, av: any(a < v for a in Metadata._iflatten(av))
        elif operator == '>':             
            predicate = lambda v, av: any(a > v for a in Metadata._iflatten(av))
        elif operator == '>=':            
            predicate = lambda v, av: any(a >= v for a in Metadata._iflatten(av))
        elif operator == '<=': 
            predicate = lambda v, av: any(a <= v for a in Metadata._iflatten(av))
        elif operator == '=!': 
            predicate = lambda v, av: all(v != e for e in Metadata._iflatten(av))
        else:
            raise Exception('Unsupported operator %s', operator)

        for fn, md in self._file_table:
            mvalue = md.get(attribute, None)
            # print 'scanning: ', mvalue
            if mvalue is not None:
                if predicate(value, mvalue):
                    # print "-> it's a match!"
                    entries.append(fn)
        return entries
        
    def remove_entry(self, file_name):
        """ TODO: useful? """
        pass

    def get_attribute_type(self, attribute):
        atype = None
        # Systematic non-optimal search:
        for entry in self._file_table:
            value = entry[1].get(attribute, None)
            if value is not None:
                if isinstance(value, list):
                    atype = type(value[0]) #TODO: make empty list are ignored
                else:
                    atype = type(value)
                break
        return atype
    
    
    def get(self, file_name):
        # Systematic non-optimal search:
        for fn, md in self._file_table:
            if fn == op.normpath(file_name):
                return md
        return {}
        
    def get_nb_entries(self):
        return len(self._file_table)
    
    @staticmethod
    def date_is_valid(item):
        try:
            iso8601.parse_date(item)
        except iso8601.ParseError:
            return False
        return True
            
    @staticmethod
    def value_is_valid(item):
        
        def single_value_is_valid(item):
            return isinstance(item, float) or isinstance(item, int) or \
                isinstance(item, bool) or isinstance(item, datetime.datetime) or \
                (isinstance(item, string_types) and \
                 Metadata.VALUE_RE.match(item) and \
                 (not item.startswith('#') or Metadata.date_is_valid(item[1:])))

        return single_value_is_valid(item) or \
            (isinstance(item, list) and \
             single_value_is_valid(item[0]) and \
             all(type(e) is type(item[0]) for e in item))
    
    @staticmethod        
    def attribute_is_valid(attr):
        return isinstance(attr, string_types) and \
            Metadata.ATTRIBUTE_RE.match(attr)

    def _unformat_date_value(self, v):
        if isinstance(v, string_types) and v.startswith('#'):
            v = iso8601.parse_date(v[1:])
        return v
            
    def value_from_string(self, v, attribute=None):
        if attribute is None:
            rv = self._unformat_date_value(v)
        else:
            atype = self.get_attribute_type(attribute)
            if atype == str:
                rv = '%s' % v
            elif atype == unicode:
                rv = u'%s' % v
            elif atype == float:
                rv = float(v)
            elif atype == int:
                rv = int(v)
            elif atype == bool:
                rv = bool(v)
            elif atype == datetime.datetime:
                if v.startswith('#'):
                    rv = iso8601.parse_date(v[1:])
                else:
                    rv = iso8601.parse_date(v)
            else:
                raise Exception('Unhandled attribute type "%r"' %atype)
        return rv

    def value_has_consistent_type(self, value, attribute):
        atype = self.get_attribute_type(attribute)
        if atype is not None:
            if not isinstance(value, list):                
                return isinstance(value, atype)
            else:
                return all(isinstance(e, atype) for e in value)
        else:
            return True
        
    def load_json(self, json_content):
        """
        Load and check that json content complies with medinx format.
        Raise InvalidJson<...> exceptions if not.

        TODO: ensure values are casted to global attribute type if available
        """

        def dict_read(pairs):
            d = {}
            errors = []
            for attribute, value in pairs:
                value = self._unformat_date_value(value)
                if not Metadata.attribute_is_valid(attribute):
                    msg = 'Attribute "%s" is not valid' % attribute
                    errors.append(InvalidJsonAttributeFormat(msg))
                if attribute in d:
                    msg = 'Duplicate attribute: "%s"' % attribute
                    errors.append(InvalidJsonAttributeDuplicate(msg))
                if not Metadata.value_is_valid(value):
                    msg = 'Invalid value: %s' % value
                    errors.append(InvalidJsonValue(msg))
                if not self.value_has_consistent_type(value, attribute):
                    msg = 'Value %r has type %s which is inconcistent ' \
                          'with attribute type: %s.' \
                          % (value, type(value),
                             self.get_attribute_type(attribute))
                    errors.append(InconsistentValue(msg))
                d[attribute] = value
                
            if len(errors) > 0:
                if len(errors) > 1:
                    raise InvalidJsonContent('Errors in JSON content', errors)
                else:
                    raise errors[0]
            return d
        
        loaded = json.loads(json_content, object_pairs_hook=dict_read)
        if not isinstance(loaded, dict):
            raise InvalidJsonStructure('Json content must be a dictionary')
        
        return loaded
    
    def query(self, predicates):
        """
        Select metadata matching given predicates.

        Return a MetadataSelection object
        """
        return MetadataSelection(self).query(predicates)

class InvalidPredicateFormat(Exception):
    pass
    
class MetadataSelection:
    """
    Holder for current metadata selection
    """

    PRED_ATTR_VAL_FMT = u'(?P<attr>{attr})(?P<op>=|(?:=!)|(?:>=)|(?:<=)|<|>)' \
                        '(?P<aval>{val})'.format(attr=Metadata.ATTR_FORMAT,
                                                 val=Metadata.VALUE_FORMAT)
    PRED_ATTR_VAL_RE = re.compile(PRED_ATTR_VAL_FMT)
        
    PREDICATES_FORMAT = u'(\s?((?:%s)|(?:!?%s))\s?)*' % (PRED_ATTR_VAL_FMT,
                                               Metadata.VALUE_FORMAT)
    
    PREDICATE_RE = re.compile(PREDICATES_FORMAT)
    
    def __init__(self, metadata):
        """
        Init a selection on given metadata
        """
        self.metadata = metadata
        self._selection = None
        
    def query(self, predicates):
        """
        Apply given predicates to current selection (inplace).

        If predicates are invalid, raises InvalidSelectionPredicates
        """
        if not MetadataSelection.PREDICATE_RE.match(predicates):
            raise InvalidPredicateFormat('Invalid predicates: %s' % predicates)

        for predicate in predicates.split(' '):
            self._query_single_predicate(predicate)

        return self
    
    def _query_single_predicate(self, predicate):
        # TODO: handle different operators
        if predicate.startswith('@'): #TODO: def cst?
            rmatch = MetadataSelection.PRED_ATTR_VAL_RE.match(predicate).groups()
            attribute = rmatch[0]
            operator = rmatch[1]
            value = rmatch[2]
            new_entries = self.metadata.get_entries_by_predicate(value, attribute,
                                                                 operator)

        else:
            new_entries = self.metadata.get_entries_by_value(predicate)
        
        # print 'predicate:', predicate
        # print 'new_entries:', new_entries
        if self._selection is None: # first query
            self._selection = set(new_entries)
        else:
            self._selection.intersection_update(new_entries)
        # print 'cur selection:', self._selection
        
    def complete_attributes(self, prefix):
        """
        Return list of attributes in current selection that start with 
        given prefix.
        """
        return [] #stub

    def complete_values(self, prefix, attribute=None):
        """
        Return list of values in current selection that start with 
        given prefix.
        Limit search to given attribute if not None.
        """
        return [] #stub

    def get_files(self):
        """
        Return list of files in current selection.
        """
        return list(self._selection)
    

### Unit tests ###

    # ['research/bibliography/movies/interstellar_wormhole_james.pdf', {'author': ['olivier_james', 'eugenie_von_tunzelmann', 'paul_franklin'], 'journal':'american_journal_of_physics', 'year':2015, 'keyword'=['physics', 'einstein_ring', 'relativity', 'cgi']}, 
    #  'research/biblbiography/movies/goofiest_movies_of_all_times.pdf', {'author': ['george_abitbol', 'jean-philippe_herbien'], 'year': 2005},
    #  'research/bibliography/music/goofiest_music_of_all_times.pdf', {},
    #  'research/projects/big_one/bibliography/.pdf', {},
    #  'administration/condo_NY/meetings/annual_assembly_2017_09_01.docx', {},
    #  'administration/condo/meetings/annual_assembly_2016_08_27.docx', {},
    #  'administration/condo/meetings/annual_assembly_2015_08_29.docx', {},
    #  'administration/condo/contracts/gaz_2014.doc', {},
    #  'administration/condo/contracts/phone_cie_2011.doc', {},
    #  'administration/condo/contracts/the_cleaning_guys.doc', {},
    #  'administration/condo/contracts/letter_phone_cie.doc', {'author':'me', 'date':2016_09_10_14h25'},
    #  'administration/condo/bills/the_cleaning_guys.doc', {},
    #  'administration/condo/bibliography/DIY_garage_digging.pdf', {},
    #  'administration/condo/bibliography/DIY_gaz_infrastructure.pdf', {},
    #  'administration/condo/bibliography/administrator_of_the_year.pdf', {},
    #  'personal/visit_card.svg', {},
    #  'personal/visit_card.pdf', {},
    #  'personal/photo_id.png', {},
    #  'personal/CV/cv_long_en.doc', {},
    #  'personal/CV/cv_long_fr.doc', {},
    #  'personal/jobs/applications/motivation_letter_big_cie.doc', {},
    # 'personal/jobs/applications/motivation_letter_awesome_cie.doc', {},
    #  ]

class TestIndexRegister(unittest.TestCase):

    def test_uniqueness(self):

        register = IndexRegister()
        collected = set([])
        nb_ids = 10
        for i in range(nb_ids):
            idx = register.next()
            self.assertFalse(idx in collected)
            collected.add(idx)
            
        for i in range(nb_ids/2):
            rnd = random.randint(0, nb_ids-1)
            register.release(rnd)
            if rnd in collected:
                collected.remove(rnd)
            
        for i in range(nb_ids/2):
            idx = register.next()
            self.assertFalse(idx in collected)
        self.assertEquals(len(register._released), 0)
    
class Test(unittest.TestCase):

    # Inputs

    DEFAULT_FILE_SIZE = 512 #bytes
    
    GOOD_JSON = """
    {"@attribute_with_one_value" : "value_string_1",
     "@attribute_with_several_values" : ["val_str_2", "val_str_3"],
     "@attribute_with_numerical_value": 45.6,
     "@attribute_with_numerical_values": [4, 8, 15, 16, 23, 42] ,
     "@attribute_with_boolean_value": false,
     "@attribute_with_date": "#2015-06-04"
    }"""

    BAD_JSON_ATTR_DUPLICATE = \
    """{
      "@attribute_duplicate" : "value_string_1",
      "@attribute_duplicate" : ["val_str_2", "val_str_3"]
    }"""

    BAD_JSON_NON_HOMOGENEOUS_VALUES = \
    '{"@attribute_with_mixed_values" : ["val_str_2", 42.75]}'

    BAD_JSON_NO_DICT ='"no_pairs"'

    BAD_JSON_NESTED = \
    '{"@attribute_with_nested_value" : {"@sub_attr":"sub_value"}}'

    JSON_SINGLE_ATTR_APAT = u'{"@attribute_%s" : "value"}'
    JSON_SINGLE_ATTR_VPAT = u'{"@attribute" : "value_%s"}'

    # Note: "\" is not easy to test -> will escape next char
    # so u"attr_\\" will be interpreted
    BAD_CHAR_ATTR = u'#A&|- !?<>.,:;/%{}[]()=+*$àéèû'
    BAD_CHAR_VAL = u'A&|@ !?<>,;/%{}[]()=*$àéèû'
    
    BAD_VALUE_DATES = ['2015-05-03', '#2015/05/03', '#2015-05-03_15h33',
                       '#2015-05-03 15h33']
    
    GOOD_MDATA_SET = [
        ('home/work/projects/ginzoo2000/doc/letter_iron_cie.doc',
         {u'@author': u'me', u'@doctype': u'letter', u'@recipient': u'iron_cie',
          u'@date' : u'#2017-01-01', u'@project': u'ginzoo2000'}), #0
        ('home/work/projects/ginzoo2000/data/survey.xls',
          {u'@author' : [u'com_team', u'me'], u'@datatype' : u'poll',
           u'@recipient' : u'iron_cie', '@date':'#2016-04-02',
           u'@project': u'ginzoo2000'}), #1
        ('home/work/meetings/weekly_2015_08_10.doc',
         {u'@author': u'secretary', u'@doctype' : u'minutes',
          u'@date' : u'#2015-08-10'}), #2
        ('home/work/meetings/weekly_2016_08_17.doc',
         {u'@author':u'secretary', u'@doctype': u'minutes',
          u'@date': u'#2016-08-17'}), #3
        ('home/work/meetings/weekly_2016_08_24.doc',
         {u'@author' : u'secretary', u'@doctype' : u'minutes',
          u'@date' : u'#2016-08-24'}), #4
        ('home/work/meetings/weekly_2017_08_31.doc',
         { u'@author' : u'secretary', u'@doctype' : u'minutes',
           u'@date' : u'#2017-08-31'}), #5
        ('home/work/events/letter_host.doc',
         { u'@author' : u'me', u'@doctype' : u'letter',
           u'@recipient' : u'ruby_hotel', u'@date' : u'#2016-06-15'}), #6
        ('home/work/projects/ginzoo2000/', #TODO: handle folder 
         {u'@project': u'ginzoo2000', '@date':'#2014-09-02'}), #7
        ]

    BAD_MDATA_SET_MIXED_ATYPES = [
        ('home/music/favorite_tune.ogg', {'rating':5}),
        ('home/music/crap_tune.ogg', {'rating':'0'})
    ]
    
    # Queries
    GOOD_QUERIES = [(u'@author=me @doctype=letter',
                        [GOOD_MDATA_SET[0][0],GOOD_MDATA_SET[6][0]]),
                       (u'@doctype=minutes @date<2017 @date>=2015',
                        [e[0] for e in GOOD_MDATA_SET[2:5]]),
                       (u'@date>=2016 @date<2017',
                        [GOOD_MDATA_SET[i][0] for i in [1,3,4,6]]),
                       (u'@date<=2016-08-17 @author=secretary',
                        [e[0] for e in GOOD_MDATA_SET[2:4]]),
                       (u'!me', [GOOD_MDATA_SET[i][0] for i in [2,3,4,5,7]]),
                       (u'@author=!me',
                        [GOOD_MDATA_SET[i][0] for i in [2,3,4,5]]),
                       (u'@file_type=folder @project=ginzoo2000',
                        [e[0] for e in GOOD_MDATA_SET[7:8]])
    ]
    
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
       shutil.rmtree(self.tmp_dir)

    def assert_file_exists(self, fn):
        if not op.exists(fn):
            raise Exception('File %s does not exist' %fn)
        
    def _create_tmp_files(self, fns, size=DEFAULT_FILE_SIZE, contents=None):
        """
        Create files from given filenames in the current temporary directory
        (see self.tmp_dir).
        If *contents* is None then file content is filled with random bytes up 
        to given *size* in bytes.
        """
        if contents is not None:
            assert(len(contents) == len(fns))
        else:
            contents = [os.urandom(size) for fn in fns]

        fns = [op.join(self.tmp_dir,fn) for fn in fns]
        for fn, content in zip(fns, contents):
            d = op.dirname(fn)
            if not op.exists(d):
                os.makedirs(d)
            with open(fn, 'wb') as fout:
                fout.write(content)

        return fns
    
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

        Output: None
        """

        if not fn.endswith('/'):
            self._create_tmp_files([fn+'.mdf', fn],
                                   contents=[json.dumps(metadata),
                                             os.urandom(Test.DEFAULT_FILE_SIZE)])
        else:
            dname = op.join(self.tmp_dir, fn)
            if not op.exists(dname):
                os.makedirs(dname)
            self._create_tmp_files([fn[:-1]+'.mdf'],
                                   contents=[json.dumps(metadata)])            
        

    def test_json_validity(self):
        metadata = Metadata()
        metadata.load_json(Test.GOOD_JSON)

        with self.assertRaises(InvalidJsonValue):
            metadata.load_json(Test.BAD_JSON_NESTED)

        with self.assertRaises(InvalidJsonAttributeDuplicate):
            metadata.load_json(Test.BAD_JSON_ATTR_DUPLICATE)

        with self.assertRaises(InvalidJsonValue):
            bad_json = Test.BAD_JSON_NON_HOMOGENEOUS_VALUES
            metadata.load_json(bad_json)
            
        with self.assertRaises(InvalidJsonStructure):
            bad_json = Test.BAD_JSON_NO_DICT
            metadata.load_json(bad_json)

    def test_attribute_validity(self):
        good_attribute = '@the_good_attribute'
        self.assertTrue(Metadata.attribute_is_valid(good_attribute))
        for char in Test.BAD_CHAR_ATTR:
            bad_attribute = '@attribute_%s' % char
            self.assertFalse(Metadata.attribute_is_valid(bad_attribute))

    def test_value_validity(self):
        for char in Test.BAD_CHAR_VAL:
            bad_value = 'value_%s' % char
            self.assertFalse(Metadata.value_is_valid(bad_value))
            
    def test_json_attribute_validity(self):
        for char in Test.BAD_CHAR_ATTR:
            with self.assertRaises(InvalidJsonAttributeFormat):
                bad_json = Test.JSON_SINGLE_ATTR_APAT % char
                Metadata().load_json(bad_json)

    def test_json_value_validity(self):
        for char in Test.BAD_CHAR_VAL:
            with self.assertRaises(InvalidJsonValue):
                bad_json = Test.JSON_SINGLE_ATTR_VPAT % char
                Metadata().load_json(bad_json)                

    def test_good_mdf_loading(self):        
        fns = self._create_tmp_files([op.join('base_dir', 'test.data'),
                                      op.join('base_dir', 'test.data.mdf')],
                                     contents=[os.urandom(Test.DEFAULT_FILE_SIZE),
                                               Test.GOOD_JSON])

        metadata = Metadata().load_mdf_file(fns[1])

        # Check user-defined metadata:
        self.assertEquals(metadata['@attribute_with_one_value'],
                          u'value_string_1')
        self.assertItemsEqual(metadata['@attribute_with_several_values'],
                              [u'val_str_2', u'val_str_3']) #py2 only
        self.assertEquals(metadata['@attribute_with_numerical_values'],
                          [4, 8, 15, 16, 23, 42])
        self.assertEquals(metadata['@attribute_with_numerical_value'], 45.6)
        self.assertEquals(metadata['@attribute_with_boolean_value'], False)
        self.assertEquals(metadata['@attribute_with_date'],
                          iso8601.parse_date('2015-06-04'))
        self.assertEquals(len(metadata), 6)        

    def test_mdf_loading_no_datafile(self):        
        fns = self._create_tmp_files([op.join('base_dir', 'test.data.mdf')],
                                     contents=[Test.GOOD_JSON])
        with self.assertRaises(IOError):
            Metadata().load_mdf_file(fns[0])

    def test_folder_loading(self):

        # create data with metadata
        for fn, md in Test.GOOD_MDATA_SET:
            self._create_tmp_mdf_file(fn, md)
        # create data with no metada
        self._create_tmp_files(['home/work/dummy.txt',
                                'home/work/meetings/dummy.txt'])

        metadata = Metadata.from_folder(self.tmp_dir)

        self.assertEquals(metadata.get_nb_entries(), len(Test.GOOD_MDATA_SET))
        
        mdata_set = copy.deepcopy(Test.GOOD_MDATA_SET) # dates will be modified
        for fn, md in mdata_set:
            for k in list(md):
                if isinstance(md[k], string_types) and  md[k].startswith('#'):
                    md[k] = iso8601.parse_date(md[k][1:])
            for fs_attr, md_getter in viewitems(Metadata.FS_STAT_ATTRS):
                md[fs_attr] = md_getter(op.join(self.tmp_dir, fn))
            self.assertEquals(metadata.get(op.join(self.tmp_dir, fn)), md)

    def test_query(self):

        # create data with metadata
        for fn, md in Test.GOOD_MDATA_SET:
            self._create_tmp_mdf_file(fn, md)
        # create data with no metada
        self._create_tmp_files(['home/work/dummy.txt',
                                'home/work/meetings/dummy.txt'])

        metadata = Metadata.from_folder(self.tmp_dir)

        for predicate, expected_selection in Test.GOOD_QUERIES:
            print 'testing query:', predicate
            selection = metadata.query(predicate).get_files()
            expected_selection = [op.normpath(op.join(self.tmp_dir, fn))
                                  for fn in expected_selection]
            self.assertItemsEqual(selection, expected_selection)

    def test_folder_selection(self):
        pass  

### Exceptions ###

class InvalidJsonContent(Exception):
    def __init__(self, message, errors):
        super(InvalidJsonContent, self).__init__(message)
        self.errors = errors

class InvalidJsonStructure(Exception):
    pass

class InvalidJsonAttributeFormat(Exception):
    pass

class InvalidJsonAttributeDuplicate(Exception):
    pass

class InvalidJsonValue(Exception):
    pass

class InconsistentValue(Exception):
    pass

### Misc tools ###

class IndexRegister:
    """ Compactly provide unique positive integers """
    def __init__(self):
        self._next_int = 0
        self._released = set([])

    def next(self):
        """ Return the next available integers """
        if len(self._released) == 0:
            next_one = self._next_int
            self._next_int += 1
        else:
            next_one = self._released.pop()
        return next_one

    def release(self, i):
        """ Make given integer be usable again """
        assert(i < self._next_int)
        self._released.add(i)


        

    
### For script call ###
    
def main():
    pass
    
if __name__ == '__main__':
    main()
    
