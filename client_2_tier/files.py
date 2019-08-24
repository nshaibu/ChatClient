#!/usr/bin/python3
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import os

_USER_HOME_ = os.path.expanduser("~")
_USER_MEDIA_FOLDER_ = os.sep.join( [_USER_HOME_, "cchat_media"] ) 
_USER_SENT_MEDIA_ = os.sep.join( [_USER_MEDIA_FOLDER_, "sent"] )
_USER_RECEIVED_MEDIA_ = os.sep.join( [_USER_MEDIA_FOLDER_, "received"] ) 


class File_Chooser():

    def __init__(self, builder, action=Gtk.FileChooserAction.OPEN):
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

    def run(self, event, pos, data=None):
        if pos == Gtk.EntryIconPosition.SECONDARY:
            return
        self.dailog.run()

    def on_ok_button(self, widget):
        slist = self.dailog.get_files()
        print(len(slist) )

        self.dailog.hide()

    def on_cancel_button(self, widget):
        self.dailog.hide()


class File_Handler():

    def __init__(self, builder):
        if not os.path.exists(_USER_MEDIA_FOLDER_):
            os.mkdir(_USER_MEDIA_FOLDER_)
        
        if not os.path.exists(_USER_RECEIVED_MEDIA_):
            os.mkdir(_USER_RECEIVED_MEDIA_)
        
        if not os.path.exists(_USER_SENT_MEDIA_):
            os.mkdir(_USER_SENT_MEDIA_)

        self.builder = builder
        self.selected_files = []