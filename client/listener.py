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
import socket
import sys 
import requests
import threading
import time
import datetime

import users

try:
    import geocoder
except ImportError as e:
    print("Install module geocoder %s" % str(e.args))
    sys.exit(1)

import packets

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Gdk


class Custom_Message_Display(Gtk.ListBoxRow):
    """
    a widget to display messages in the message listbox
    """
    
    def __init__(self, builder, users_manager, message=None, time=None, justify=Gtk.Justification.RIGHT):
        Gtk.ListBoxRow.__init__(self)
        self.uid = None    #unique identifier for this display
        self.users_manager = users_manager
        
        self.msg_listbox_listbox = builder.get_object("messges_display_listbox")
        self.listbox_scroll = builder.get_object("messages_scrollwindow")

        #self.listbox_scroll.connect( "size-allocate", self.auto_scroll_listbox ) #enable autoscrolling

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        
        self.message_label = Gtk.Label()
        self.time_label = Gtk.Label()

        self.eventbox = Gtk.EventBox()
        self.fixed = Gtk.Fixed()

        self.eventbox.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(red=65, green=65535, blue=65))
        self.eventbox.modify_fg(Gtk.StateType.NORMAL, Gdk.Color(red=0, green=0, blue=0))
        self.eventbox.connect("button_press_event", self.on_clicked_message)      

        self.vbox.pack_start(self.time_label, False, False, 2)
        self.vbox.pack_start(self.message_label, True, True, 2)

        self.time_label.set_justify(Gtk.Justification.LEFT)
        self.message_label.set_justify(Gtk.Justification.LEFT)

        if justify == Gtk.Justification.RIGHT:
            self.eventbox.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(red=65, green=65, blue=65535))
            self.eventbox.modify_fg(Gtk.StateType.NORMAL, Gdk.Color(red=65535, green=65535, blue=65535))
            
            self.hbox.pack_start(self.eventbox, True, True, 10)
            self.hbox.pack_start(self.fixed, True, True, 50) 
        else:
            self.eventbox.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(red=65, green=65535, blue=65))
            self.eventbox.modify_fg(Gtk.StateType.NORMAL, Gdk.Color(red=0, green=0, blue=0))
            
            self.hbox.pack_start(self.fixed, True, True, 50)
            self.hbox.pack_start(self.eventbox, True, True, 10)

        if not message is None:
            self.message_label.set_label(message)
            self.message_label.set_line_wrap(True)
            self.eventbox.add(self.vbox)
        
        if time is None:
            curr_tim = datetime.datetime.now()
            self.time_label.set_markup("<small><i>%s</i></small>" % curr_tim.strftime("%Y-%m-%d %H:%M"))
        else:
            self.time_label.set_markup("<small><i>%s</i></small>" % str(time))

        self.popover = Message_Display_Popover(builder, self)
        self.eventbox.set_border_width(3)
        self.add(self.hbox)

    def on_clicked_message(self, widget, event):
        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            self.popover.set_relative_to(self.eventbox)
            self.popover.show_all()
            self.popover.popup()

    def set_display_uid(self, uid):
        self.uid = uid

    def get_display_uid(self):
        return self.uid

    def write_to_display(self):
        self.msg_listbox_listbox.add(self)
        self.msg_listbox_listbox.show_all()

    def auto_scroll_listbox(self, widget=None, event=None, data=None):
        adj = self.listbox_scroll.get_vadjustment()
        adj.set_value( adj.get_upper() - adj.get_page_size() )


class Message_Display_Popover(Gtk.Popover):
    """
    Creates a popover when a messages is double clicked which allows 
    users to delete, copy and show the details of messages
    """

    def __init__(self, builder, _obj):
        Gtk.Popover.__init__(self)

        self.widget_obj = _obj   #the widget that have been clicked 
        
        self.msg_details_popover = Message_Details_Popover(builder)
        self.msg_details_popover.popover.set_relative_to(self.widget_obj.eventbox)
        
        listbox = Gtk.ListBox()

        row = Gtk.ListBoxRow()
        self.event1 = Gtk.EventBox()
        delete_msg = Gtk.Label()
        delete_msg.set_label("Delete Message")
        self.event1.add(delete_msg)
        row.add(self.event1)
        listbox.add(row)
        
        self.event1.connect("button_press_event", self.on_delete_msg_press)
        
        row = Gtk.ListBoxRow()
        self.event2 = Gtk.EventBox()
        clear_all_msg = Gtk.Label()
        clear_all_msg.set_label("Clear All Message")
        self.event2.add(clear_all_msg)
        row.add(self.event2)
        listbox.add(row)

        self.event2.connect("button_press_event", self.on_clear_all_msg_press)

        row = Gtk.ListBoxRow()
        self.event3 = Gtk.EventBox()
        copy_msg = Gtk.Label()
        copy_msg.set_label("Message Details")
        self.event3.add(copy_msg)
        row.add(self.event3)
        listbox.add(row)
        
        self.event3.connect("button_press_event", self.on_msg_details_press)

        self.set_position(Gtk.PositionType.BOTTOM)
        self.add(listbox)

    def run(self):
        self.show_all()
        self.popup()

    def on_delete_msg_press(self, widget, event):
        try:
            self.widget_obj.users_manager.database_manager.cursor.execute(  "DELETE FROM messages \
                                                                            WHERE message_id='%s'" %
                                                                                self.widget_obj.uid
                                                                        )
            self.widget_obj.users_manager.database_manager.db.commit()
        except Exception :
            self.widget_obj.users_manager.database_manager.db.rollback()
            return

        self.widget_obj.msg_listbox_listbox.remove( self.widget_obj )
        self.hide()

    def on_clear_all_msg_press(self, widget, event):
        
        children = self.widget_obj.msg_listbox_listbox.get_children()
        for row in children:
            try:
                self.widget_obj.users_manager.database_manager.cursor.execute(  "DELETE FROM messages \
                                                                                WHERE message_id='%s'" %
                                                                                    str(row.uid)
                                                                            )
                self.widget_obj.users_manager.database_manager.db.commit()               
            except Exception:
                self.widget_obj.users_manager.database_manager.db.rollback()
                continue

            self.widget_obj.msg_listbox_listbox.remove( row )

    def on_msg_details_press(self, widget, event):
        try:
            self.widget_obj.users_manager.database_manager.cursor.execute(  "SELECT * FROM messages \
                                                                            WHERE message_id='%s'" % 
                                                                                str(self.widget_obj.uid)
                                                                        )

            result = self.widget_obj.users_manager.database_manager.cursor.fetchone()
            
            self.msg_details_popover.set_message_id(result[0])
            
            try:
                name = self.widget_obj.users_manager.get_user_name( userid=int(result[1]) )
                if name is None:
                    self.msg_details_popover.set_sender( "None" )
                else:
                    self.msg_details_popover.set_sender( str(name) )
            except ValueError:
                self.msg_details_popover.set_sender( "None" )

            tim = time.localtime( float(result[3]) )
            self.msg_details_popover.set_time_received( time.strftime("%Y-%m-%d, %T", tim) )

            if int(result[4]) == -1:
                self.msg_details_popover.set_time_read("None")
            else:
                tim = time.localtime( float(result[4]) )
                self.msg_details_popover.set_time_read( time.strftime("%Y-%m-%d, %T", tim) )

            self.msg_details_popover.run()

        except Exception as e:
            print(str(e.args))
            return


class Message_Details_Popover():
    """a popover to show a detail information about a message"""

    def __init__(self, builder):
        self.builder = builder
        self.popover = self.builder.get_object("message_details_popover")

    def run(self):
        self.popover.show_all()
        self.popover.popup()

    def set_message_id(self, _id):
        self.message_id_label = self.builder.get_object("message_id_popover_label")
        self.message_id_label.set_label( str(_id) )

    def set_sender(self, userid):
        self.sender_label = self.builder.get_object("sender_msg_popoover_label")
        self.sender_label.set_label( str(userid) )

    def set_time_received(self, _time):
        self.time_received_label = self.builder.get_object("time_recieved_popover_label")
        self.time_received_label.set_label( str(_time) )

    def set_time_read(self, _time):
        self.time_sent_label = self.builder.get_object("time_read_popover_label")
        self.time_sent_label.set_label( str(_time) )


class StartThreadTask(threading.Thread):
    """creates a thread as a task"""
    
    def __init__(self, task_to_run=None):
        threading.Thread.__init__(self)
        
        self.thread_id = -1
        self.task = task_to_run     #the task to run
        self.param = None             #the parameter to pass to the task

    def run(self):

        if callable(self.task):
            if self.param is None:
                self.task()
            else:
                self.task( self.param )

        return


class Geolocation_Event():
    """Module that handles geolocation information for application"""
    
    def __init__(self):
        self.geo_cord = list()
        self.builder = None
        self.client_socket = None
        
        self.time_interval = 20        #amount of time in seconds to wait before next run
        self.timer_obj = None          #timer object
        
        self.cancel_thread = False     #to determine whether to cancel thread
        
    def geo_listener(self, param):          
        while True:
            if self.cancel_thread is True:
                break
                
            exception_occurred = False
                
            try:
                geo = geocoder.ip('me')
            except (requests.exceptions.HTTPError, 
                    requests.exceptions.ConnectionError,  
                    requests.exceptions.ReadTimeout, 
                    requests.exceptions.ProxyError,
                    requests.exceptions.RequestException,
                    requests.exceptions.RetryError,
                    requests.exceptions.SSLError,
                    ValueError ):
                exception_occurred = True

            if geo.ok == True and exception_occurred == False:
                tmp = geo.latlng

                if self.geo_cord != tmp:
                    self.geo_cord = tmp

                    pk = packets.packets(packet_type=packets.SET_GEO_PACKET,
                                         userid=param,
                                         receiverid=-1,
                                         mesg_type=packets.COORD_DATA,
                                         mesg="%f:%f" % (self.geo_cord[0], self.geo_cord[1]) )
                
                    self.client_socket.send_msg_dontwait( pk.packet_to_str() )

            time.sleep(self.time_interval)
        return
                

    def register_geolocation_event(self, userid=-1):
        self.timer_obj = StartThreadTask(task_to_run=self.geo_listener)
        self.timer_obj.param = userid
        self.timer_obj.start()

    def unregister_geolocation_event(self):
        if not self.timer_obj is None:  
            self.cancel_thread = True


class Network_Listener():
    """Listener to listen for any in-coming and out-going packets"""
    
    def __init__(self):
        self.listener_source_id = -1
        self.client_socket = None
        self.builder = None
        self.users_manager = None

    def register_listener_event(self):
        
        def listener(widget):
            reply_chunk = None
            try:
                reply_chunk = self.client_socket.recv_reply(flags=socket.MSG_DONTWAIT)
            except (BlockingIOError, OSError):
                reply_chunk = None

            if not reply_chunk is None:
                pk = packets.packets()
                pk.str_to_packet( reply_chunk )

                pk.interpret_packet(builder=self.builder, 
                                    users_manager=self.users_manager )

            return True

        self.listener_source_id = GObject.timeout_add(1000, listener, None)

    def unregister_listener_event(self):
        if self.listener_source_id == -1:
            return
        GObject.source_remove( self.listener_source_id )