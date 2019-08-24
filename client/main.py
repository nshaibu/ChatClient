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
import sys, time, datetime
import requests
import hashlib
import uuid

import packets
import users
import files
import listener

try:
    from ipaddress import ip_address
except ImportError as err:
    print("ImportError: %s" % err.args)
    print("Install the package:[ipaddress]")
    sys.exit(1)

try:
    import geocoder
except ImportError as e:
    print("Install module geocoder %s" % str(e.args))
    sys.exit(1)

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf


glade_file = "main.glade"


'''
This is to make sure that the user have connected to the server before
trying to authenticate
''' 
config_connect = False  

files_manager = files.File_Handler()

'''
This global object is an instance of class users.Users_handler that managers
all user accounts at client side
'''
users_manager = users.Users_handler()

'''event listener for the socket'''
socket_listener = listener.Network_Listener()

'''event for setting and getting geolocational information'''
geo_event = listener.Geolocation_Event()

#generates hash of strings passed to it
gen_hash = lambda x: x not in [None, ""] and hashlib.md5( str(x).encode(encoding="utf-8") ).hexdigest() or str(-1)


def display_msg_dialog(builder, primary_mesg="", second_mesg="", dialog_icon=Gtk.MessageType.INFO):
    if builder is None:
        return 
    
    dialog = builder.get_object("window_message_dialog")
    dialog.format_secondary_text( str(second_mesg) )

    dialog.set_property("message-type", dialog_icon)
    dialog.set_property("text", str(primary_mesg))
    
    
    dialog.connect("delete-event", lambda signal, widget: dialog.hide())
    
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        dialog.hide()

    
def clear_message_display(builder):
    """
    Clears the message display when context have been shift to a new user
    """

    msg_listbox = builder.get_object("messges_display_listbox")

    children = msg_listbox.get_children()
    for widget in children:
        msg_listbox.remove(widget)


def get_messages_from_db_to_display(builder, senderid, receiverid):
    """Get all messages for the conversation between this users and display them"""

    try:
        users_manager.database_manager.cursor.execute("SELECT * FROM messages \
                                                       WHERE sender_id=%d AND receiver_id=%d \
                                                       OR sender_id=%d AND receiver_id=%d \
                                                       ORDER BY time_received" % ( 
                                                       int(senderid), 
                                                       int(receiverid),
                                                       int(receiverid),
                                                       int(senderid) ) )

        result = users_manager.database_manager.cursor.fetchall()

        for row in result:
            
            get_time_tuple = lambda : int(row[4]) == -1 and time.localtime( float(row[3]) ) or time.localtime( float(row[4]) )

            if int(row[1]) == int(senderid):
                mesg_display = listener.Custom_Message_Display( builder,
                                                                users_manager, 
                                                                message=str(row[6]),
                                                                time=time.strftime( "%Y-%m-%d %H:%M", get_time_tuple() ), 
                                                                justify=Gtk.Justification.RIGHT )
                mesg_display.set_display_uid( str(row[0]) )
                mesg_display.write_to_display()
                mesg_display.auto_scroll_listbox()
            else:
                mesg_display = listener.Custom_Message_Display( builder,
                                                                users_manager,
                                                                message=str(row[6]),
                                                                time=time.strftime( "%Y-%m-%d %H:%M", get_time_tuple() ),
                                                                justify=Gtk.Justification.LEFT )

                mesg_display.set_display_uid( str(row[0]) )
                mesg_display.write_to_display()
                mesg_display.auto_scroll_listbox()

            if int(row[4]) == -1:   #if not read
                try:
                    users_manager.database_manager.cursor.execute("UPDATE messages SET time_read=%d \
                                                                    WHERE message_id='%s' " % (
                                                                        time.time(),
                                                                        str(row[0])
                                                                    ) )
                    users_manager.database_manager.db.commit()
                except Exception:
                    users_manager.database_manager.db.rollback()
        
    except Exception:
        users_manager.database_manager.db.rollback()

    return


class Custom_button(Gtk.EventBox):
    """Create a button with image on the left and two labels vertically aligned also to the right"""

    def __init__(self, image_=None, label=None):
        Gtk.EventBox.__init__(self)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        hbox_down = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)

        picbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(image_, 35, 35)

        self.image = Gtk.Image()
        self.name_label = Gtk.Label()
        self.status_label = Gtk.Label()
        self.message_count_label = Gtk.Label()     #the number of messages sent by user and not yet read

        self.name_label.set_justify(Gtk.Justification.LEFT)
        self.status_label.set_justify(Gtk.Justification.LEFT)
        self.message_count_label.set_justify(Gtk.Justification.LEFT)

        self.image.set_from_pixbuf(picbuf)
        self.name_label.set_markup("<b>%s</b>" % str(label).capitalize() )
        self.message_count_label.set_label("0") #set_markup("<small><i>0</i></small>")

        hbox.pack_start(self.image, False, False, 0)
        vbox.pack_start(self.name_label, False, False, 0)

        hbox_down.pack_start(self.message_count_label, False, False, 0)
        hbox_down.pack_start(self.status_label, False, False, 0)

        vbox.pack_start(hbox_down, False, False, 0)
        hbox.pack_start(vbox, False, False, 0)

        self.set_border_width(6)
        self.add(hbox)
        

class Users_Button(Gtk.ListBoxRow):
    """Creates a button for each user to be added to the USERS listbox"""

    def __init__(self):
        Gtk.ListBoxRow.__init__(self)

        self.button = None
        self.userid = -1
        self.username = None 

        self.builder = None

    def create_button(self, image, label_):
        self.button = Custom_button(image_=image, label=label_)
        self.add(self.button)

    def connect_event_to_button(self):
        if self.button is None:
            return False

        self.button.connect("button-press-event", self.on_press_button)
        return True

    def on_press_button(self, signal, widget):
        users_manager.curr_receiver_user = self.userid

        clear_message_display(self.builder)

        get_messages_from_db_to_display(self.builder, 
                                        senderid=self.userid, 
                                        receiverid=users_manager.curr_sender_user)
        
        self.button.message_count_label.set_label("0") #reset counter

        def task(param):
            reply_chunk = None
            pk = packets.packets(packet_type=packets.GET_GEO_PACKET,
                                userid=users_manager.curr_sender_user,
                                receiverid=self.userid,
                                mesg_type=packets.TXT_DATA,
                                mesg="0")

            if users_manager.client_socket.send_msg_dontwait( pk.packet_to_str() ):
                reply_chunk = users_manager.client_socket.recv_reply()
                if reply_chunk is None: return
                
                pk.str_to_packet( reply_chunk )

                lt = str(pk.mesg).split(':')
                if lt == [float(-1), float(-1)]: return

                if len(lt) == 2:
                    try:
                        geo = geocoder.google(lt, method='reverse')
                    except (requests.exceptions.HTTPError, 
                            requests.exceptions.ConnectionError, 
                            requests.exceptions.ReadTimeout, 
                            requests.exceptions.ProxyError,
                            requests.exceptions.RequestException,
                            requests.exceptions.RetryError,
                            requests.exceptions.SSLError,
                            ValueError):
                        return

                    if geo.ok == True:
                        status_msg = str(geo.country) + ',' + str(geo.city)
                        param.status_label.set_markup("<small><i>%s</i></small>" % status_msg)

            return

        tasks_obj = listener.StartThreadTask(task_to_run=task)
        tasks_obj.param = self.button

        tasks_obj.start()


def load_users_and_create_buttons(builder):
    """
    Load users from database and while doing that create
    a button for each and append to listbox for users
    """

    listbox = builder.get_object("users_listbox")

    users_manager.database_manager.cursor.execute("SELECT * FROM users WHERE NOT userid=%d" %
                                                    users_manager.curr_sender_user)

    result = users_manager.database_manager.cursor.fetchall()

    for row in result:

        user_button_listboxrow = Users_Button()
        
        user_button_listboxrow.userid = int(row[0])
        user_button_listboxrow.username = str(row[1])
        user_button_listboxrow.builder = builder

        user_button_listboxrow.create_button( "./icon/user.png", str(row[1]) )
        user_button_listboxrow.connect_event_to_button()
        
        listbox.add(user_button_listboxrow)

    listbox.show_all()


def clear_users_buttons(builder):
    """
    clear custom users button from users frame when users is
    logging out
    """
    
    listbox = builder.get_object("users_listbox")

    for row in listbox.get_children():
        listbox.remove(row)



class Main_window():
    """Main window for the whole application. It is the entry point for all the widgets"""

    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(glade_file)
        
        users_manager.builder = self.builder
        socket_listener.builder = self.builder

        self.client_socket = Network_Socket()

        #assigning sockets structures
        users_manager.client_socket = self.client_socket
        socket_listener.client_socket = self.client_socket
        geo_event.client_socket = self.client_socket

        socket_listener.users_manager = users_manager

        self.main_window = self.builder.get_object("main_window")
        self.main_window.connect("delete-event", self.on_delete)
        
        #toolbar popovers
        self.user_info_popover = User_Information_PopOver(self.builder, self.client_socket)
        self.settings_popover = Settings_PopOver(self.builder, self.client_socket)
        
        #toolbar buttons
        self.user_info_toolbutton = self.builder.get_object("auth_toolbutton")
        self.settings_toolbutton = self.builder.get_object("settings_toolbutton")
        self.clear_cache_toolbutton = self.builder.get_object("clear_cache_toolbutton")

        #connect signals to toolbar buttons
        self.user_info_toolbutton.connect("clicked", self.user_info_popover.run)
        self.settings_toolbutton.connect("clicked", self.settings_popover.run)
        self.clear_cache_toolbutton.connect("clicked", users_manager.clear_user_cached_data)

        #toolbar decoration
        self.main_toolbar = self.builder.get_object("main_toolbar")
        context = self.main_toolbar.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        #message entry field widgets
        self.mesg_entry = Message_Entry_Field(self.builder, self.client_socket)
        self.mesg_entry.send_button.connect("clicked", self.mesg_entry.on_Messages_textentry_activate)

    def run(self):
        self.main_window.show_all()
        Gtk.main()

    def on_delete(self, builder, widget):
        if self.user_info_popover.login_button.get_active():
            pk = packets.packets(packet_type=packets.LOGOUT_PACKET,
                                userid=users_manager.curr_sender_user,
                                receiverid=-1,
                                mesg_type=packets.TXT_DATA,
                                mesg="0")

            if self.user_info_popover.client_socket.send_msg_dontwait( pk.packet_to_str() ):
                clear_users_buttons(self.builder)
                clear_message_display(self.builder)

                socket_listener.unregister_listener_event()
                geo_event.unregister_geolocation_event()

                self.user_info_popover.login_button.set_active(False)
            else:
                display_msg_dialog( self.builder, 
                                    primary_mesg="Close Connection Request Failed",
                                    second_mesg="Could not logout successfully so close connection request failed.\
                                    you can manually close the connection before exiting." 
                                )

                return

            del pk

            pk = packets.packets(packet_type=packets.CLOSE_PACKET,
                                userid=users_manager.curr_sender_user,
                                receiverid=-1,
                                mesg_type=packets.TXT_DATA,
                                mesg="0")

            self.user_info_popover.client_socket.send_msg_dontwait( pk.packet_to_str() )
        Gtk.main_quit()


class Message_Entry_Field():
    """Manages the text entry field of the main window"""

    def __init__(self, builder, cli_socket):
        self.builder = builder
        self.entry_field = self.builder.get_object("Messages_textentry")
        self.send_button = self.builder.get_object("send_button")

        self.client_socket = cli_socket

        #filechooser widget for file upload
        self.filechooser = files.File_Chooser(  builder=self.builder,
                                                title="select files to upload", 
                                                container=files_manager.selected_files)

        #set signal to send message when user press enter key when entry_field has the focus
        self.entry_field.connect("activate", self.on_Messages_textentry_activate)
        self.entry_field.connect("icon-press", self.filechooser.run)

    def on_Messages_textentry_activate(self, widget):
        pk = packets.packets(packet_type=packets.MSG_PACKET, 
                            userid=users_manager.curr_sender_user,
                            receiverid=users_manager.curr_receiver_user,
                            mesg_type=packets.TXT_DATA,
                            mesg="%s" % str( self.entry_field.get_text() ))
        
        if users_manager.curr_receiver_user == -1:
            display_msg_dialog( self.builder, 
                                primary_mesg="No receiver selected",
                                second_mesg="you have not selected any receive for this message",
                                dialog_icon=Gtk.MessageType.ERROR)
            return

        self.entry_field.set_text("")
        if self.client_socket.send_msg_dontwait( pk.packet_to_str() ):
            uid = str(uuid.uuid4().hex)
            list_display = listener.Custom_Message_Display( self.builder, 
                                                            users_manager,
                                                            message=str( pk.mesg ), 
                                                            justify=Gtk.Justification.LEFT)
            list_display.set_display_uid(uid)
            list_display.write_to_display()
            list_display.auto_scroll_listbox()
            
            tim = time.time()

            try:
                users_manager.database_manager.cursor.execute("INSERT INTO messages \
                                                            VALUES('%s', %d, %d, %ld, %ld, %d, '%s') \
                                                            " % (uid,    #unique id for messages
                                                                int(pk.userid),        #sender id
                                                                int(pk.receiverid),    #receiver id
                                                                tim,                     #time sent(in seconds since unix epoch)
                                                                tim,                     #time read(in seconds since unix epoch)
                                                                int(pk.mesg_type),     #message type
                                                                pk.mesg))              #message
                users_manager.database_manager.db.commit()
            except Exception:
                users_manager.database_manager.db.rollback()
        else:
            display_msg_dialog( self.builder,
                                primary_mesg="Message not sent",
                                second_mesg="check whether you still connected to the server or the server is down",
                                dialog_icon=Gtk.MessageType.ERROR)


class User_Information_PopOver():
    """user information popover for main toolbar"""

    def __init__(self, builder, network_socket):
        self.builder = builder
        self.popover = self.builder.get_object("user_information_popover")

        self.client_socket = network_socket

        self.user_name = None       #name for the user
        self.user_password = None   #password for users
        
        #popover buttons
        self.cancel_button = self.builder.get_object("user_info_cancel_button")
        self.login_button = self.builder.get_object("login_button")
        self.register_button = self.builder.get_object("registration_button")

        #connect signals to popover buttons
        self.cancel_button.connect("clicked", self.on_user_info_cancel_button_clicked)
        self.login_button.connect("toggled", self.on_login_button_toggled)
        self.register_button.connect("clicked", self.on_registration_button_clicked)

        #text fields
        self.name_text_field = self.builder.get_object("popover_name_textentry")
        self.password_text_field = self.builder.get_object("popover_password_textentry")

        #buttons
        self.settings_connect_toggle_button = self.builder.get_object("connect_togglebutton")

    def run(self, builder):
        self.popover.show_all()

    def on_user_info_cancel_button_clicked(self, widget):
        self.popover.hide()

    def on_login_button_toggled(self, widget):
        global config_connect

        if config_connect == False:
            if self.login_button.get_active():
                display_msg_dialog( self.builder, 
                                    "Not Connect to the server", 
                                    "connect to server before", 
                                    dialog_icon=Gtk.MessageType.ERROR )
            
            self.login_button.set_active(False)
            return 

        if self.login_button.get_active():
            self.user_name = self.name_text_field.get_text()
            self.user_password = self.password_text_field.get_text()

            if self.user_name == "" and self.user_password == "":
                if self.login_button.get_active():
                    display_msg_dialog( self.builder, 
                                        "Empty fields not allowed", 
                                        "either name and password cannot be empty", 
                                        Gtk.MessageType.ERROR)

                self.login_button.set_active(False)
                return

            pk = packets.packets(userid=-1, receiverid=-1)   #create a packet
            pk.packet_type = packets.AUTH_PACKET           #authentication packe
            pk.mesg_type = packets.COORD_DATA              #coordinate data
            pk.mesg = ':'.join( [self.user_name, gen_hash(self.user_password)] )

            if self.client_socket.send_msg_dontwait( pk.packet_to_str() ):
                reply_chunk = self.client_socket.recv_reply()
                pk.str_to_packet( reply_chunk )
                    
                if not pk.interpret_packet():
                    
                    if self.login_button.get_active():
                        display_msg_dialog(self.builder, 
                                           "Authentication failed", 
                                           "check and type username and password correctly. connection to server have been closed. you have to reconnect", 
                                           Gtk.MessageType.ERROR)
                    
                    config_connect = False
                    
                    self.settings_connect_toggle_button.set_active(False)
                    self.login_button.set_active(False)
                    return

                users_manager.curr_sender_user = int(pk.userid)
                try:
                    users_manager.set_revision_number()
                except ConnectionError as e:
                    pk.packet_type = packets.LOGOUT_PACKET
                    pk.userid = users_manager.curr_sender_user
                    pk.receiverid = -1
                    pk.mesg_type = packets.TXT_DATA
                    pk.mesg = "0"

                    self.client_socket.send_msg_dontwait( pk.packet_to_str() )

                    if self.login_button.get_active():
                        display_msg_dialog(self.builder, 
                                           "Connection Error", 
                                           "You have not connect to database server yet %s" % str(e.args), 
                                           Gtk.MessageType.ERROR)

                    config_connect = False
                    
                    self.login_button.set_active(False)
                    self.settings_connect_toggle_button.set_active(False)
                    return
                
                users_manager.get_users_from_server()
                 
                load_users_and_create_buttons(self.builder)
                
                socket_listener.register_listener_event()   #register socket listener
                geo_event.register_geolocation_event( userid=users_manager.curr_sender_user )  #register geolocation event
            else:
                clear_users_buttons(self.builder)

                socket_listener.unregister_listener_event()
                geo_event.unregister_geolocation_event()
                
                if self.login_button.get_active():
                    display_msg_dialog(self.builder, "Request Not Sent", "login request not sent")
                self.login_button.set_active(False)
                
                
            
            del pk
        else:
            pk = packets.packets(packet_type=packets.LOGOUT_PACKET, userid=int(users_manager.curr_sender_user), receiverid=-1)
            pk.mesg_type = packets.TXT_DATA
            pk.mesg = "%d" % 0

            if self.client_socket.send_msg_dontwait( pk.packet_to_str() ):
                config_connect = False

                clear_users_buttons(self.builder)
                clear_message_display(self.builder)

                users_manager.database_manager.database_disconnection()

                socket_listener.unregister_listener_event()
                geo_event.unregister_geolocation_event()
                self.settings_connect_toggle_button.set_active(False)

            del pk

    def on_registration_button_clicked(self, widget):
        if config_connect == False:
            display_msg_dialog( self.builder, 
                                "Not Connect to the server", 
                                "connect to server before", 
                                dialog_icon=Gtk.MessageType.ERROR )
            return

        self.user_name = self.name_text_field.get_text()
        self.user_password = self.password_text_field.get_text()

        if self.user_name == "" and self.user_password == "":
            display_msg_dialog( self.builder, 
                                "Empty fields not allowed", 
                                "name and password cannot be empty", 
                                Gtk.MessageType.ERROR)
            return

        pk = packets.packets(packet_type=packets.REG_PACKET, userid=-1, receiverid=-1)
        pk.mesg_type = packets.COORD_DATA
        pk.mesg = ':'.join( [self.user_name, gen_hash(self.user_password)] )

        if self.client_socket.send_msg_dontwait( pk.packet_to_str() ):
            reply_chunk = self.client_socket.recv_reply()
            pk.str_to_packet(reply_chunk)

            if not pk.interpret_packet():
                display_msg_dialog(self.builder, 
                                   "Request Failed", 
                                   "registration request failed. user already on the system")
        else:
            pass

        del pk


class Network_Socket():
    """creates and destroys sockets"""

    def __init__(self, hostname=None, port_num=None):
        self.socket = None

        self._hostname = hostname
        self._portnum = port_num

    @property
    def port_num(self):
        return self._portnum
    
    @port_num.setter
    def port_num(self, port):
        self._portnum = port

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, hostname):
        ip_obj = None
        try:
            ip_obj = ip_address( hostname )
        except ValueError:         #ip address is wrong or is hostname so resolve it
            addr = str(hostname).split('.')
            
            if len(addr) >= 4:      #if it is a wrong ip address then size of list is greater than or equal to 4  
                raise ValueError("IP address is wrong %s" % hostname)
            else:                   #Then it is a hostname then resolve it
                self._hostname = socket.gethostbyname( hostname )  #raise except if not able to resolve

        if ip_obj is not None:
            self._hostname = hostname


    def connect(self):
        if self.hostname is None or self.port_num is None:
            raise ConnectionError("hostname or port number fields cannot be empty") 
        else:
            try:
                self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                self.socket.connect( (self.hostname, int(self.port_num)) )
            except socket.error as e:
                raise ConnectionError("Connecting to server failed %s" % str(e.args))

    def disconnect(self):
        pk = packets.packets(packet_type=packets.CLOSE_PACKET, 
                             userid=-1, 
                             receiverid=-1, 
                             mesg_type=packets.FILE_TXT_DATA, 
                             mesg=0)

        try:
            self.send_msg_dontwait( pk.packet_to_str() )
            self.socket.shutdown( socket.SHUT_RDWR )
        except (BrokenPipeError, OSError):
            pass

        self.socket.close()

    def send_msg_dontwait(self, message):
        
        try:
            mesg = str(message).encode(encoding="utf-8")
            self.socket.sendall(mesg, socket.MSG_DONTWAIT)
            return True
        except (BrokenPipeError, UnicodeEncodeError, OSError):
            return False

    def recv_reply(self, flags=0):
        return self.socket.recv(packets.MAX_PACKET_SIZE, flags)



class Settings_PopOver():
    """popover for server connection"""

    def __init__(self, builder, network_socket):
        self.builder = builder
        self.popover = self.builder.get_object("settings_popover")

        self.client_socket = network_socket   #network infos

        #popover buttons
        self.cancel_button = self.builder.get_object("settings_cancel_button")
        self.connect_button = self.builder.get_object("connect_togglebutton")

        #popover signals connection
        self.cancel_button.connect("clicked", self.on_settings_cancel_button_clicked)
        self.connect_button.connect("toggled", self.on_connect_togglebutton_toggled)

        #popover entry field
        self.host_addr_entry = self.builder.get_object("server_addr_textentry")
        self.port_num_entry = self.builder.get_object("port_num_spinbutton")

    def on_connect_togglebutton_toggled(self, widget):
        global config_connect

        if self.connect_button.get_active():
            try:
                self.client_socket.hostname = self.host_addr_entry.get_text()
            except ValueError as e:
                display_msg_dialog(self.builder, "Hostname Error", second_mesg=str(e.args), dialog_icon=Gtk.MessageType.ERROR)
                return
            except socket.gaierror as e:
                display_msg_dialog(self.builder, "Hostname Error", second_mesg=str(e.args), dialog_icon=Gtk.MessageType.ERROR)
                return

            self.client_socket.port_num = self.port_num_entry.get_text()

            try:
                self.client_socket.connect()
                users_manager.database_manager.database_connection()
                config_connect = True   
            except ConnectionError as e:
                display_msg_dialog(self.builder, "Connect Error", second_mesg=str(e.args), dialog_icon=Gtk.MessageType.ERROR)
                self.connect_button.set_active(False)
                return
        else:
            if config_connect == True:
                self.client_socket.disconnect()
                users_manager.database_manager.database_disconnection()
                config_connect = False

    def on_settings_cancel_button_clicked(self, widget):
        self.popover.hide()

    def run(self, builder):
        self.popover.show_all()

if __name__ == '__main__':
    window = Main_window()
    window.run()