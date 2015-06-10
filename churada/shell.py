import paramiko, subprocess, logging

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

