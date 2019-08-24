import packets
import threading
from time import time
from collections import deque, namedtuple

''' 
Sessions are spawn as threads to send the required data
however the data they will be sending have piriorities
    -text -- HIGHEST
    -PICS/VIDEO -- LOW
The data are blocked down into smaller fixed size lengths
of 1000bytes
'''

MAX_SIZE_OF_PACKET = 1000 #bytes



'''
READ_SESSION:  Read sessions it reads messages from server 
WRITE_SESSION:  Send messages to server
'''
SessionType = namedtuple('SessionType', ['READ_SESSION', 'WRITE_SESSION'])
sessionType = SessionType(10, 11)


class session(threading.Thread):
    
    def __init__(self, sid, session_type=sessionType.WRITE_SESSION):
        super().__init__()

        self.time_started = time()
        self.session_type = session_type
        self.session_number = sid   #session id
        self._buffer = deque()

        if self.session_type == sessionType.READ_SESSION:
            self.total_packet_to_receive = None
            self.total_packet_received = None
        else:
            pass
    
    def duration(self):
        return time() - self.time_started

    def _write_data(self, data):
        if data.mesg_type == packets.TXT_DATA:
            _data = str(data.mesg).encode('ascii')
            
            if len(_data) > 0:
                num_fragments = len(_data) // MAX_SIZE_OF_PACKET
                if num_fragments:
                    begin, end = 0, MAX_SIZE_OF_PACKET

                    for _ in range(num_fragments):

                        self._buffer.appendleft(packets.packets(
                            packet_type=packets.MSG_PACKET,
                            userid="userid",
                            receiverid="receiverid",
                            mesg_type=packets.TXT_DATA,
                            mesg=_data[begin:end]
                        ))

                        begin += MAX_SIZE_OF_PACKET
                        end += MAX_SIZE_OF_PACKET
                    else: #if excess data are left capture them below
                        if end < len(_data):
                            self._buffer.appendleft(packets.packets(
                                packet_type=packets.MSG_PACKET,
                                userid="userid",
                                receiverid="receiverid",
                                mesg_type=packets.TXT_DATA,
                                mesg=_data[end:]
                            ))

                else: #if data has only one fragments
                    self._buffer.appendleft(packets.packets(packet_type=packets.MSG_PACKET, userid="userid", receiverid="receiverid", mesg_type=packets.TXT_DATA, mesg=_data))
            else:
                return #kill self
        else:
            try:
                fd = open(str(data.mesg), "rb")
            except FileNotFoundError:
                return

            while True:
                data_content = fd.read(MAX_SIZE_OF_PACKET)
                if not data_content: break
                
                self._buffer.appendleft(packets.packets(
                                    packet_type=packets.MSG_PACKET,
                                    userid="userid",
                                    receiverid="receiverid",
                                    mesg_type=packets.TXT_DATA,
                                    mesg=str(data_content).encode('ascii')
                                    ))

            fd.close()

    def _read_data(self):
        pass

    def run(self):
        pass


class SessionsManager():
    
    def __init__(self):
        pass