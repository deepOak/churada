import logging,time,re,os
from operator import itemgetter

from .torrent import LocalTorrent,RemoteTorrent
from .record import LocalRecord,RemoteRecord
from .shell import Shell

class SeedboxError(Exception):
    pass

class Seedbox:
    """
    Manages the upload/download queues for an individual seedbox
     and download file locations.
     - capacity: represents the capacity
     - up_queue - LocalRecord representing a queue of files to upload. Populated externally.
     - down_queue - RemoteRecord representing a queue of files to download. Populated individually after each successful upload
     - info - RemoteRecord representing the totality of the records on the remote server
      used to organize deletion events
     
     - rules are a tuple of the form (key,func) for use in query functions
     - r_download_valid - list of rules that determine if a download is valid
     - r_download_path - list of rules that determine where to download a path.
      - elements are triples of the form (rule,path,priority)
      - sorted by priority; first match is used
     - r_delete_valid - list of rules that determine if a deletion is valid
    """
    __upload_limit = 0.25
    __download_limit = 0.25
    __upload_command = ["rsync","-n"]
    __download_command = ["rsync","-rn"]
    __delete_command = "deluge-console \"connect 127.0.0.1:33307; info \'%s\'\"" # rm --remove-data \'%s\'<F12>\"" 
    __size_command = "du --block-size=1 -s ~/"
    __info_command = "deluge-console \"connect 127.0.0.1:33307; info\""
    __max_failures = 5
    # NOTE: must assign local path when appending things to download queue
    def __init__(self,uname,host,capacity,paths,rules):
        self.shell = Shell(uname,host)
        self.up_queue = LocalRecord(self.shell)
        self.down_queue = RemoteRecord(self.shell)
        self.info = RemoteRecord(self.shell)

        self.upload_failures = {}
        self.download_failures = {}

        self.path_remote_torrent = self.shell.path + ":" + paths['remote_torrent']
        self.path_remote_data = self.shell.path + ":" + paths['remote_data']
        self.path_local_data = os.path.normpath(paths['local_data'])

        if not os.path.isdir(self.path_local_data):
            raise SeedboxError("init error:  bad local data path")
        
        self.capacity = capacity
        self.upload_limit = self.__upload_limit * capacity
        self.download_limit = self.__download_limit * capacity

        self.rules = rules

        self.logger = logging.getLogger("Seedbox")
        self.rules['download_path'].sort(key=itemgetter(2),reverse=True)
    def __repr__(self):
        return "<%s>"%(self.shell.path)
    def __check_download_valid(self,rtor):
        return reduce(lambda x,y: x and y.query(rtor), self.rules['download_valid'],True)
    def __check_download_path(self,rtor):
        for rule,path,priority in self.rules['download_path']:
            if rule.query(rtor):
                return path
        return self.path_remote_data
    def __check_delete_valid(self,rtor):
        return reduce(lambda x,y: x and y.query(rtor),self.rules['delete_valid'],True)
    def __size(self,exitcode,output):
        if exitcode == 0:
            match = re.match("\d+",output)
            self.size = int(match.group())
            self.logger.info("size used: %.2f GiB" %(self.size/float(1<<30)))
    def __update(self,exitcode,output):
        if exitcode == 0:
            rtor_list = RemoteTorrent.batch_parse(output,time.time())
            self.info = RemoteRecord(self.shell)
            for rtor in rtor_list:
                self.info.rtor_add(rtor=rtor)
            
    def act(self):
        # update
        self.update_info()
        self.update_size()
        self.shell.do_ssh()
        # delete stuff
        up_size = 0
        for ltor in self.up_queue:
            if(up_size + ltor.size) < self.upload_limit:
                up_size += ltor.size
        delete_size = up_size - self.free
        self.delete(delete_size)
        self.shell.do_ssh()
        # check size
        self.update_size()
        self.shell.do_ssh()
        # upload files
        self.upload(self.free)
        self.shell.do_shell()
        self.download(self.download_limit)
        self.shell.do_shell()
    def delete(self,space,rtor_iter=None,rtor=None,exitcode=None,output=None):
        if not rtor_iter:
            rtor_iter = iter(self.info)
        if rtor and exitcode == 0: # successful delete
            space -= rtor.size
            self.down_queue.rtor_del(rtor=rtor)
            self.logger.info("(%0.f MiB / %0.f MiB left) delete %s" %(rtor.size/float(1<<20),space/float(1<<20),rtor))
        if space <= 0: # done with deleting
            return
        try:
            rtor = rtor_iter.next()
            while not self.__check_delete_valid(rtor):
                rtor = rtor_iter.next()
        except StopIteration:
            return
        command = self.__delete_command %(rtor.name)
        func = self.delete
        args = {'rtor':rtor,'rtor_iter':rtor_iter,'space':space}
        self.shell.add_ssh(command,func,args)
    def download(self,space,rtor_iter=None,rtor=None,exitcode=None,output=None):
        if not rtor_iter:
            rtor_iter = iter(self.down_queue)
        # check to see if the previous download was successful
        if rtor and exitcode == 0:
            space -= rtor.size
            self.down_queue.rtor_del(rtor=rtor)
            self.logger.info("(%0.f MiB / %0.f MiB left) download %s" %(rtor.size/float(1<<20),space/float(1<<20),rtor))
        if space <= 0:
            return
        try:
            rtor = rtor_iter.next()
            while not self.__check_download_valid(rtor):
                rtor = rtor_iter.next()
        except StopIteration:
            return
        # if we have enough space, download
        if rtor.size <= space:
            download_path = self.__check_download_path(rtor)
            if not download_path:
                download_path = self.path_local_data
            command = self.__download_command
            command.extend([self.path_remote_data,download_path])
            func = self.download
            args = {'rtor':rtor,'rtor_iter':rtor_iter,'space':space}
            self.shell.add_shell(command,func,args)
        # otherwise, move on 
        else:
            self.download(space,rtor_iter=rtor_iter)
    def enqueue(self,ltor):
        self.up_queue.ltor_add(ltor=ltor)
    def find(self,name):
        return self.up_queue.ltor_find(name=name) or self.info.rtor_find(name=name)
    @property
    def free(self):
        return self.capacity - self.size
    def update_info(self):
        self.logger.info("updating info")
        self.shell.add_ssh(self.__info_command,self.__update,{})
    def update_size(self):
        self.logger.info("updating size")
        self.shell.add_ssh(self.__size_command,self.__size,{})
    def upload(self,space,ltor_iter=None,ltor=None,exitcode=None,output=None):
        if not ltor_iter:
            ltor_iter = iter(self.up_queue)
        # successful upload
        if ltor and exitcode == 0:
            space -= ltor.size
            self.down_queue.rtor_add(name=ltor.name)
            self.up_queue.ltor_del(ltor=ltor)
            self.logger.info("(%0.f MiB / %0.f MiB) upload %s" %(ltor.size/float(1<<20),space/float(1<<20),ltor))
        try:
            ltor = ltor_iter.next()
        except StopIteration:
            return
        # if we have enough space, upload
        if ltor.size <= space:
            command = self.__upload_command
            command.extend([ltor.path,self.path_remote_torrent])
            func = self.upload
            args = {'ltor':ltor,'ltor_iter':ltor_iter,'space':space}
            self.shell.add_shell(command,func,args)
        # otherwise, move on to the next item 
        else:
            self.upload(space,ltor_iter=ltor_iter)

