import unittest
from nose_parameterized import parameterized
from mock import MagicMock
from mock import mock_open
from mock import patch
import re
import __builtin__
import os

from churada.core import LocalTorrent
import logging

tfile_1 = """d8:announce21:http://www.tracker.ca13:announce-listll10:announce-110:announce-2ee13:creation datei10000e7:comment4:blah10:created by7:creator4:infod4:name15:single_file.ext6:lengthi100e12:piece lengthi1000e6:pieces20:123456789012345678907:privatei1eee"""

tfile_1_dict = {'announce':'http://www.tracker.ca',
                     'announce-list':[['announce-1','announce-2']],
                     'creation date':10000,
                     'comment':'blah',
                     'created by':'creator',
                     'info':{'name':'single_file.ext',
                             'length':100,
                             'piece length':1000,
                             'pieces':'12345678901234567890',
                             'private':1
                            }
               }


tfile_2 = """d8:announce21:http://www.tracker.us13:announce-listll10:announce-310:announce-4ee13:creation datei1234e7:comment3:ayy10:created by3:idk4:infod4:name15:other_file.ext26:lengthi1024e12:piece lengthi12345e6:pieces40:12345678901234567890abcdefghijklmnopqrst7:privatei1eee"""
 
tfile_2_dict = {'announce':'http://www.tracker.us',
                'announce-list':[['announce-3','announce-4']],
                'creation date':1234,
                'comment':'ayy',
                'created by':'idk',
                'info':{'name':'other_file.ext2',
                        'length':1024,
                        'piece length':12345,
                        'pieces':'12345678901234567890abcdefghijklmnopqrst',
                        'private':1
                       }
               }

                    
tfile_3 = """d8:announce21:http://www.tracker.en13:announce-listll10:announce-510:announce-6ee13:creation datei3456e7:comment4:lmao4:infod4:name14:data_directory12:piece lengthi123e6:pieces60:0123456789012345678901234567890123456789012345678901234567897:privatei0e5:filesld6:lengthi2000e4:pathl7:subdir17:subdir25:file1eed6:lengthi3200e4:pathl7:subdir17:subdir35:file2eeeee"""

tfile_3_dict = {'announce':'http://www.tracker.en',
                'announce-list':[['announce-5','announce-6']],
                'creation date':3456,
                'comment':'lmao',
                'info':{'name':'data_directory',
                        'piece length':123,
                        'pieces':'012345678901234567890123456789012345678901234567890123456789',
                        'private':0,
                        'files':[{'length':2000,
                                  'path':['subdir1','subdir2','file1']},
                                 {'length':3200,
                                  'path':['subdir1','subdir3','file2']}]
                       }
               }

tfile_4 = """d4:infod4:name15:single_file.ext6:pieces0:6:lengthi55eee"""

tfile_zero = """d4:infod4:name:0:6:pieces0:6:lengthi0eee"""

timestamp = 42


import churada
class LocalTorrentTest(unittest.TestCase):
    def setUp(self):
        self.patcher_isfile = patch('churada.core.os.path.isfile', return_value=True)
#        self.patcher_isdir = patch.object(churada.core.os.path,'isdir')
#        self.patcher_exists = patch.object(churada.core.os.path,'exists')
        self.patcher_getsize = patch('churada.core.os.path.getsize', return_value=0)
#        self.patcher_move = patch.object(churada.core.os.path,'move')
        self.mock_isfile = self.patcher_isfile.start()
#        self.mock_isdir = self.patcher_isdir.start()
#        self.mock_exists = self.patcher_exists.start()
        self.mock_getsize = self.patcher_getsize.start()
#        self.mock_move = self.patcher_move.start()
        # Defaults for successful ltor creation
#        self.patcher = patch('churada.core.os')
#        self.os = self.patcher.start()
#        self.os.path.getsize.return_value = 0
#        self.os.path.isfile.return_value = True
#        self.os.path.isdir.return_value = False
#        self.os.path.exists.return_value = True
#        self.os.path.normpath = os.path.normpath
#        self.os.path.isabs = os.path.isabs
#        self.os.path.join = os.path.join
#        self.os.path.dirname = os.path.dirname
#        self.os.path.basename = os.path.basename
    @parameterized.expand([
        ("parse_1",tfile_1,tfile_1_dict),
        ("parse_2",tfile_2,tfile_2_dict),
        ("parse_3",tfile_3,tfile_3_dict)
        ])
    def parse_test(self,_,bencode,control):
        src = LocalTorrent.tokenize(bencode)
        parsed = LocalTorrent.parse_bencode(src.next,src.next())
        self.assertEqual(parsed,control)
    @parameterized.expand(
       [("equal_1",tfile_1,'/path',tfile_1,'/path',True),
        ("equal_2",tfile_2,'/path',tfile_2,'/path',True),
        ("equal_3",tfile_3,'/path',tfile_3,'/path',True),
        ("not_equal_1",tfile_1,'/path1',tfile_2,'/path2',False),
        ("not_equal_2",tfile_2,'/path1',tfile_3,'/path2',False),
        ("not_equal_3",tfile_3,'/path1',tfile_1,'/path2',False),
        ("equal_4",tfile_1,'/path1',tfile_1,'/path2',True),
        ("equal_5",tfile_1,'/path1',tfile_2,'/path1',True),
        ("equal_6",tfile_4,'/path',tfile_1,'/path',True)]
       )
    def eq_ne_test(self,_,tfile1,path1,tfile2,path2,eq_flag):
        with patch("__builtin__.open", mock_open(read_data=tfile1)) as m:
            ltor1 = LocalTorrent(path1)
        with patch("__builtin__.open", mock_open(read_data=tfile2)) as m:
            ltor2 = LocalTorrent(path2)
        self.assertEqual(ltor1.__eq__(ltor2), eq_flag)
        self.assertEqual(ltor1.__ne__(ltor2), not eq_flag)
    @parameterized.expand(
       [("nonzero_1",tfile_1,'/path',True),
        ("nonzero_2",tfile_2,'/path',True),
        ("nonzero_3",tfile_3,'/path',True),
        ("zero_path",tfile_1,'',False),
        ("zero_name",tfile_zero,'/path',False)])
    def nonzero_test(self,_,tfile,path,nonzero_flag):
        with patch("__builtin__.open", mock_open(read_data=tfile)) as m:
            ltor = LocalTorrent(path)
        self.assertEqual(ltor.__nonzero__(),nonzero_flag)
    @parameterized.expand(
      [("lambda_1",tfile_1,'/path',{'key':'size','func':lambda x: x > 3},True),
       ("lambda_2",tfile_1,'/path',{'key':'size','func':lambda x: x < 3},False),
       ("lambda_3",tfile_1,'/path',{'key':'announce','func':lambda x: x == 'http://www.tracker.ca'},True),
       ("regex_1",tfile_1,'/unique',{'key':'path','func':lambda x: bool(re.search('que',x))},True),
       ("regex_2",tfile_2,'/path',{'key':'announce','func':lambda x: bool(re.search('ca',x))},False),
       ("regex_3",tfile_3,'/path',{'key':'comment','func':lambda x: bool(re.match('lmao',x))},True)]
       )
    def query_test(self,_,tfile,path,func_args,query_flag):
        with patch("__builtin__.open", mock_open(read_data=tfile)) as m:
            ltor = LocalTorrent(path)
        result = ltor.query(**func_args)
        self.assertEqual(result,query_flag)
    @parameterized.expand(
            [("move_dir_1",tfile_1,("/dir1/path.e","/dir2/dest","/dir2/dest/path.e"),
                 {'dest_isfile':False,'dest_isdir':True,'mvdest_exists':False,'call_move':True})
        #     ("move_dir_2",tfile_1,("/dir1/path.e",)

                                
            ])
    def move_test(self,_,tfile,paths,flags):
        path,dest,path_ = paths
        with patch("__builtin__.open", mock_open(read_data=tfile)) as m:
            ltor = LocalTorrent(path)
        self.mock_isfile.return_value = flags['dest_isfile']
        self.mock_isdir.return_value = flags['dest_isdir']
        self.mock_exists.return_value = flags['mvdest_exists']
#        ltor.move(dest)
        self.assertEquals(ltor.path,path_)
        if flags['call_move']:
            self.os.path.move.assert_called_once_with(path,path_)
        else:
            self.assertEqual(self.os.path.move.called,False)
    def tearDown(self):
        self.patcher_isfile.stop()
#        self.patcher_isdir.stop()
#        self.patcher_exists.stop()
        self.patcher_getsize.stop()
#        self.patcher_move.stop()
