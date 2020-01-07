import os.path as op
import os
import json

import medinx
import medinx.ui as mdx_ui
import tempfile
import shutil

from PyQt5 import QtWidgets
import sys

def main():
    # tmp_dir = tempfile.mkdtemp(prefix='medinx_tmp_')
    tmp_dir = '/home/tom/test/medinx/'

    if not op.exists(tmp_dir):
        dump_test_files(tmp_dir)
    app = QtWidgets.QApplication(sys.argv)
    main_widget = mdx_ui.MdataTableEditorMain(tmp_dir)
    main_widget.show()
    sys.exit(app.exec_())
    
    # shutil.rmtree(tmp_dir)
    
def dump_test_files(tmp_dir):
    test_data = [
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
            ('research/projects/big_one/bibliography/hahaha.pdf', {}),
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

    return [(create_tmp_mdf_file(fn, md, tmp_dir), md) for fn, md in test_data]

def create_tmp_mdf_file(fn, metadata, tmp_dir):
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
        file_size = 512
        if len(metadata)>0:
            create_tmp_files([fn+'.mdf'], tmp_dir, contents=[json.dumps(metadata)])
        return create_tmp_files([fn], tmp_dir, contents=['dummy_content'])[0]
    else:
        dname = op.join(tmp_dir, fn)
        if not op.exists(dname):
            os.makedirs(dname)
        if len(metadata)>0:
            create_tmp_files([fn[:-1]+'.mdf'], tmp_dir,
                                   contents=[json.dumps(metadata)])            
        return dname
    
def create_tmp_files(fns, tmp_dir, size=512, contents=None):
    """
    Create files from given filenames in the current temporary directory
    If *contents* is None then file content is filled with random bytes up 
    to given *size* in bytes.
    """
    if contents is not None:
        assert(len(contents) == len(fns))
        open_mode = 'w'
    else:
        contents = [os.urandom(size) for fn in fns]
        open_mode = 'wb'

    fns = [op.join(tmp_dir,fn) for fn in fns]
    for fn, content in zip(fns, contents):
        d = op.dirname(fn)
        if not op.exists(d):
            os.makedirs(d)
        with open(fn, open_mode) as fout:
            fout.write(content)

    return fns

if __name__ == '__main__':
    main()
