#!/usr/bin/python3
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import os
from platform import system

_USER_HOME_ = os.path.expanduser("~")

if system() == 'Windows':
    _APPDATA_ = os.getenv("AppData", default=os.path.normpath(os.sep.join([_USER_HOME_, "AppData"])) )
    media_folder = os.sep.join( [_APPDATA_, "cchat_media"] )
else:    
    media_folder = os.sep.join( [_USER_HOME_, "cchat_media"] ) 

_USER_MEDIA_FOLDER_ = media_folder
_USER_SENT_MEDIA_ = os.sep.join( [_USER_MEDIA_FOLDER_, "sent"] )
_USER_RECEIVED_MEDIA_ = os.sep.join( [_USER_MEDIA_FOLDER_, "received"] ) 


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


class File_Chooser():

    def __init__(self, builder, title="", default_dir=_USER_HOME_, action=Gtk.FileChooserAction.OPEN, container=list()):
        self.dailog = builder.get_object("upload_filechooser")
        self.cancel_button = builder.get_object("file_chooser_cancel_button")
        self.ok_button = builder.get_object("file_chooser_ok_button")

        #connects signals
        self.cancel_button.connect("clicked", self.on_cancel_button)
        self.ok_button.connect("clicked", self.on_ok_button)

        self.dailog.connect("delete-event", lambda signal, widget:self.on_cancel_button(widget) )

        #set widgets properties
        self.dailog.set_property("action", action)
        self.dailog.set_property("local-only", True)
        self.dailog.set_property("show-hidden", True)
        self.dailog.set_property("select-multiple", True)

        self.dailog.set_title(title)
        self.dailog.set_current_folder(default_dir)

        self.container = container

        filter = Gtk.FileFilter()
        filter.set_name("text file")
        filter.add_mime_type("text/plain")

        self.dailog.add_filter(filter)

    def run(self, event, pos, data=None):
        if pos == Gtk.EntryIconPosition.SECONDARY:
            return
        self.dailog.run()

    def on_ok_button(self, widget):
        slist = self.dailog.get_files()
        count = len(slist)
        self.container.clear()

        for i in range(count):
            self.container.append( os.path.normpath(slist[i].get_path()) )

        self.dailog.hide()

    def on_cancel_button(self, widget):
        self.dailog.hide()


class File_Handler():

    def __init__(self, builder=None):
        if not os.path.exists(_USER_MEDIA_FOLDER_):
            os.mkdir(_USER_MEDIA_FOLDER_)
        
        if not os.path.exists(_USER_RECEIVED_MEDIA_):
            os.mkdir(_USER_RECEIVED_MEDIA_)
        
        if not os.path.exists(_USER_SENT_MEDIA_):
            os.mkdir(_USER_SENT_MEDIA_)

        self.builder = builder
        self.selected_files = []


    def upload_files_vault(self):
        pass

    def send_files_user(self):
        pass