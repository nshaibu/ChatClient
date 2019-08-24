#!/usr/bin/python3

#===========================================================================================
# Copyright (C) 2018 Nafiu Shaibu.
# Purpose: 
#-------------------------------------------------------------------------------------------
# This is a free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your option)
# any later version.

# This is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#===========================================================================================

import gi
import time
import uuid

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import listener
import users


MAX_PACKET_SIZE = 200   #maximmum packet size 
MAX_DATA_SIZE = MAX_PACKET_SIZE - 21 # maximum data size

#########################
#ENUMS FOR MESSAGE TYPES#
#########################
(
    TXT_DATA, 
    FILE_TXT_DATA, 
    DOC_TEXT_DATA, 
    PPT_TEXT_DATA, 
    MP3_AUDIO_DATA, 
    MP4_AUDIO_DATA, 
    MP4_VIDEO_DATA, 
    MKV_VIDEO_DATA, 
    JPG_PIC_DATA, 
    PNG_PIC_DATA, 
    COORD_DATA, 
    COORD_DATA_MANY 
) = range(12)

################
# PACKET TYPES #
################
REG_PACKET = 9     #registration packet
AUTH_PACKET = 10   #authentication packet
LOGOUT_PACKET = 13 #logout packet
USERS_PACKET = 11   #users packet
GET_USERNAME_PACKET = 14 #get a users name request
GET_ALL_USERS_PACKET = 12   #ask the server for all  the users on the system and the userid
GEO_PACKET = 20        #packet received is geolocation packet[send geolocation info to self or other client]
GET_GEO_PACKET = 21    #get geolocation packet [request]
SET_GEO_PACKET = 22    #set geolocation packet [request]
MSG_PACKET = 30   #normal messages like plain text
FILE_PACKET = 31  #send messages in a form of files like .docx,.txt,.mp3
GET_MSG_PACKET = 32  #get messages in database
ACK_PACKET = 40    #acknowledge packet
SYN_PACKET = 41    #synchronization packet
FIN_PACKET = 42    #Finishing packet*/
CLOSE_PACKET = 43  #request close connection packet*/


def get_child_widget(parent, child):
    """gets child widget with name 'child' from parent widget 'parent'"""
    #childen = parent.get_children()
    pass
    

class packets():
    """
    This module defines the packet structure and all the various packet types
    for the client application. it is similar to the servers packets.h file
    """
    
    def __init__(self, packet_type=None, userid=None, receiverid=None, mesg_type=None, mesg=None):
        self._ptype = packet_type
        self._userid = userid
        self._receiverid = receiverid
        self._tmsg = mesg_type
        self._msg = mesg

    @property
    def packet_type(self):
        return self._ptype
    @packet_type.setter
    def packet_type(self, ptye):
        self._ptype = ptye

    @property
    def userid(self):
        return self._userid
    @userid.setter
    def userid(self, id):
        self._userid = id

    @property
    def receiverid(self):
        return self._receiverid
    @receiverid.setter
    def receiverid(self, id):
        self._receiverid = id

    @property
    def mesg_type(self):
        return self._tmsg
    @mesg_type.setter
    def mesg_type(self, tmsg):
        self._tmsg = tmsg
    
    @property
    def mesg(self):
        return self._msg
    @mesg.setter
    def mesg(self, msg):
        self._msg = msg

    def packet_to_str(self):
        packet_str = '|' + str(self.packet_type) + '|' + str(self.userid) + '|' + str(self.receiverid) + '|' + str(self.mesg_type) + '|' + str(self.mesg) + '|'
        return packet_str

    def str_to_packet(self, str_):
        lt = str(str_, encoding="utf-8").split('|')
        
        if len(lt) >= 4:
            self.packet_type = lt[1]
            self.userid = lt[2]
            self.receiverid = lt[3]
            self.mesg_type = lt[4]
            self.mesg = lt[5]

    def interpret_packet(self, builder=None, users_manager=None):
        
        if self.packet_type is None:
            return

        if int(self.packet_type) == FIN_PACKET:
            return False
        elif int(self.packet_type) == ACK_PACKET:
            return True
        elif int(self.packet_type) == MSG_PACKET:
            assert builder is not None, "builder cannot be None"
            assert users_manager is not None, "Users manager is None"

            listbox = builder.get_object("users_listbox")

            uid = str(uuid.uuid4().hex)
            Gdk.beep()

            if int(self.userid) == int(users_manager.curr_receiver_user):   #if sender is the one in focus
                list_display = listener.Custom_Message_Display( builder, 
                                                                users_manager,
                                                                message=str(self.mesg) )
                list_display.set_display_uid(uid)
                list_display.write_to_display()
                list_display.auto_scroll_listbox()

                tim = time.time()

                try:
                    users_manager.database_manager.cursor.execute("INSERT INTO messages \
                                                                VALUES('%s', %d, %d, %ld, %ld, %d, '%s') \
                                                                " % (uid,    #unique id for messages
                                                                    int(self.userid),        #sender id
                                                                    int(self.receiverid),    #receiver id
                                                                    tim,                     #time sent(in seconds since unix epoch)
                                                                    tim,                     #time read(in seconds since unix epoch)
                                                                    int(self.mesg_type),     #message type
                                                                    self.mesg))              #message
                    users_manager.database_manager.db.commit()
                except Exception:
                    users_manager.database_manager.db.rollback()
            else:
                children = listbox.get_children()
                for child in children:
                    if int(child.userid) == int(self.userid):
                        count = int( child.button.message_count_label.get_label() )
                        count = count + 1
                        child.button.message_count_label.set_label( "%d" % count )

                tim = time.time()

                try:
                    users_manager.database_manager.cursor.execute("INSERT INTO messages \
                                                                VALUES('%s', %d, %d, %ld, %ld, %d, '%s') \
                                                                " % (uid,    #unique id for messages
                                                                    int(self.userid),        #sender id
                                                                    int(self.receiverid),    #receiver id
                                                                    tim,                     #time sent(in seconds since unix epoch)
                                                                    int(-1),                     #time read(in seconds since unix epoch)
                                                                    int(self.mesg_type),     #message type
                                                                    self.mesg))

                    users_manager.database_manager.db.commit()  
                except Exception:
                    users_manager.database_manager.db.rollback()

            return True