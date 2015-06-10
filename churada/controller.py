from .shell import Shell
from .record import LocalRecord
from operator import itemgetter
from glob import glob
import os,logging

class Controller:
    """
    Controls multiple seedbox instances, manages upload logic
    - watches local folders for torrent files
    - 
    - chooses upload path based on free space availability and capacity
    """
    __upload_limit = 0.25
    def __init__(self,seedbox_list,paths,rules):
        self.logger = logging.getLogger("Controller")
        self.up_queue = LocalRecord(Shell())
        self.seedbox_list = seedbox_list
        
        self.rules = rules

        self.path_local_torrent = os.path.normpath(paths['local_torrent'])
        self.path_local_invalid = os.path.normpath(paths['local_invalid'])
        self.path_watchlist = []
        # check valdity of paths
        for watchpath in paths['watchlist']:
            watchpath = os.path.normpath(watchpath)
            if os.path.isdir(watchpath) and os.path.isabs(watchpath):
                self.path_watchlist.append(watchpath)
        # sort rules by priority
        self.rules['upload_path'].sort(key=itemgetter(2),reverse=True)
        # check variables
        if not os.path.isabs(self.path_local_torrent):
            raise ControllerError("init error: not absolute path: %s"%(self.path_local_torrent))
        if not os.path.isabs(self.path_local_invalid):
            raise ControllerError("init error: not absolute path: %s"%(self.path_local_invalid))
        if not os.path.isdir(self.path_local_torrent):
            raise ControllerError("init error: not directory: %s"%(self.path_local_torrent))
        if not os.path.isdir(self.path_local_invalid):
            raise ControllerError("init error: not directory: %s"%(self.path_local_invalid))
        if not self.path_watchlist:
            raise ControllerError("no valid watchpaths")
        if not self.seedbox_list:
            raise ControllerError("no seedboxes")
    def __repr__(self):
        return self
    def __check_upload_path(self,ltor):
        for rule,path,priority in self.rules['upload_path']:
            if rule.query(ltor):
                return upload_path
        return None 
    # act
    def act(self):
        for seedbox in self.seedbox_list:
            seedbox.act()
    # populate 
    def populate(self):
        seedbox_free = dict([(seedbox,seedbox.free) for seedbox in self.seedbox_list])
        seedbox_capacity = dict([(seedbox,seedbox.upload_limit) for seedbox in self.seedbox_list])
        # first check upload rules
        for ltor in self.up_queue:
            seedbox = self.__check_upload_path(ltor)
            if seedbox and ltor.size < seedbox_capacity[seedbox]:
                seedbox.enqueue(ltor)
                seedbox_capacity[seedbox] -= ltor.size
                seedbox_free[seedbox] -= ltor.size
                self.up_queue.ltor_del(ltor=ltor)
       # second: order by free space
        for ltor in self.up_queue:
            print ltor
            try:
                seedbox = next((seedbox for seedbox,free in sorted(seedbox_free.items(),key=itemgetter(1)) if ltor.size < free))
            except StopIteration:
                 pass
            else:
                seedbox.enqueue(ltor)
                self.up_queue.ltor_del(ltor=ltor)
                print seedbox
                print seedbox_free[seedbox]
                print ltor.size
                seedbox_free[seedbox] -= ltor.size
                seedbox_capacity[seedbox] -= ltor.size
        # third: order by capacity remaining
        for ltor in self.up_queue:
            try:
                seedbox = next((seedbox for seedbox,capacity in sorted(seedbox_capacity.items(),key=itemgetter(1)) if ltor.size < capacity))
            except StopIteration:
                pass
            else:
                seedbox.enqueue(ltor)
                self.up_queue.ltor_del(ltor=ltor)
                seedbox_free[seedbox] -= ltor.size
                seedbox_capacity[seedbox] -= ltor.size
    def scan(self):
        torrent_pathlist = []
        for watchpath in self.path_watchlist:
            path_expr = os.path.join(watchpath,"*.torrent")
            tfiles = glob(path_expr)
            torrent_pathlist.extend(tfiles)
        for path in torrent_pathlist:
            try:
                ltor = LocalTorrent(path)
                print ltor
            except Exception as e:
                logger.error(e)
                ltor.move(self.path_local_invalid)
            else:
                ltor.move(self.path_local_torrent)
                self.up_queue.ltor_add(ltor=ltor)
