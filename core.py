import logging
import subprocess
import paramiko
import select
import time

class RemoteTorrent:
    """Record from seedbox 'info' command
    uniquely defined by the name variable
    Purpose is to represent a remote .torrent file and its connection info.
    Remote suggests that we don't have access to the .torrent file.
    """
    def __eq__(self,other):
        return self.name == other.name
    def __hash__(self):
        return hash(self.name)
    def __init__(self,info,timestamp):
        self.logger = logging.getLogger("RemoteTorrent")
        self.time = timestamp
        self.parse(info)
        pass
    def __ne__(self,other):
        return self.name != other.name
    def __nonzero__(self):
        return bool(self.state) and bool(self.name)
    def __repr__(self):
        return self.name
    def __reduce__(self):
        pass
    def __str__(self):
        return self.name
    def parse(self,info):
        self.name = info
        self.size = None
        self.state = None
        # check both for matching and uniqueness when parsing
        pass
    def query(self,func,key):
        return key in self.__dict__ and func(self.__dict__[key])
        pass

class LocalTorrent:
    """ Record constructed from a .torrent file
    uniquely defined by the name variable
    Purpose is to represent a .torrent file
    Local suggests we have direct access to the .torrent file
    """
    def __eq__(self,other):
        return self.name == other.name or self.path == other.path
    def __hash__(self):
        return hash(self.name)
    def __init__(self,path,timestamp):
        self.logger = logging.getLogger("LocalTorrent")
        self.time = timestamp
        self.path = path
        self.parse()
    def __ne__(self,other):
        return self.name != other.name and self.path != other.path
    def __nonzero__(self):
        return bool(self.path) and bool(self.name)
    def __reduce__(self):
        pass
    def __repr__(self):
        pass
    def __str__(self):
        pass
    def parse(self):
        self.name = None
        self.size = None
        # parse things
    def query(self,func,key):
        return key in self.__dict__ and func(self.__dict__[key])
    
    # parse torrent bencode, extract useful information
    # keep track of the .torrent file on disc: move, delete
    # keep two separate (uncorrelated) lists of LocalTorrent, RemoteTorrent; 
    #  we only need to correlate lists for one purpose, and this is easily done by checking for inclusion
# TODO: Test error handling code
class Shell:
    """ 
    Maintain a list of local shell and SSH commands in a queue 
    Evaluates and returns the returned output when directed 
    Purpose is to manage input and output with shell and remote server efficiently
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
            ltor = LocalTorrent(path,time.time())
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
            result.parse()
            self.ltor_add(ltor=result,pos=index)
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
    Manages the logic of upload and download queues and of 
    where to upload and download file locations.
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
