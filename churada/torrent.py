import os, shutil, re, logging, time


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
			  "Size: (?P<csize>\d+)/(?P<size>\d+) Ratio: (?P<ratio>\d+\.\d+)\s*\n"
              "Seed time: (?P<stime>\d+) Active: (?P<atime>\d+)\s*\n"
              "Tracker status: (?P<tracker>[\w.]+): (?P<tracker_status>[\w ]+)\s*(\n)?"
              "(Progress: (?P<progress>\d+\.\d+)\%)?")
	
    __size_pattern = r"(\d+\.\d+) ([KMGT])iB"
    __time_pattern = r"(\d+) days (\d+):(\d+):(\d+)"
    __size_dict = { 'K':1<<10, 'M':1<<20, 'G':1<<30, 'T':1<<40 }
    __time_dict = { 'd':24*60*60, 'h':60*60, 'm':60, 's':1 }
    __time_factor = [ 24*60*60, 60*60, 60, 1]
#    __state_list = ['Active','Allocating','Checking','Downloading','Error','Paused','Seeding','Queued']
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
        return "<rtor %s, %s>" %(self.name,self.state)
#        return self.name
    # defined for testing purposes
    def __reduce__(self):
        pass
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
            if key != 'name' and key != 'state':
                try:
                    info_dict[key] = float(info_dict[key])
                except (TypeError,ValueError):
                   pass
        if info_dict['atime'] > 0:
            info_dict['score'] = 10**6*info_dict['ratio']/info_dict['atime']
#        if info_dict['state'] not in self.__state_list:
#            info_dict['state'] = None
        self.__dict__.update(info_dict)
        if not self:
            raise RemoteTorrentError("init error: torrent has no record")
    @classmethod
    def batch_parse(cls,info,timestamp):
        info = re.sub(cls.__size_pattern, cls.__size_convert, info)
        info = re.sub(cls.__time_pattern, cls.__time_convert, info)   
        info_iter = re.finditer(cls.__record_pattern,info)
        batch = [RemoteTorrent(match.group(),timestamp) for match in info_iter]
        batch.sort(key=lambda rtor: rtor.score)
        return batch
#    def query(self,key,func):
#        return key in self.__dict__ and func(self.__dict__[key])

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
#    def query(self,key,func):
#        return key in self.__dict__ and func(self.__dict__[key])
        # log: query, result

