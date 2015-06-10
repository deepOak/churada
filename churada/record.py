import logging,copy,time
from .torrent import LocalTorrent


class LocalRecord:
    """
    Manages records, including creation, deletion, updating;
    asserts uniqueness for records, and ensures torrent files are validated
    Purpose is to keep a list of valid, up-to-date records on hand

    Keeps two queues: one for LocalTorrents and one for RemoteTorrents
    The order of each queue is maintained. Duplicates and zero-records 
     (as defined above) are forbidden.

    Supports add, del, find, and update operations for each of 
     LocalTorrent (ltor) and RecordTorrent (rtor) queues
     Operations may be called by object or name (and by path for LocalTorrents)
    Since uniqueness is maintained, operations are always performed on any 
     object present in the queue which is equal to the passed argument.
    """
    def __init__(self, shell):
        self.logger = logging.getLogger("Record")
        self.record = []
        self.shell = shell
    def __nonzero__(self):
        return bool(self.record)
    def __iter__(self):
        return iter(copy.copy(self.record))
    def __repr__(self):
        return str(self.record) 
    # ltor > path
    def ltor_add(self,ltor=None,path=None,pos=None):
        if ltor and ltor not in self.record:
            if pos and pos in range(0,len(self.record)+1):
                self.record.insert(pos,ltor)
            else:
                self.record.append(ltor)
        elif path:
            ltor = LocalTorrent(path)
            self.ltor_add(pos=pos,ltor=ltor)
    # ltor > name > path
    def ltor_del(self,ltor=None,name=None,path=None):
        if ltor and ltor in self.record:
            self.record.remove(ltor)
        elif name:
            self.ltor_del(ltor=self.ltor_find(name=name))
        elif path:
            self.ltor_del(ltor=self.ltor_find(path=path))
    # ltor > name > path
    def ltor_find(self,ltor=None,name=None,path=None):
        result = None
        if ltor:
            result = next((e for e in self.record if e == ltor),None)
        elif name:
            result = next((e for e in self.record if e.name == name),None)
        elif path:
            result = next((e for e in self.record if e.path == path),None)
        return result
    # ltor > name > path
#    def ltor_update(self,ltor=None,name=None,path=None):
#        result = self.ltor_find(ltor=ltor,name=name,path=path)
#        if result:
#            index = self.record.index(result)
#            self.ltor_del(ltor=result)
#            ltor_new = LocalTorrent(result.path)
#            self.ltor_add(ltor=ltor_new,pos=index)
    def ltor_sort(self,key=lambda ltor: ltor.size):
        self.record.sort(key=key)

class RemoteRecord:
    def __init__(self,shell):
        self.logger = logging.getLogger("RemoteRecord")
        self.record = []
        self.shell = shell
        self.info_cmd = "deluge-console \"connect 127.0.0.1:33307; info %s\""
    def __iter__(self):
        return iter(copy.copy(self.record))
    def __repr__(self):
        return self.record
    # helper function for seedbox_manager
    def __rtor_add(self,data,pos=None):
        rtor = RemoteTorrent(time.time(),data)
        if rtor not in self.record:
            if pos:
                self.record.insert(pos,rtor)
            else:
                self.record.append(rtor)
    # rtor > name
    def rtor_add(self,rtor=None,name=None,pos=None):
        if rtor and rtor not in self.record:
            self.record.append(rtor)
        elif name:
            command = self.info_cmd %(name)
            func = self.__rtor_add
            self.shell.add_ssh(command,func,{'pos':pos})
    # rtor > name
    def rtor_del(self,rtor=None,name=None):
        if rtor and rtor in self.record:
            self.record.remove(rtor)
        elif name:
            self.rtor_del(rtor=self.rtor_find(name=name))
    def rtor_find(self,rtor=None,name=None):
        result = None
        if rtor:
            result = next((e for e in self.record if e == rtor),None)
        elif name:
            result = next((e for e in self.record if e.name == name),None)
        return result
    def rtor_update(self,rtor=None,name=None):
        result = self.rtor_find(rtor=rtor,name=name)
        if result:
            index = self.record.index(result)
            self.rtor_del(rtor=result)
            self.rtor_add(name=result.name,pos=index)

