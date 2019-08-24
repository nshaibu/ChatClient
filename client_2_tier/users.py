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

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import packets
import files

try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb 
except ImportError as err:
    print("ImportError: %s\n" % err.args)
    print("Install package [pip install pymysql]")
    sys.exit(1)

import sqlite3

_USR_DB_FOLDER_ = os.sep.join( [files._USER_MEDIA_FOLDER_, "DB"] )
__DB_NAME__ = "concurrent_chat_client_2018_04_08"
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

        self.db_hostname = None
        self.db_username = None
        self.db_passwd = None

    def init_database_popover(self, builder):
        ''' initialize database popover after a builder object have been passed'''

        self.database_popover = builder.get_object("database_popover")

        #database popover entry fields
        self.db_hostname_entry = builder.get_object("database_host_entry_field")
        self.db_username_entry = builder.get_object("database_username_entry_field")
        self.db_userpasswd_entry = builder.get_object("database_userpasswd_entry_field")

        #database popover buttons
        self.db_cancel_button = builder.get_object("database_cancel_button")
        self.db_connect_toggle_button = builder.get_object("database_connection_toggle_button")

        #set events or signals for database popover 
        self.db_connect_toggle_button.connect("toggled", self.on_database_connection_toggle_button_toggled)
        self.db_cancel_button.connect("clicked", self.on_database_cancel_button_clicked)

    def popover_run(self, widget):
        ''' show or pop up database popover '''
        self.database_popover.show_all()

    def database_connection(self):
        if self.db_hostname is None:
            self.db_hostname = "localhost"
        
        check_none = lambda x: x is None and "" or str(x)
        try:
            self.db = MySQLdb.connect( str(self.db_hostname),
                                       check_none(self.db_username), 
                                       check_none(self.db_passwd),
                                       ""
                                     )
            
            self.cursor = self.db.cursor()
        except (MySQLdb.err.OperationalError, MySQLdb.err.InternalError):
            return False 

        try:
        #check whether database exist if not create it
            self.cursor.execute("SELECT SCHEMA_NAME FROM \
                                INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '%s'" % __DB_NAME__)

            result = self.cursor.fetchall()
            
            if len(result) == 0:
                self.cursor.execute("CREATE DATABASE %s" % __DB_NAME__)

                self.cursor.execute("CREATE TABLE %s.users ( \
                                    userid INTEGER NOT NULL PRIMARY KEY, \
                                    username VARCHAR(%d) \
                                    )" %  (__DB_NAME__, __NAME_BUF_SIZE__) )

                self.cursor.execute("CREATE TABLE %s.messages ( \
                                    message_id VARCHAR(100) NOT NULL PRIMARY KEY, \
                                    sender_id INTEGER NOT NULL, \
                                    receiver_id INTEGER NOT NULL, \
                                    time_received DECIMAL(20, 0), \
                                    time_read DECIMAL(20, 0), \
                                    msg_type INTEGER NOT NULL, \
                                    message VARCHAR(%d) \
                                    )" %  (__DB_NAME__, packets.MAX_DATA_SIZE) )
                self.db.commit()
            
        except Exception:
            self.db.rollback()
      
        return True

    def database_connection2(self):
        if not os.path.exists( os.path.normpath(files._USER_MEDIA_FOLDER_) ):
            os.mkdir( os.path.normpath(files._USER_MEDIA_FOLDER_) )
            os.mkdir( os.path.normpath(_USR_DB_FOLDER_) )

        if not os.path.exists( os.path.normpath(os.sep.join([_USR_DB_FOLDER_, __DB_NAME__])) ):
            self.db = sqlite3.connect(os.sep.join([_USR_DB_FOLDER_, __DB_NAME__]))
            self.cursor = self.db.cursor()

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
            except:
                self.db.rollback()
                os.remove( os.path.normpath(os.sep.join([_USR_DB_FOLDER_, __DB_NAME__])) )

    def database_disconnection(self):
        if self.db is None:
            return
        self.db.commit()
        self.db.close()

    def on_database_connection_toggle_button_toggled(self, widget):
        if self.db_connect_toggle_button.get_active():
            self.db_hostname = self.db_hostname_entry.get_text()
            self.db_username = self.db_username_entry.get_text()
            self.db_passwd = self.db_userpasswd_entry.get_text()

            if not self.database_connection():
                    self.db_connect_toggle_button.set_active(False)
        else:
            self.database_disconnection()

    def on_database_cancel_button_clicked(self, widget):
        self.database_popover.hide()


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
            self.database_manager.cursor.execute("SELECT * FROM %s.users" % __DB_NAME__)

            result = self.database_manager.cursor.fetchall()
            self.revision_num = len(result)
        except:
            pass 

    def get_user_name(self, userid=-1):
        if userid < 0:
            raise ValueError("user id cannot be less than zero")

        #first check local database for user
        try:
            self.database_manager.cursor.execute("SELECT username FROM %s.users WHERE userid=%d" % (__DB_NAME__, userid) )
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
                    self.database_manager.cursor.execute("INSERT %s.users VALUES(%d, '%s')" % 
                                                            ( __DB_NAME__, int(lt[0]), str(lt[1]) ) )
                    self.revision_num = self.revision_num + 1
                    self.database_manager.db.commit()
                except Exception:
                    return
                
                self.get_users_from_server()
            else:
                return

        return


    def get_login_users(self):
        pass
