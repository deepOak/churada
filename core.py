import logging
import subprocess
import paramiko
import select
import time
import re
from copy import copy
import os

from operator import itemgetter
from glob import glob
import shutil

class RemoteTorrentError(Exception):
    pass

class RemoteTorrent:
    """Record from seedbox 'info' command
    uniquely defined by name and state
    Purpose is to represent a remote .torrent file and its connection info.
    The name 'Remote' suggests that we may not have access to the .torrent file.

    RemoteTorrent instances are meant to be wrappers for parsed deluge-console records
    """
    # names are unique identifiers
    __record_pattern = ("Name: (?P<name>.+)\s*\n"
              "ID: (?P<id>[0-9a-f]+)\s*\n"
              "State: (?P<state>[\w]+)( Down Speed: (?P<dspeed>\d+)?/s)?( Up Speed: (?P<uspeed>\d+)/s)?( ETA: (?P<eta>[\d\w ]+))?\s*\n"
              "(Seeds: (?P<cseed>\d+) \((?P<tseed>\d+)\) Peers: (?P<cpeer>\d+) \((?P<tpeer>\d+)\) Availability: (?P<avail>\d+\.\d+)\s*\n)?"
			  "Size: (?P<csize>\d+)/(?P<tsize>\d+) Ratio: (?P<ratio>\d+\.\d+)\s*\n"
              "Seed time: (?P<stime>\d+) Active: (?P<atime>\d+)\s*\n"
              "Tracker status: (?P<tracker>[\w.]+): (?P<tracker_status>[\w ]+)\s*(\n)?"
              "(Progress: (?P<progress>\d+\.\d+)\%)?")
	
    __size_pattern = r"(\d+\.\d+) ([KMGT])iB"
    __time_pattern = r"(\d+) days (\d+):(\d+):(\d+)"
    __size_dict = { 'K':1<<10, 'M':1<<20, 'G':1<<30, 'T':1<<40 }
    __time_dict = { 'd':24*60*60, 'h':60*60, 'm':60, 's':1 }
    __time_factor = [ 24*60*60, 60*60, 60, 1]
    __state_list = ['Active','Allocating','Checking','Downloading','Error','Paused','Seeding','Queued']
    def __eq__(self,other):
        return self.name == other.name
    def __hash__(self):
        return hash(self.name)
    def __init__(self,info,timestamp):
        self.logger = logging.getLogger("RemoteTorrent")
        self.time = timestamp
        self.__parse(info)
    def __ne__(self,other):
        return self.name != other.name
    # a non-zero state implies a successful query: that torrent is present on the remote server and data is parsed correctly
    def __nonzero__(self):
        return bool(self.state) and bool(self.name)
    def __repr__(self):
        return self.name
    # defined for testing purposes
    def __reduce__(self):
        pass
    def __str__(self):
        return self.name
    @classmethod
    def __size_convert(cls,matchobj):
        return str(int( float(matchobj.group(1)) * cls.__size_dict[matchobj.group(2)] ))
    @classmethod
    def __time_convert(cls,matchobj):
		return str(sum( [i*j for i,j in zip( cls.__time_factor,[int(t) for t in matchobj.groups('0')] )]) )
    def __parse(self,info):
        # name/state will always be present
        self.name = None
        self.state = None
        # convert sizes to bytes, dates to seconds since epoch
        info = re.sub(self.__size_pattern, self.__size_convert, info)
        info = re.sub(self.__time_pattern, self.__time_convert, info)
        matchobj = re.search(self.__record_pattern,info)
        if not matchobj:
            raise RemoteTorrentError("No data present")

        info_dict = matchobj.groupdict()
        for key in info_dict:
            try:
                info_dict[key] = float(info_dict[key])
            except (TypeError,ValueError):
               pass
        if info_dict['atime'] > 0:
            info_dict['score'] = 10**6*info_dict['ratio']/info_dict['atime']
        if info_dict['state'] not in self.__state_list:
            info_dict['state'] = None
        self.__dict__.update(info_dict)
        if not self:
            raise RemoteTorrentError("init erro: torrent has no record")
    @classmethod
    def batch_parse(cls,info,timestamp):
        info = re.sub(cls.__size_pattern, cls.__size_convert, info)
        info = re.sub(cls.__time_pattern, cls.__time_convert, info)   
        info_iter = re.finditer(cls.__record_pattern,info)
        batch = [RemoteTorrent(match.group(),timestamp) for match in info_iter]
        batch.sort(key=lambda rtor: rtor.score)
        return batch
    def query(self,key,func):
        return key in self.__dict__ and func(self.__dict__[key])
        pass

class LocalTorrentError(Exception):
    pass

class LocalTorrent:
    """ Record constructed from a .torrent file
    Uniquely defined by both name and path variables.
    Purpose is to represent a local .torrent file
    The name 'Local' suggests we have direct access to the .torrent file,
     but that we are uncertain of its state on the server
    
    Objects created with faulty paths or data are silently created as empty files

    LocalTorrent instances are meant to be wrappers for parsed *.torrent files.
    """
    def __eq__(self,other):
        return self.name == other.name or self.path == other.path
    def __hash__(self):
        return hash(self.name)
    def __init__(self,path):
        self.logger = logging.getLogger("LocalTorrent")
        self.name = None
        self.path = None
        self.size = None
        path = os.path.normpath(path)
        if not os.path.isabs(path):
            raise LocalTorrentError("init error: path is not absolute: %s"%(path))
        if not os.path.isfile(path):
            raise LocalTorrentError("init error: path is not a file: %s"%(path))
        self.path = path
        self.time = time.time()
        self.size = os.path.getsize(self.path)
        self.__parse()
        # log: created ltor
    def __ne__(self,other):
        return self.name != other.name and self.path != other.path
    # need both name and path to be nonzero
    def __nonzero__(self):
        return bool(self.path) and bool(self.name)
    # defined for testing purposes
    def __reduce__(self):
        pass
    def __repr__(self):
        return "<%s,%s>" %(self.name,self.path)
    # tokenize and parse_bencode both from Fredrik Lundh:
    # August 2007 (effbot.org/zone/bencode.htm)
    @classmethod
    def tokenize(cls,bencode):
        i = 0
        match = re.compile("([deil])|(\d+):|(-?\d+)").match
        while i < len(bencode):
            m = match(bencode,i)
            s = m.group(m.lastindex)
            i = m.end()
            if m.lastindex == 2:
                yield "s"
                yield bencode[i:i+int(s)]
                i = i + int(s)
            else:
                yield s
    @classmethod
    def parse_bencode(cls,next_token,token):
        if token == 'i':
            data = int(next_token())
            if next_token() != 'e':
                raise ValueError
        elif token == 's':
            data = next_token()
        elif token == 'd' or token == 'l':
            data = []
            tok = next_token()
            while tok != "e":
                data.append(cls.parse_bencode(next_token,tok))
                tok = next_token()
            if token == "d":
                data = dict(zip(data[0::2],data[1::2]))
        else:
            raise ValueError
        return data
    def __parse(self):
        try:
            with open(self.path,'r') as tfile:
                bencode = tfile.read()
            src = self.tokenize(bencode)
            tfile_dict = self.parse_bencode(src.next,src.next())
            for token in src:
                raise SyntaxError("trailing bencode")
        except OSError as e:
            # log error
            raise LocalTorrentError("parse error: file error")
        except (AttributeError,ValueError,StopIteration,SyntaxError) as e:
            # log error
            raise LocalTorrentError("parse error: badly formed data")
        info = tfile_dict['info']
        del tfile_dict['info']
        del info['pieces']
        tfile_dict.update(info)
        if 'files' in info:
            for fdict in info['files']:
                self.size += fdict['length'] 
        else:
            self.size += tfile_dict['length']
        self.__dict__.update(tfile_dict)
        if not self:
            raise LocalTorrentError("init error: zero record")
    # moves the file (filename intact) to a directory
    def move(self,dest):
        dest = os.path.normpath(dest)
        if not os.path.isabs(dest):
            raise LocalTorrentError("move error: path not absolute: %s"%(self.path))
        if os.path.isdir(dest):
            filename = os.path.basename(self.path)
            dest = os.path.join(dest,filename)
        #if not os.path.isdir(os.path.dirname(dest)):
        #    raise LocalTorrentError("move error: no valid directory in path: %s"%(self.path))
        self.last_path = self.path
        shutil.move(self.path,dest)
        self.path = dest
        # log: moved file
    def query(self,func,key):
        return key in self.__dict__ and func(self.__dict__[key])
        # log: query, result
# Still need to test Shell
class Shell:
    """ 
    Maintain a list of local shell and SSH commands in a queue 
    Evaluates and returns the returned output when directed 
    Purpose is to manage input and output with shell and remote server efficiently,
     without requiring an individual ssh connection for each command.
    
    Usage is as follows
    - enqueue commands using add_ssh or add_shell,
      which includes both command, func, and arguments
    - resolve the queue using do_ssh or do_shell, 
      individually processing each command, and calling func(output,**args)
    """
    __connection_attempts = 5
    def __init__(self,uname=None,host=None):
        self.logger = logging.getLogger("Shell")
        self.ssh_queue = []
        self.shell_queue = []
        self.host = host
        self.uname = uname
        self.path = None
        if self.host and self.uname:
            self.path = uname+"@"+host
        self.__doing_shell = False
        self.__doing_ssh = False
    def __repr__(self):
        return "Shell(\"%s\", \"%s\")" %(self.uname,self.host)
    def __str__(self):
        return self.path
    def __connect(self):
        if not self.path:
            return
        for i in reversed(range(0,self.__connection_attempts)):
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(self.host,username=self.uname)
                self.__client = client
                self.logger.debug("Connected: %s" %(self.path))
                return 
            except paramiko.ssh_exception.SSHException as e:
                if i == 0:
                    raise e
                time.sleep(1)
    def __disconnect(self):
        if self.__client != None:
            self.__client.close()
            self.__client = None
    def __shell_command(self,command):
        command = re.split(" ",command)
        self.logger.debug("Command: (%s) %s",self,command)
        try:
            output = subprocess.check_output(command)
            exitcode = 0
        except (subprocess.CalledProcessError) as e:
            output = e.output
            exitcode = e.returncode
        return (exitcode,output)
    def __ssh_command(self,command):
        if not self.path:
            return
        self.logger.debug("Command: (%s) %s",self,command)
        stdin,stdout,stderr = self.__client.exec_command(command)
        output = ""
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                rl,wl,xl = select.select([stdout.channel],[],[],0.0)
                if len(rl) >= 0:
                    part = stdout.channel.recv(1024)
                    while part:
                        output += part
                        part = stdout.channel.recv(1024)
        exitcode = stdout.channel.recv_exit_status()
        return (exitcode,output)
    def add_ssh(self,command,func,args):
        if not self.path:
            return
        self.ssh_queue.append( (command,func,args) )
    def add_shell(self,command,func,args):
        self.shell_queue.append( (command,func,args) )
    def do_ssh(self):
        if not self.path or self.__doing_ssh:
            return
        self.__processing_ssh = True
        self.__connect()
        if self.__client:
            for command,func,args in self.ssh_queue:
                data = None
                try:
                    exitcode,output = self.__ssh_command(command)
                except (paramiko.ssh_exception.SSHException) as e:
                    self.logger.warning(e)
                args['exitcode'] = exitcode
                args['output'] = output
                func(**args) #,data=output)
            self.__disconnect()
            self.ssh_queue = []
        self.__doing_ssh = False
        #for command,func in self.ssh_queue:
    def do_shell(self):
        # try CalledProcessError for nonzero exit code
        if self.__doing_shell:
            return
        self.__processing_shell = True
        for command,func,args in self.shell_queue:
            data = None
            try:
                exitcode,output = self.__shell_command(command)
            except OSError as e:
                self.logger.warning(e)
            args['exitcode'] = exitcode
            args['output'] = output
            func(**args) #data = output
        self.shell_queue = []
        self.__doing_shell = False
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
        return iter(copy(self.record))
    def __repr__(self):
        pass
    def __str__(self):
        pass
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
    def ltor_update(self,ltor=None,name=None,path=None):
        result = self.ltor_find(ltor=ltor,name=name,path=path)
        if result:
            index = self.record.index(result)
            self.ltor_del(ltor=result)
            ltor_new = LocalTorrent(result.path)
            self.ltor_add(ltor=ltor_new,pos=index)
    def ltor_sort(self,key=lambda ltor: ltor.size):
        self.record.sort(key=key)

class RemoteRecord:
    def __init__(self,shell):
        self.logger = logging.getLogger("RemoteRecord")
        self.record = []
        self.shell = shell
        self.info_cmd = "deluge-console \"connect 127.0.0.1:33307; info %s\""
    def __iter__(self):
        return iter(copy(self.record))
    def __repr__(self):
        pass
    def __str__(self):
        pass
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
    __upload_command = "rsync -n %s %s"
    __download_command = "rsync -rn %s %s"
    __delete_command = "deluge-console \"connect 127.0.0.1:33307; info %s\"" # rm --remove_data %s
    __size_command = "du -block-size=1 -s ~/"
    __info_command = "deluge-console \"connect 127.0.0.1:33307; info\""
    # NOTE: must assign local path when appending things to download queue
    def __init__(self,uname,host,capacity,paths,rules):
        self.shell = Shell(uname,host)
        self.up_queue = LocalRecord(self.shell)
        self.down_queue = RemoteRecord(self.shell)
        self.info = RemoteRecord(self.shell)

        self.path_remote_torrent = paths[0]
        self.path_remote_data = paths[1]
        self.path_local_data = paths[2]
        
        self.capacity = capacity
        self.upload_limit = self.__upload_limit * capacity
        self.download_limit = self.__download_limit * capacity

        self.r_download_valid = rules[0]
        self.r_download_path = rules[1]
        self.r_delete_valid = rules[2]
        
        self.logger = logging.getLogger("Seedbox")
        # sort rules by priority 
        self.r_download_path.sort(key=itemgetter(2))
    def __str__(self):
        pass
    def __check_composite_rule(self,rule_list,rtor):
        for rule in rule_list:
            if not rtor.query(*rule):
                return False
        return True
    def __check_download_valid(self,rtor):
        for rule_list in self.r_download_valid:
            if not self.__check_composite_rule(rule_list,rtor):
                return False
        return True
    def __check_download_path(self,rtor):
        for rule_list,download_path,priority in self.r_download_path:
            if not self.__check_composite_rule(rule_list,rtor):
                return download_path
        return None # self.path_remote_data
    def __check_delete_valid(self,rtor):
        for rule_list in self.r_delete_valid:
            if not self.__check_composite_rule(rule_list,rtor):
                return False
        return True
    def __size(self,exitcode,output):
        if exitcode == 0:
            match = re.match("\d+",output)
            self.size = int(match.group())
    def __update(self,exitcode,output):
        if exitcode == 0:
            rtor_list = RemoteTorrent.batch_parse(output,time.time())
            self.info = RemoteRecord(self.shell)
            for rtor in rtor_list:
                self.info.add_rtor(rtor=rtor)
    def act(self):
        # update
        self.update_info()
        self.update_size()
        self.shell.do_ssh()
        # delete stuff
        up_queue_size = 0
        for ltor in self.up_queue:
            if(up_queue_size + ltor.size) < self.upload_limit:
                up_queue_size += ltor.size
        delete_size = up_queue_size - self.free
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
            command = self.__download_command %(self.path_remote_data,download_path)
            func = self.download
            args = {'rtor':rtor,'rtor_iter':rtor_iter,'space':space}
            self.shell.add_shell(command,func,args)
        # otherwise, move on 
        else:
            self.download(space,rtor_iter=rtor_iter)
    def enqueue(self,ltor):
        self.up_queue.add_ltor(ltor=ltor)
    @property
    def free(self):
        return self.capacity - self.size
    def update_info(self):
        self.shell.add_ssh(self.__info_command,self.__update,{})
    def update_size(self):
        self.shell.add_ssh(self.__size_command,self.__size,{})
    def upload(self,space,ltor_iter=None,ltor=None,exitcode=None,output=None):
        if not ltor_iter:
            ltor_iter = iter(self.up_queue)
        # successful upload
        if ltor and exitcode == 0:
            space -= ltor.size
            self.down_queue.rtor_add(name=ltor.name)
            self.up_queue.ltor_del(ltor=ltor)
        try:
            ltor = ltor_iter.next()
        except StopIteration:
            return
        # if we have enough space, upload
        if ltor.size <= space:
            command = self.__upload_command %(ltor.path,self.path_remote_torrent)
            func = self.upload
            args = {'ltor':ltor,'ltor_iter':ltor_iter,'space':space}
            self.shell.add_shell(command,func,args)
        # otherwise, move on to the next item 
        else:
            self.upload(space,ltor_iter=ltor_iter)

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
    def __init__(self,seedbox_list,path_watchlist,path_local_torrent,path_local_invalid,r_upload_path):
        self.logger = logging.getLogger("Controller")
        self.up_queue = LocalRecord(Shell())
        self.seedbox_list = seedbox_list
        self.r_upload_path = r_upload_path

        self.path_local_torrent = os.path.normpath(path_local_torrent)
        self.path_local_invalid = os.path.normpath(path_local_invalid)
        self.path_watchlist = []
        # check valdity of paths
        for watchpath in path_watchlist:
            watchpath = os.path.normpath(watchpath)
            if os.path.isdir(watchpath) and os.path.isabs(watchpath):
                self.path_watchlist.append(watchpath)
        # sort rules by priority
        self.r_upload_path.sort(key=itemgetter(2))
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
        if not seedbox_list:
            raise ControllerError("no seedboxes")
    def __str__(self):
        pass
    def __repr__(self):
        return self
    def __check_composite_rule(self,rule_list,ltor):
        for rule in rule_list:
            if not ltor.query(*rule):
                return False
        return True
    def __check_upload_path(self,ltor):
        for rule_list,upload_path,priority in self.r_upload_rule:
            if self.__check_composite_rule(rule_list,ltor):
                return upload_path
        return None 
    # act
    def act(self):
        for seedbox in seedbox_list:
            seedbox.act()
    # populate 
    def populate(self):
        seedbox_free = [(seedbox,seedbox.free) for seedbox in seedbox_list]
        seedbox_capacity = [(seedbox,seedbox.capacity*self.__upload_limit) for seedbox in seedbox_list]
        # first check upload rules
        for ltor in self.up_queue:
            seedbox = self.__check_upload_path(ltor)
            if seedbox and ltor.size < seedbox_capacity[seedbox]:
                seedbox.enqueue(ltor)
                seedbox_capacity[seedbox] -= ltor.size
                seedbox_free[seedbox] -= ltor.size
                self.up_queue.del_ltor(ltor=ltor)
       # second: order by free space
        for ltor in self.up_queue:
            try:
                seedbox = next(seedbox for seedbox,free in sorted(seedbox_free.items(),key=itemgetter(1)) if ltor.size < free)
            except StopIteration:
                 pass
            else:
                seedbox.enqueue(ltor)
                self.up_queue.del_ltor(ltor=ltor)
                seedbox_free[seedbox] -= ltor.size
                seedbox_capacity[seedbox] -= ltor.size
        # third: order by capacity remaining
        for ltor in self.up_queue:
            try:
                seedbox = next(seedbox for seedbox,capacity in sorted(seedbox_capacity.items(),key=itemgetter(1)) if ltor.size < capacity)
            except StopIteration:
                pass
            else:
                seedbox.enqueue(ltor)
                self.up_queue.del_ltor(ltor=ltor)
                seedbox_free[seedbox] -= ltor.size
                seedbox_capacity[seedbox] -= ltor.size
        # first: check upload rules. upload to seedbox with matching rule, highest priority
        # second: order seedboxes by real free space remaining. upload to seedbox with smallest but that can accomodate torrent
        # third: order seedboxes by effective capacity (some multiple of their total capacity). upload to seedbox with the smallest that can accomodate torrent
    def scan(self):
        torrent_pathlist = []
        for watchpath in self.path_watchlist:
            path_expr = os.path.join(watchpath,"*.torrent")
            tfiles = glob(path_expr)
            torrent_pathlist.extend(tfiles)
        for path in torrent_pathlist:
            try:
                ltor = LocalTorrent(path)
            except Exception as e:
                logger.error(e)
            else:
                self.up_queue.add_ltor(ltor=ltor)
                ltor.move(self.path_local_torrent)
#            up_queue_size = sum(ltor.size for ltor in seedbox.up_queue)
#            max_upload = self.__upload_limit * seedbox.capacity
#            up_queue_size = 0
#            for ltor in seedbox.up_queue:
#                if (up_queue_size + ltor.size) < max_upload:
#                    up_queue_size += ltor.size
#            delete_size = up_queue_size - seedbox.free
#            seedbox.delete(delete_size)
