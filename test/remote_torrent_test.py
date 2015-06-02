import unittest
from nose_parameterized import parameterized
from mock import patch

from churada.core import RemoteTorrent
import logging

# representative text dumps are given below based on torrent status
# there also exist states: "Allocating", "Checking", "Queued"
# these states should be rare, and should act similar to other non-active cases
# e.g. paused, error

timestamp = 42

info_seeding = """Name: Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash
ID: 484d0948198cedc854d69091ae48f7502a54b7f1
State: Seeding Up Speed: 44.9 KiB/s
Seeds: 0 (86) Peers: 1 (6) Availability: 0.00
Size: 14.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 67 days 15:44:47 Active: 67 days 16:09:22
Tracker status: landof.tv: Announce OK"""

dict_seeding = {'name':"Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash",
                'id':"484d0948198cedc854d69091ae48f7502a54b7f1",
                'state':'Seeding',
                'uspeed':float(45977),
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
                'tracker':'landof.tv',
                'tracker_status':"Announce OK",
                'time':timestamp}

info_paused = """Name: Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash
ID: 484d0948198cedc854d69091ae48f7502a54b7f1
State: Paused
Size: 14.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 67 days 15:44:47 Active: 67 days 16:09:22
Tracker status: landof.tv: Announce OK"""

dict_paused = {'name':"Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash",
               'id':"484d0948198cedc854d69091ae48f7502a54b7f1",
               'state':'Paused',
               'csize':float(15461882265),
               'tsize':float(15461882265),
               'ratio':float(3.237),
               'stime':float(5845487),
               'atime':float(5846962),
               'tracker':'landof.tv',
               'tracker_status':"Announce OK",
               'time':timestamp}

info_checking = """Name: Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash
ID: 484d0948198cedc854d69091ae48f7502a54b7f1
State: Checking
Size: 6.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 67 days 15:44:47 Active: 67 days 16:09:22
Tracker status: landof.tv: Announce OK"""

dict_checking = {'name':"Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash",
                 'id':"484d0948198cedc854d69091ae48f7502a54b7f1",
                 'state':'Checking',
                 'csize':float(6871947673),
                 'tsize':float(15461882265),
                 'ratio':float(3.237),
                 'stime':float(5845487),
                 'atime':float(5846962),
                 'tracker':'landof.tv',
                 'tracker_status':"Announce OK",
                 'time':timestamp}

info_error = """Name: Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash
ID: 484d0948198cedc854d69091ae48f7502a54b7f1
State: Error
Size: 6.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 67 days 15:44:47 Active: 67 days 16:09:22
Tracker status: landof.tv: Announce OK"""

dict_error = {'name':"Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash",
              'id':"484d0948198cedc854d69091ae48f7502a54b7f1",
              'state':'Error',
              'csize':float(6871947673),
              'tsize':float(15461882265),
              'ratio':float(3.237),
              'stime':float(5845487),
              'atime':float(5846962),
              'tracker':'landof.tv',
              'tracker_status':"Announce OK",
              'time':timestamp}

info_downloading = """Name: Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash
ID: 484d0948198cedc854d69091ae48f7502a54b7f1
State: Downloading Down Speed: 16.8 MiB/s Up Speed: 44.9 KiB/s
Seeds: 13 (86) Peers: 1 (6) Availability: 21.33
Size: 6.4 GiB/14.4 GiB Ratio: 3.237
Seed time: 0 days 00:00:00 Active: 67 days 16:09:22
Tracker status: landof.tv: Announce OK
Progress: 44.4% [#####~~~~]"""

dict_downloading = {'name':"Steven.Universe.S01.720p.WEB-DL.AAC2.0.H.264-RainbowCrash",
                    'id':"484d0948198cedc854d69091ae48f7502a54b7f1",
                    'state':'Downloading',
                    'dspeed':float(17616076),
                    'uspeed':float(45977),
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
                    'tracker':'landof.tv',
                    'tracker_status':"Announce OK",
                    'progress':float(44.4),
                    'time':timestamp}


class RemoteTorrentTest(unittest.TestCase):
    def setUp(self):
        pass
    @parameterized.expand(
       [("seeding",[info_seeding,timestamp],dict_seeding),
        ("paused",[info_paused,timestamp],dict_paused),
        ("checking",[info_checking,timestamp],dict_checking),
        ("error",[info_error,timestamp],dict_error),
        ("downloading",[info_downloading,timestamp],dict_downloading)]
       )
    @patch('logging.getLogger')
    def parse_test(self,_,func_args,control,mock_logger):
        rtor = RemoteTorrent(*func_args)
        for key in control:
            self.assertEqual(control[key],rtor.__dict__[key])
        mock_logger.assert_called_once_with("RemoteTorrent")
        self.assertEqual(rtor.time,timestamp)
    def eq_test(self):
        pass
    def ne_test(self):
        pass
    def nonzero_test(self):
        pass
    def query_test(self):
        pass
