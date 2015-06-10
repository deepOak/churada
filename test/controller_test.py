import unittest
from nose_parameterized import parameterized
from mock import MagicMock, patch
from copy import deepcopy

from churada.record import LocalRecord
from churada.rule import Rule
from churada.controller import Controller

from generators import ltor_gen,seedbox_gen

seedbox_list = [
        seedbox_gen(20,5,10),
        seedbox_gen(100,0,50),
        seedbox_gen(10,5,5),
        seedbox_gen(100,3,10)]

paths = {'watchlist':["/dir/lwatch1","/dir/lwatch2","/dir/lwatch3","/dir/lwatch4"],
         'local_torrent':"/dir/ltor",
         'local_invalid':"/dir/linv"}

rules = {'upload_path':[(Rule('name',lambda x: x == 5),seedbox_list[2],50),
                        (Rule('path',lambda x: x == str(4)),seedbox_list[3],40),
                        (Rule('path',lambda x: x == str(5)),seedbox_list[3],60)]} 

tfiles = [['/1'],['/2','/3'],['/4','/5','/6'],['/7','/8','/9','/10']]

ltor_list = [ltor_gen(name=str(i),path='/'+str(i),size=i) for i in range(1,11)]

class ControllerTest(unittest.TestCase):
    def setUp(self):
        patcher_isdir = patch('os.path.isdir',return_value=True)
        patcher_glob = patch('glob.glob',side_effect=tfiles)
        patcher_ltor = patch('churada.core.LocalTorrent',side_effect=ltor_list)

        self.mock_isdir = patcher_isdir.start()
        self.mock_glob = patcher_glob.start()
        self.mock_ltor = patcher_ltor.start()
        
        self.controller = Controller(seedbox_list,paths,rules)
    def populate_test(self):
        pass
        #self.controller.scan()
        #self.controller.populate()
        #for seedbox in self.controller.seedbox_list:
        #    print seedbox.enqueue.calls

    def scan_test(self):
        self.maxDiff = None
        self.controller.scan()
        control = []
        for ltor in deepcopy(ltor_list):
            ltor.move(paths['local_torrent'])
        self.assertEqual(self.controller.up_queue.record,control)
    def tearDown(self):
        patch.stopall()
        self.controller = None
