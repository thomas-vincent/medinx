import os
import os.path as op
import re

import json
import jsonschema
import iso8601
from datetime import datetime
from iso8601 import parse_date

import warnings
import logging
logger = logging.getLogger('medinx')

import inspect

MDF_EXTENSION = '.mdf'
ATTRIBUTE_FORMAT = r'[^\d\W]\w*' 
ATTRIBUTE_RE = re.compile(r'^%s$' % ATTRIBUTE_FORMAT, re.UNICODE)
VALUE_FORMAT = r'#?[a-zA-Z0-9_\-+:.@]+'
VALUE_REGEXP = re.compile(r'^%s$' % VALUE_FORMAT, re.UNICODE)

MDF_JSON_SCHEMA = {
    'type' : 'object',
    'patternProperties' : {
        r'^%s$' % ATTRIBUTE_FORMAT : {
            'type': 'array',
            'items' : {
                'type' : ['number', 'string', 'boolean']
            }
        }
    }
}

PRED_ATTR_VAL_FMT = r'(?P<attr>{attr})(?P<op_bin>=|(?:!=)|(?:>=)|(?:<=)|<|>)' \
                     '(?P<aval>{val})'.format(attr=ATTRIBUTE_FORMAT,
                                              val=VALUE_FORMAT)
PRED_ATTR_VAL_RE = re.compile(PRED_ATTR_VAL_FMT, re.UNICODE)
        
PREDICATE_FORMAT = r'\s?(?:(?:%s)|(?:(?P<op_una>[!]?)(?P<val>%s)))\s?' % \
                    (PRED_ATTR_VAL_FMT, VALUE_FORMAT)

PREDICATE_RE = re.compile(r'^%s$' % PREDICATE_FORMAT, re.UNICODE)

PREDICATES_RE = re.compile(r'^(?:%s)*$' % PREDICATE_FORMAT, re.UNICODE)

def parse_folder(path):
    """ 
    Helper function to recursevely parse folder.
    See MetadataIndex.from_folder
    """
    return MetadataIndex.from_folder(path)

def _load_metadata(md_fn):
    """
    Load metadata from JSON file and ensure that the associated file or folder
    exists. Also add filesystem metada (TODO): 
        - file_type (either 'file' or 'folder')
        - file_modification_date (datetime object)

    Output: tuple(associated file, metadata dict)
    """
    associated_fn = op.splitext(md_fn)[0]
    if not op.exists(associated_fn):
        raise IOError('Associated file not found: %s' % associated_fn)
        
    with open(md_fn, 'r') as fin:
        md = load_json(fin.read())
    
    return (associated_fn, md)
            
def _save_metadata(md_fn, md):
    formatted_md = {}
    for a,vs in md.items():
        if isinstance(vs[0], datetime):
            vs = [format_value_date(v) for v in vs]
        formatted_md[a] = vs

    with open(md_fn, 'w', encoding='utf-8') as fout:
        json.dump(formatted_md, fout, ensure_ascii=False, indent=4)

def load_json(json_content):
    """
    Load and check that json content complies with medinx format.
    Raise InvalidJson<...> exceptions if not.

    Args:
        - json_content (str): raw json content, MDF format
    """
    def dict_read(pairs):
        """ Simply check for duplicate attributes """
        d = {}
        duplicates = []
        for attribute, values in pairs:
            if attribute in d:
                duplicates.append(attribute)
            d[attribute] = values
            
        if len(duplicates) > 0:
            msg = 'Duplicate attributes: "%s"' % ', '.join(duplicates)
            raise InvalidJsonAttributeDuplicate(msg)

        return d
    
    def fix_type(mdata):
        """
        Check json againt MDF schema (see MDF_JSON_SCHEMA). 
        Check strings, check and convert dates, convert int to float. 
        Check that type is homogeneous for all values in array associated to
        any attribute.
        """
        
        errors = []
        for attribute, values in mdata.items():
            fixed_values = []
            for value in values:
                if isinstance(value, str):
                    if VALUE_REGEXP.match(value) is None:
                        msg = 'Invalid value: %s' % value
                        errors.append(InvalidJsonValue(msg))
                    if value.startswith('#'):
                        try:
                            value = parse_date(value[1:])
                        except iso8601.ParseError:
                            msg = 'Invalid date value: %s' % value
                            errors.append(InvalidJsonValue(msg))
                    fixed_values.append(value)
                elif not isinstance(value, bool) and isinstance(value, int):
                    fixed_values.append(float(value))                
                else:
                    fixed_values.append(value)
                    
            if not all(type(v)==type(fixed_values[0]) for v in fixed_values):
                msg = 'Value type is not homogeneous for attribute %s.' \
                      % attribute
                errors.append(InconsistentValue(msg))
                    
            mdata[attribute] = fixed_values
                    
        if len(errors) > 0:
            if len(errors) > 1:
                raise InvalidJsonContent('Errors in JSON content', errors)
            else:
                raise errors[0]
            
        return mdata

    loaded = json.loads(json_content, object_pairs_hook=dict_read)
    jsonschema.validate(loaded, MDF_JSON_SCHEMA)

    return fix_type(loaded)


## Formatting and unformatting functions

def format_str_list(l):
    return '[' + ', '.join(l) + ']'

def format_values_float(values):
    return format_str_list(['%s'%v for v in values])

def format_values_str(values):
    return format_str_list(values)

def format_values_bool(values):
    return format_str_list(['%s'%v for v in values])

def format_value_date(value):
    return '#' + value.isoformat('T')

def format_values_date(values):
    return format_str_list([format_value_date(v) for v in values])

def format_values(values):
    """
    WARNING: type unsafe
    ASSUME: all values are of the same type (not checked).
    """
    if len(values) == 0:
        return format_values_str([])
    
    if isinstance(values[0], float):
        return format_values_float(values)
    elif isinstance(values[0], bool):
        return format_values_bool(values)
    elif isinstance(values[0], str):
        return format_values_str(values)
    elif isinstance(values[0], datetime):
        return format_values_date(values)
    else:
        raise TypeError('Unsupported type %s' % str(type(values[0])))

def unformat_str_list(s):
    return [e.strip() for e in s.strip('[]').split(',') if len(e) > 0]
    
def unformat_values_float(s):
    return [float(v) for v in unformat_str_list(s)]

def unformat_values_str(values):
    return unformat_str_list(values)

def unformat_values_bool(values):
    return [v.lower()=='true' for v in unformat_str_list(values)]

def unformat_values_date(values):
    return [parse_date(v.strip('#')) for v in unformat_str_list(values)]

unformatters = {
    str : unformat_values_str,
    float : unformat_values_float,
    bool : unformat_values_bool,
    datetime : unformat_values_date,
}
def unformat_values(values, attribute_type):
    try:
        return unformatters[attribute_type](values)
    except KeyError:
        raise TypeError('Unsupported type %s' % str(attribute_type))
    
## Main class 
class MetadataIndex:
    """
    Metadata index for pathes and associated metadata.
    Can be filtered according to criteria on metadata.

    Parts of the specification that are not supported:
    - value-based search with negation.
    - file-system metadata are not extracted
    - tree-view is not implemented

    Slow implementation: all entries are scanned during queries.
    """

    STR_TO_COMPARATOR = {
        '=' : lambda v,tv: v==tv,
        '' : lambda v,tv: str(v)==str(tv), # value-based search
        '>' : lambda v,tv: v>tv,
        '<' : lambda v,tv: v<tv,
        '>=' : lambda v,tv: v>=tv,
        '<=' : lambda v,tv: v<=tv,
        '!=' : lambda v,tv: v!=tv,
#        '!' : lambda v,tv: str(v)!=str(tv), # value-based search (negation)
    }

    
    def __init__(self, path_and_mdata_list):
        """ IMPORTANT: given path_and_mdata_list is not checked for type consistency etc. """
        self._file_table = path_and_mdata_list

        self.attribute_types = {}
        for fn, md in self._file_table:
            for attr, values in md.items():
                if len(values) > 0:
                    if attr in self.attribute_types and \
                       self.attribute_types[attr] != type(values[0]):
                            msg = 'Inconsistent Value type for %s of file %s. ' \
                                  'Should be %s instead of %s' % \
                                  (attr, fn, self.attribute_types[attr], type(values[0]))
                            raise InconsistentValue(msg)
                    elif self.attribute_types.get(attr, None) is None:
                        self.attribute_types[attr] = type(values[0])
                else:
                    self.attribute_types[attr] = None

        if any([atype is None for atype in self.attribute_types.values()]):
            logger.warn('No value associated with attribute %s for any file.' % atype)
            
    @staticmethod
    def from_folder(path):

        if not op.exists(path):
            raise FileNotFoundError(path)

        # Recursively walk path and extract metadata from each .mdf file found
        file_table = []
        for root, dirs, bfns in os.walk(path):
            for bfn in bfns:
                if bfn.endswith(MDF_EXTENSION):
                    file_table.append(_load_metadata(op.join(root, bfn)))
        return MetadataIndex(file_table)

    def get_attributes(self):
        return sorted(self.attribute_types.keys())

    def get_attribute_types(self):
        return self.attribute_types
    
    def get_files(self):
        """ Return all indexed files names """
        return [fn for fn, md in self._file_table]

    def get_metadata(self, fn):
        for _fn, md in self._file_table:
            if _fn == fn:
                return md
        return {}

    def set_metadata_attr(self, fn, attr, values):

        # Check that all given value have same type:
        if any(type(v) != type(values[0]) for v in values):
            raise InconsistentValue('Non-homogeneous type in given values.')

        for _fn, md in self._file_table:
            if _fn == fn:
                if len(values) > 0:
                    # If new or undefined attribute:
                    if self.attribute_types.get(attr, None) is None:
                        self.attribute_types[attr] = type(values[0])

                    # Check type consistency:
                    if self.attribute_types[attr] != type(values[0]):
                        msg = 'Inconsistent value type: %s. Should be %s' % \
                              (str(type(values[0])), str(self.attribute_types[attr]))
                        raise InconsistentValue(msg)
                    
                md[attr] = values
                return
        raise FileNotFoundError(fn)

    def save(self):
        """
        Save metadata in .mdf files.
        """
        
        for fn, md in self._file_table:
            if len(md) > 0:
                mdf_fn = fn + MDF_EXTENSION
                _save_metadata(mdf_fn, md)
                
    ## Query ##
    
    def filter(self, criteria):
        """ Return a filtered view of the index.
        If criteria are invalid, raises InvalidSelectionPredicates
        """
        if not PREDICATE_RE.match(criteria):
            raise InvalidPredicateFormat('Invalid filter criteria: %s' % \
                                         criteria)

        predicates = [self.unformat_predicate(c) for c in criteria.split(' ')]
        filtered_table = []
        for fn, md in self._file_table:
            predicate_valid = []
            logger.debug('Scanning entry: %s', fn) 
            for predicate in predicates:
                predicate_valid.append(False)
                logger.debug('  Trying predicate: %s', predicate) 
                for attr, values in md.items():
                    logger.debug('    on  %s(%s): %s', attr, str(type(values[0])), values)
                    if any(predicate(attr, value) for value in values):
                        logger.debug('    -> OK') 
                        predicate_valid[-1] = True
                        break
                    else:
                        logger.debug('    -> NO MATCH') 
                if not predicate_valid[-1]:
                    break
            if all(predicate_valid):
                filtered_table.append((fn, md))
        return MetadataIndex(filtered_table)

    def unformat_predicate(self, criterion):
        """ 
        Create a callable from given string criterion.
        Criterion is of the form:
          - <attribute><operator><value>, where operator is one of "=", "!=",
            "<", ">", "<=", ">=".
          - [!]<value>

        ASSUME: criterion is valid (has already been checked).

        NOTE: weak-type version, where attributes can have different types
              on different index entries.

        Return a callable with args (attribute, value) to a be applied on a single
        indexed metadata entry and returning True if predicate is verified, else False.
        """
        # Parse criterion
        match = PREDICATE_RE.search(criterion)
        logger.debug('Unformatting criterion: %s', criterion)
        if match.group('op_bin') is not None:
            # Attribute and value have to match
            value_matches = MetadataIndex.STR_TO_COMPARATOR[match.group('op_bin')]
            attribute_matches = lambda a, ta: a==ta
            queried_attribute = match.group('attr')
            queried_value = match.group('aval')            
        elif match.group('op_una') is not None:
            # Only value has to match:
            value_matches = MetadataIndex.STR_TO_COMPARATOR[match.group('op_una')]
            attribute_matches = lambda a, ta: True # attribute is ignored
            queried_attribute = None
            queried_value = match.group('val')
    
        logger.debug('  amatch: %s', inspect.getsource(attribute_matches))
        logger.debug('    queried_attr: %s', queried_attribute)
        logger.debug('  vmatch: %s', inspect.getsource(value_matches))
        logger.debug('    queried_value: %s', queried_value)
        
        return Predicate(queried_attribute, queried_value, attribute_matches, value_matches)
    
class Predicate:
    def __init__(self, queried_attribute, queried_value, attribute_matches, value_matches):
        """
        Args:
            - queried_attribute (str): extracted from query cretirion.
                                       If None, then str values will be considered.
                                       (value-based search)
            - queried_value (str): unformatted value, extracted from query cretirion
        """
        self.queried_attribute = queried_attribute
        self.queried_value = queried_value
        self.attribute_matches = attribute_matches
        self.value_matches = value_matches

    def __call__(self, indexed_attr, indexed_val):
        """ 
        Applied predicate to given index entry.

        Args:
            - indexed_attr (str): attribute that value *v* is associated with
            - indexed_val (typed): value associated with attribute *a*
        """
        # convert queried_value to type of value in indexed metadata:
        if not self.attribute_matches(indexed_attr, self.queried_attribute):
            return False

        if self.queried_attribute is not None: # attr & value query
            if isinstance(indexed_val, datetime):
                queried_value = parse_date(self.queried_value.strip('#'))
            elif isinstance(indexed_val, bool):
                queried_value = self.queried_value.lower() == 'true'
            else:
                queried_value = type(indexed_val)(self.queried_value)
        else: # Value-based query -> ASSUME string-only
            queried_value = self.queried_value
            
        return self.value_matches(indexed_val, queried_value)
    
class InvalidPredicateFormat(Exception):
    pass
    
class InvalidJsonAttributeFormat(Exception):
    pass

class InvalidJsonAttributeDuplicate(Exception):
    pass

class InvalidJsonValue(Exception):
    pass

class InconsistentValue(Exception):
    pass
