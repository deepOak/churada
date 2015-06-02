import unittest
from nose_parameterized import parameterized
from mock import MagicMock
from mock import patch
import re

from churada.core import RemoteTorrent
import logging

# representative text dumps are given below based on torrent status
# there also exist states: "Allocating", "Checking", "Queued"
# these states should be rare, and should act similar to other non-active cases
# e.g. paused, error


info_seeding = """Name: torrent_name
ID: abcdef1234567890
State: Seeding Up Speed: 44.9 KiB/s
Seeds: 0 (86) Peers: 1 (6) Availability: 0.00
Size: 14.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 67 days 15:44:47 Active: 67 days 16:09:22
Tracker status: tracker.ca: Announce OK"""

dict_seeding = {'name':"torrent_name",
                'id':"abcdef1234567890",
                'state':'Seeding',
                'dspeed':None,
                'uspeed':float(45977),
                'eta':None,
                'cseed':float(0),
                'tseed':float(86),
                'cpeer':float(1),
                'tpeer':float(6),
                'avail':float(0),
                'csize':float(15461882265),
                'tsize':float(15461882265),
                'ratio':float(3.237),
                'stime':float(5845487),
                'atime':float(5846962),
                'tracker':'tracker.ca',
                'tracker_status':"Announce OK",
                'progress':None,
                'score':(3.237)/(5.846962)}

info_paused = """Name: torrent_name
ID: abcdef1234567890
State: Paused
Size: 14.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 67 days 15:44:47 Active: 67 days 16:09:22
Tracker status: tracker.ca: Announce OK"""

dict_paused = {'name':"torrent_name",
               'id':"abcdef1234567890",
               'state':'Paused',
               'dspeed':None,
               'uspeed':None,
               'eta':None,
               'cseed':None,
               'tseed':None,
               'cpeer':None,
               'tpeer':None,
               'avail':None,
               'csize':float(15461882265),
               'tsize':float(15461882265),
               'ratio':float(3.237),
               'stime':float(5845487),
               'atime':float(5846962),
               'tracker':'tracker.ca',
               'tracker_status':"Announce OK",
               'progress':None,
               'score':(3.237)/(5.846962)}

info_checking = """Name: torrent_name
ID: abcdef1234567890
State: Checking
Size: 6.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 67 days 15:44:47 Active: 67 days 16:09:22
Tracker status: tracker.ca: Announce OK"""

dict_checking = {'name':"torrent_name",
                 'id':"abcdef1234567890",
                 'state':'Checking',
                 'dspeed':None,
                 'uspeed':None,
                 'eta':None,
                 'cseed':None,
                 'tseed':None,
                 'cpeer':None,
                 'tpeer':None,
                 'avail':None,
                 'csize':float(6871947673),
                 'tsize':float(15461882265),
                 'ratio':float(3.237),
                 'stime':float(5845487),
                 'atime':float(5846962),
                 'tracker':'tracker.ca',
                 'tracker_status':"Announce OK",
                 'progress':None,
                 'score':(3.237)/(5.846962)}

info_error = """Name: torrent_name
ID: abcdef1234567890
State: Error
Size: 6.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 67 days 15:44:47 Active: 67 days 16:09:22
Tracker status: tracker.ca: Announce OK"""

dict_error = {'name':"torrent_name",
              'id':"abcdef1234567890",
              'state':'Error',
              'dspeed':None,
              'uspeed':None,
              'eta':None,
              'cseed':None,
              'tseed':None,
              'cpeer':None,
              'tpeer':None,
              'avail':None,
              'csize':float(6871947673),
              'tsize':float(15461882265),
              'ratio':float(3.237),
              'stime':float(5845487),
              'atime':float(5846962),
              'tracker':'tracker.ca',
              'tracker_status':"Announce OK",
              'progress':None,
              'score':(3.237)/(5.846962)}

info_downloading = """Name: torrent_name
ID: abcdef1234567890
State: Downloading Down Speed: 16.8 MiB/s Up Speed: 44.9 KiB/s
Seeds: 13 (86) Peers: 1 (6) Availability: 21.33
Size: 6.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 0 days 00:00:00 Active: 67 days 16:09:22
Tracker status: tracker.ca: Announce OK
Progress: 44.4% [#####~~~~]"""

dict_downloading = {'name':"torrent_name",
                    'id':"abcdef1234567890",
                    'state':'Downloading',
                    'dspeed':float(17616076),
                    'uspeed':float(45977),
                    'eta':None,
                    'cseed':float(13),
                    'tseed':float(86),
                    'cpeer':float(1),
                    'tpeer':float(6),
                    'avail':float(21.33),
                    'csize':float(6871947673),
                    'tsize':float(15461882265),
                    'ratio':float(3.237),
                    'stime':float(0),
                    'atime':float(5846962),
                    'tracker':'tracker.ca',
                    'tracker_status':"Announce OK",
                    'progress':float(44.4),
                    'score':(3.237)/(5.846962)}


info_unique_title = """Name: unique_title
ID: abcdef1234567890
State: Downloading Down Speed: 16.8 MiB/s Up Speed: 44.9 KiB/s
Seeds: 13 (86) Peers: 1 (6) Availability: 21.33
Size: 6.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 0 days 00:00:00 Active: 67 days 16:09:22
Tracker status: tracker.ca: Announce OK
Progress: 44.4% [#####~~~~]"""

info_bad_state = """Name: x
ID: abcdef1234567890
State: x Down Speed: 16.8 MiB/s Up Speed: 44.9 KiB/s
Seeds: 13 (86) Peers: 1 (6) Availability: 21.33
Size: 6.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 0 days 00:00:00 Active: 67 days 16:09:22
Tracker status: tracker.ca: Announce OK
Progress: 44.4% [#####~~~~]"""

timestamp = 42

class RemoteTorrentTest(unittest.TestCase):
    @parameterized.expand(
       [("seeding",[info_seeding,timestamp],dict_seeding),
        ("paused",[info_paused,timestamp],dict_paused),
        ("checking",[info_checking,timestamp],dict_checking),
        ("error",[info_error,timestamp],dict_error),
        ("downloading",[info_downloading,timestamp],dict_downloading),
        ("empty_info",["",timestamp],{'name':None,'state':None}) ]
       )
    @patch('logging.getLogger')
    def parse_test(self,_,func_args,control,mock_logger):
        mock_logger.return_value = MagicMock()
        control.update({'time':timestamp,'logger':mock_logger.return_value})
        rtor = RemoteTorrent(*func_args)
        mock_logger.assert_called_once_with("RemoteTorrent")
        self.assertEqual(control,rtor.__dict__)
    @parameterized.expand( 
       [("self_1",info_seeding,info_seeding,True),
        ("self_2",info_unique_title,info_unique_title,True),
        ("equal_1",info_seeding,info_downloading,True),
        ("equal_2",info_seeding,info_paused,True),
        ("equal_3",info_seeding,info_checking,True),
        ("equal_4",info_seeding,info_error,True),
        ("not_equal_1",info_seeding,info_unique_title,False),
        ("not_equal_2",info_downloading,info_unique_title,False),
        ("not_equal_3",info_error,info_unique_title,False),
        ("not_equal_4",info_paused,info_unique_title,False),
        ("not_equal_5",info_checking,info_unique_title,False)]
       )
    def eq_ne_test(self,_,info_1,info_2,equal_flag):
        rtor_1 = RemoteTorrent(info_1,timestamp)
        rtor_2 = RemoteTorrent(info_2,timestamp)
        self.assertEqual(rtor_1 == rtor_2,equal_flag)
        self.assertEqual(rtor_1 != rtor_2,not equal_flag)
    @parameterized.expand(
       [("nonzero_1",info_seeding,True),
        ("nonzero_2",info_downloading,True),
        ("nonzero_3",info_error,True),
        ("nonzero_4",info_paused,True),
        ("nonzero_5",info_checking,True),
        ("nonzero_6",info_unique_title,True),
        ("zero_1","",False),
        ("zero_2",info_bad_state,False)]
       )
    def nonzero_test(self,_,info,nonzero_flag):
        rtor = RemoteTorrent(info,timestamp)
        self.assertEqual(bool(rtor),nonzero_flag)
    @parameterized.expand(
      [("lambda_1",info_downloading,{'key':'tpeer','func':lambda x: x > 3},True),
       ("lambda_2",info_downloading,{'key':'tpeer','func':lambda x: x < 3},False),
       ("lambda_3",info_downloading,{'key':'tracker','func':lambda x: x == 'tracker.ca'},True),
       ("regex_1",info_downloading,{'key':'tracker','func':lambda x: bool(re.search('tracker',x))},True),
       ("regex_2",info_downloading,{'key':'tracker','func':lambda x: bool(re.search('ca',x))},True),
       ("regex_3",info_downloading,{'key':'tracker','func':lambda x: bool(re.search('what',x))},False)]
       )
    def query_test(self,_,info,func_args,query_flag):
        rtor = RemoteTorrent(info,timestamp)
        self.assertEquals(rtor.query(**func_args),query_flag)
