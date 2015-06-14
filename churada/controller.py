from .shell import Shell
from .record import LocalRecord
from .torrent import LocalTorrent,LocalTorrentError
from operator import itemgetter
from glob import glob
import os,logging,shutil

class ControllerError(Exception):
    pass

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
        self.blacklist = LocalRecord(Shell())

        self.rules = rules

        self.path_local_torrent = os.path.normpath(paths['local_torrent'])
        self.path_local_invalid = os.path.normpath(paths['local_invalid'])
        self.path_watchlist = []
        # check valdity of paths
        for watchpath in paths['local_watch']:
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
        for watchpath in self.path_watchlist:
            self.scan(watchpath)
        self.populate()
        # scan
        # populate
    # populate 
    def populate(self):
        self.logger.info("populating")
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
                self.logger.debug("populate: rule: %s <- %s"%(seedbox,ltor))
       # second: order by free space
        for ltor in self.up_queue:
            try:
                seedbox = next((seedbox for seedbox,free in sorted(seedbox_free.items(),key=itemgetter(1)) if ltor.size < free))
            except StopIteration:
                 pass
            else:
                seedbox.enqueue(ltor)
                self.up_queue.ltor_del(ltor=ltor)
                seedbox_free[seedbox] -= ltor.size
                seedbox_capacity[seedbox] -= ltor.size
                self.logger.debug("populate: free space: %s <- %s"%(seedbox,ltor))
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
                self.logger.debug("populate: capacity: %s <- %s"%(seedbox,ltor))
    def scan(self,scan_path):
        self.logger.info("scanning: %s"%(scan_path))
        path_expr = os.path.join(scan_path,"*.torrent")
        tfiles = glob(path_expr)
        for tpath in tfiles:
            try:
                ltor = LocalTorrent(tpath)
            except LocalTorrentError as e:
                self.logger.error("scan: invalid: %s" %(tpath))
                shutil.move(tpath,self.path_local_invalid)
            else:
                # make sure it's not a duplicate
                unique_flag = True
                for seedbox in self.seedbox_list:
                    if seedbox.find(ltor.name):
                       unique_flag = False
                       ltor.move(self.path_local_invalid) 
                       self.logger.info("scan: duplicate: %s (%s)",ltor,seedbox)
                       break
                if unique_flag:
                # move to active folder and enqueue
                    ltor.move(self.path_local_torrent)
                    self.up_queue.ltor_add(ltor=ltor)
                    self.logger.info("scan:adding: %s (%s)",ltor,seedbox)
