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
import sys
import os
import sqlite3
import shutil

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import packets
import files



_USR_DB_FOLDER_ = os.sep.join( [files._USER_MEDIA_FOLDER_, "DB"] )
__DB_NAME__ = "concurrent_chat_client_2018_04_08.sqlite3"
__NAME_BUF_SIZE__ = 100
__PASSWD_BUF_SIZE__ = 120


def get_messages_from_server(builder=None, users_manager=None, receiver_id=-1):
    """
    get messages from the server. This message is the mesg sent when
    the receiver is not online
    """
    pk = packets.packets(packet_type=packets.GET_MSG_PACKET,
                        userid=users_manager.curr_sender_user,
                        receiverid=-1,
                        mesg_type=packets.TXT_DATA,
                        mesg="0")

    users_manager.client_socket.send_msg_dontwait( pk.packet_to_str() )  #request message from server
    
    while True:
        reply_chunk = users_manager.client_socket.recv_reply()
        pk.str_to_packet( reply_chunk )

        if int(pk.packet_type) == packets.MSG_PACKET:
            try:
                pass
            except:
                break
        else:
            break

    
class Database_Manager():
    """The main database manager for the application"""

    def __init__(self):
        self.db = None     #database connection handler
        self.cursor = None #for read querys from db cursor is required to move through all the response 

    def database_connection(self):
        if not os.path.exists( os.path.normpath(files._USER_MEDIA_FOLDER_) ):
            os.mkdir( os.path.normpath(files._USER_MEDIA_FOLDER_) )

        if not os.path.exists( os.path.normpath(_USR_DB_FOLDER_) ):    
            os.mkdir( os.path.normpath(_USR_DB_FOLDER_) )

        if not os.path.exists( os.path.normpath(os.sep.join([_USR_DB_FOLDER_, __DB_NAME__])) ):
            try:
                self.db = sqlite3.connect(os.sep.join([_USR_DB_FOLDER_, __DB_NAME__]))
                self.cursor = self.db.cursor()
            except (sqlite3.OperationalError, sqlite3.InternalError) as e:
                raise ConnectionError("Failed to connect to database %s" % str(e.args))

            try:
                self.cursor.execute("CREATE TABLE users ( \
                                    userid INTEGER NOT NULL PRIMARY KEY, \
                                    username VARCHAR(%d) \
                                    )" %  __NAME_BUF_SIZE__ )

                self.cursor.execute("CREATE TABLE messages ( \
                                    message_id VARCHAR(100) NOT NULL PRIMARY KEY, \
                                    sender_id INTEGER NOT NULL, \
                                    receiver_id INTEGER NOT NULL, \
                                    time_received DECIMAL(20, 0), \
                                    time_read DECIMAL(20, 0), \
                                    msg_type INTEGER NOT NULL, \
                                    message VARCHAR(%d) \
                                    )" %  packets.MAX_DATA_SIZE )
                self.db.commit()
            except Exception as e:
                os.remove( os.path.normpath(os.sep.join([_USR_DB_FOLDER_, __DB_NAME__])) )
                raise ConnectionError("Initialization of database failed %s" % str(e.args))

        else:
            try:
                self.db = sqlite3.connect(os.sep.join([_USR_DB_FOLDER_, __DB_NAME__]))
                self.cursor = self.db.cursor()
            except (sqlite3.OperationalError, sqlite3.InternalError) as e:
                raise ConnectionError("Failed to connect to database %s" % str(e.args))

    def database_disconnection(self):
        if self.db is None:
            return
        self.db.commit()
        self.db.close()



class Users_handler():
    """handler for all user management activities require by the application"""
    
    def __init__(self):
        self.builder = None
        self.client_socket = None

        self.curr_receiver_user = -1   #id of current receiver user
        self.curr_sender_user = -1     #id of current sender user

        self.login_users = []          #login users list
        #self.all_users = {}            #hash table of all users with thier ids
        
        ''' 
        This is technically the number of users on the system. However it is
        used during initial negotiation with the server to know whether a new user
        have been added since last successfully login
        '''
        self.revision_num = 0

        self.database_manager = Database_Manager()  #client side database manager


    def set_revision_number(self):
        if self.database_manager.db is None:
            raise ConnectionError("Not connected to a database")
        
        try:
            self.database_manager.cursor.execute("SELECT * FROM users")

            result = self.database_manager.cursor.fetchall()
            self.revision_num = len(result)
        except:
            pass 

    def get_user_name(self, userid=-1):
        if userid < 0:
            raise ValueError("user id cannot be less than zero")

        #first check local database for user
        try:
            self.database_manager.cursor.execute("SELECT username FROM users WHERE userid=%d" % userid )
            result = self.database_manager.cursor.fetchone()

            if len(result) == 0:
                return None 
            
            return result[0]
        except Exception:
            pass
        
        #if not found, ask the server
        if self.client_socket is None:
            return None
        
        pk = packets.packets(packet_type=packets.GET_USERNAME_PACKET, 
                             userid=self.curr_sender_user,
                             receiverid=-1,
                             mesg_type=packets.TXT_DATA,
                             mesg=0 )

        if self.client_socket.send_msg_dontwait( pk.packet_to_str() ):
            reply_chunk = self.client_socket.recv_reply()
            pk.str_to_packet( reply_chunk )

            return pk.mesg

        del pk

    def get_users_from_server(self):
        """ 
        get all users from server and save then in clients database.
        request 1 users per request. [recursive]
        """

        if self.client_socket is None:
            return

        '''
        get all users from the server. The mesg section of packet is the revision
        number that the client is using to tell the server to send only those it does
        not known yet
        '''
        pk = packets.packets(packet_type=packets.GET_ALL_USERS_PACKET,
                             userid=self.curr_sender_user,
                             receiverid=-1,
                             mesg_type=packets.TXT_DATA,
                             mesg="%d" % (self.revision_num))

        if self.client_socket.send_msg_dontwait( pk.packet_to_str() ):
            reply_chunk = self.client_socket.recv_reply()
            pk.str_to_packet( reply_chunk )

            if int(pk.packet_type) == packets.USERS_PACKET:
                lt = str(pk.mesg).split(':')
                
                if len(lt) != 2:
                    return

                try:
                    self.database_manager.cursor.execute("INSERT INTO users VALUES(%d, '%s')" % 
                                                            ( int(lt[0]), str(lt[1]) ) )
                    self.revision_num = self.revision_num + 1
                    self.database_manager.db.commit()
                except Exception:
                    return
                
                self.get_users_from_server()
            else:
                return

        return

    def clear_user_cached_data(self, widget):
        if self.curr_sender_user == -1:
            return

        login_button = self.builder.get_object("login_button")
        settings_connect_toggle_button = self.builder.get_object("connect_togglebutton")

        files.display_msg_dialog(builder=self.builder,
                                primary_mesg="Clear All User Data",
                                second_mesg="Do you really want to delete all user data from the computer?",
                                dialog_icon=Gtk.MessageType.WARNING)

        if os.path.exists( os.path.normpath(files._USER_MEDIA_FOLDER_) ):
            pk = packets.packets(packet_type=packets.LOGOUT_PACKET,
                                userid=int(self.curr_sender_user),
                                receiverid=-1,
                                mesg_type=packets.TXT_DATA,
                                mesg="0")
            
            if self.client_socket.send_msg_dontwait( pk.packet_to_str() ):
                shutil.rmtree(os.path.normpath(files._USER_MEDIA_FOLDER_), ignore_errors=True)
                self.database_manager.database_disconnection()

                login_button.set_active(False)
                settings_connect_toggle_button.set_active(False)
        

    def get_login_users(self):
        pass