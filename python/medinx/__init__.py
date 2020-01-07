import sys
if sys.version_info[0] < 3:
    raise Exception('Python 3 or newer is required.')

from ._medinx import parse_folder, _load_metadata, format_values, unformat_values
from ._medinx import MetadataIndex

