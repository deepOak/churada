import logging
import subprocess
import paramiko
import select
import time
import re

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
        if matchobj:
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
    def query(self,key,func):
        return key in self.__dict__ and func(self.__dict__[key])
        pass

class LocalTorrent:
    """ Record constructed from a .torrent file
    Uniquely defined by both name and path variables.
    Purpose is to represent a local .torrent file
    The name 'Local' suggests we have direct access to the .torrent file,
     but that we are uncertain of its state on the server

    LocalTorrent instances are meant to be wrappers for parsed *.torrent files.
    """
    # names and paths are both unique identifiers
    def __eq__(self,other):
        return self.name == other.name or self.path == other.path
    def __hash__(self):
        return hash(self.name)
    def __init__(self,path):
        self.logger = logging.getLogger("LocalTorrent")
        self.time = time.time()
        self.path = path
        self.__parse()
    def __ne__(self,other):
        return self.name != other.name and self.path != other.path
    # nonzero name implies a successful bencode parse
    # nonzero path is required to have an associated local file
    def __nonzero__(self):
        return bool(self.path) and bool(self.name)
    # defined for testing purposes
    def __reduce__(self):
        pass
    def __repr__(self):
        return "<%s,%s>" %(self.name,self.path)
    def __str__(self):
        pass
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
        self.name = None
        self.size = None
        with open(self.path,'r') as tfile:
            bencode = tfile.read()
        try:
            src = self.tokenize(bencode)
            tfile_dict = self.parse_bencode(src.next,src.next())
            for token in src:
                # log error
                raise SyntaxError("trailing bencode")
        except (AttributeError,ValueError,StopIteration),e:
            # log error
            return
            
        info = tfile_dict['info']
        del tfile_dict['info']
        if 'pieces' in info:
            del info['pieces']
        tfile_dict.update(info)
        if 'files' in info:
            self.size = 0
            for fdict in info['files']:
                self.size += fdict['length'] 
        else:
            self.size = tfile_dict['length']
        self.__dict__.update(tfile_dict)
    def query(self,func,key):
        return key in self.__dict__ and func(self.__dict__[key])
    
# TODO: Test error handling code
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
    def __init__(self,uname,host):
        self.logger = logging.getLogger("Shell")
        self.ssh_queue = []
        self.shell_queue = []
        self.host = host
        self.uname = uname
        self.path = host+"@"+uname
        self.__doing_shell = False
        self.__doing_ssh = False
    def __repr__(self):
        return "Shell(\"%s\", \"%s\")" %(self.uname,self.host)
    def __str__(self):
        return self.path
    def __connect(self):
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
        self.logger.debug("Command: (%s) %s",self,command)
        output = subprocess.check_output(command)
        return output
    def __ssh_command(self,command):
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
        return output
    def add_ssh(self,command,func,args):
        self.ssh_queue.append( (command,func,args) )
    def add_shell(self,command,func,args):
        self.shell_queue.append( (command,func,args) )
    def do_ssh(self):
        if self.__doing_ssh:
            return
        self.__processing_ssh = True
        self.__connect()
        if self.__client:
            for command,func,args in self.ssh_queue:
                output = None
                try:
                    output = self.__ssh_command(command)
                except (paramiko.ssh_exception.SSHException) as e:
                    self.logger.warning(e)
                if output is not None:
                    func(data=output,**args)
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
            output = None
            try:
                output = self.__shell_command(command)
            except (subprocess.CalledProcessError,OSError) as e:
                self.logger.warning(e)
            if output is not None:
                func(data=output,**args)
        self.shell_queue = []
        self.__doing_shell = False
class Record:
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
        self.record_remote = []
        self.record_local = []
        self.shell = shell
        self.info_cmd = "deluge-console \"connect 127.0.0.1:33307; info %s\""
    def __repr__(self):
        pass
    def __str__(self):
        pass
    # helper function for seedbox_manager
    def __rtor_add(self,data,pos=None):
        rtor = RemoteTorrent(time.time(),data)
        if rtor not in self.record_remote:
            if pos:
                self.record_remote.insert(pos,rtor)
            else:
                self.record_remote.append(rtor)
    # ltor > path
    def ltor_add(self,ltor=None,path=None,pos=None):
        if ltor and ltor not in self.record_local:
            if pos and pos in range(0,len(self.record_local)+1):
                self.record_local.insert(pos,ltor)
            else:
                self.record_local.append(ltor)
        elif path:
            ltor = LocalTorrent(path)
            self.ltor_add(pos=pos,ltor=ltor)
    # ltor > name > path
    def ltor_del(self,ltor=None,name=None,path=None):
        if ltor and ltor in self.record_local:
            self.record_local.remove(ltor)
        elif name:
            self.ltor_del(ltor=self.ltor_find(name=name))
        elif path:
            self.ltor_del(ltor=self.ltor_find(path=path))
    # ltor > name > path
    def ltor_find(self,ltor=None,name=None,path=None):
        result = None
        if ltor:
            result = next((e for e in self.record_local if e == ltor),None)
        elif name:
            result = next((e for e in self.record_local if e.name == name),None)
        elif path:
            result = next((e for e in self.record_local if e.path == path),None)
        return result
    # ltor > name > path
    def ltor_update(self,ltor=None,name=None,path=None):
        result = self.ltor_find(ltor=ltor,name=name,path=path)
        if result:
            index = self.record_local.index(result)
            self.ltor_del(ltor=result)
            ltor_new = LocalTorrent(result.path)
            self.ltor_add(ltor=ltor_new,pos=index)
    # rtor > name
    def rtor_add(self,rtor=None,name=None,pos=None):
        if rtor and rtor not in self.record_remote:
            self.record_remote.append(rtor)
        elif name:
            command = self.info_cmd %(name)
            func = self.__rtor_add
            self.shell.add_ssh(command,func,{'pos':pos})
    # rtor > name
    def rtor_del(self,rtor=None,name=None):
        if rtor and rtor in self.record_remote:
            self.record_remote.remove(rtor)
        elif name:
            self.rtor_del(rtor=self.rtor_find(name=name))
    def rtor_find(self,rtor=None,name=None):
        result = None
        if rtor:
            result = next((e for e in self.record_remote if e == rtor),None)
        elif name:
            result = next((e for e in self.record_remote if e.name == name),None)
        return result
    def rtor_update(self,rtor=None,name=None):
        result = self.rtor_find(rtor=rtor,name=name)
        if result:
            index = self.record_remote.index(result)
            self.rtor_del(rtor=result)
            self.rtor_add(name=result.name,pos=index)

class Seedbox:
    """
    Manages the logic of upload/download queues for an individual seedbox
     as well as upload and download file locations.
    """
    def __init__(self):
        self.logger = logging.getLogger("Seedbox")
#        self.shell = Shell()
#        self.uqueue = Record(
        pass
    def __repr__(self):
        pass
    def __str__(self):
        pass
    # dfunc, ufunc describe what to do with the output returned by the shell manager
    # 0) call shell to get the file record ->
    # 1)  ensure the file/record still exists
    # 2)  validate the file/record by arbitrary test (size, matching)
    # 3) call shell to perform the action (upload, download, deletion)
    # 4)  cleanup queues (call del_uqueue, etc.)
    def __delete(self):
        pass
    def __download(self):
        pass
    def __upload(self):
        pass

    def uqueue_add(self,ltor):
        pass
    def uqueue_del(self,ltor):
        pass
    def uqueue_do(self,max_data = 0):
        pass
    def uqueue_populate(self):
        pass
    def dqueue_add(self,rtor):
        pass
    def dqueue_del(self,rtor):
        pass
    def dqueue_do(self,max_data = 0):
        pass
    def record_populate(self):
        pass
