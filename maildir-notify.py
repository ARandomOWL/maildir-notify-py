#!/usr/bin/python2
# Author: Adrian R Wheeldon <adrian at awheeldon dot com>
# Based on: https://bbs.archlinux.org/viewtopic.php?pid=962423#p962423
# This version is modified to handle mailboxes with spaces in the names
# Modified to use Adwaita icon rather than oxygen icon

import pyinotify
import pynotify
from os.path import expanduser
from mailbox import MaildirMessage
from email.header import decode_header
import gtk
import gobject
from gtk.gdk import pixbuf_new_from_file
import re

unread_mail_icon = r"/usr/share/icons/Adwaita/32x32/status/mail-unread.png"
read_mail_icon = r"/usr/share/icons/Adwaita/32x32/status/mail-read.png"
mailbox_file = expanduser(r"~/.mutt/mailboxes")
maildir_folder = expanduser(r"~/Maildir/")
notification_timeout = 12000
ignore = "trash$|spam$|sent$|junk|drafts?$|calendar|outbox|clutter$"
enable_desktop_notifications = False

unread_icon_pixbuf = pixbuf_new_from_file(unread_mail_icon)
read_icon_pixbuf = pixbuf_new_from_file(read_mail_icon)

gobject.threads_init()  # Allows GTK functions to be called from other threads (I think...)

class desktop_notification(pyinotify.ProcessEvent):
    def __init__(self, name):
        pynotify.init(name)

    def process_IN_CREATE(self,event):
        self.notify_pre(event)

    def process_IN_MOVED_TO(self,event):
        self.notify_pre(event)

    def process_IN_DELETE(self,event):
        i_tray_icon.set_icon_old_mail()

    def process_IN_MOVED_FROM(self,event):
        i_tray_icon.set_icon_old_mail()

    def notify_pre(self, event):
        i_tray_icon.set_icon_new_mail()
        if (enable_desktop_notifications):
            self.notify(event)

    def notify(self, event):
        # Handling a new mail
        dec_header = lambda h : ' '.join(unicode(s, e if bool(e) else 'ascii') for s, e in decode_header(h))

        fd = open(event.pathname, 'r')
        mail = MaildirMessage(message=fd)
        From = "From: " + dec_header(mail['From'])
        Subject = "Subject: " + dec_header(mail['Subject'])
        n = pynotify.Notification("New mail in "+'/'.join(event.path.split('/')[-3:-1]), From+ "\n"+ Subject)
        fd.close()
        n.set_icon_from_pixbuf(unread_icon_pixbuf)
        n.set_timeout(notification_timeout)
        n.show()

def quit_app(something):
    if (i_tray_icon.enabled == True):
        i_filesystem_watcher.stop()
    gtk.main_quit()

class tray_icon:
    def __init__(self):
        self.enabled = True
        self.status_icon = gtk.status_icon_new_from_pixbuf(read_icon_pixbuf)
        self.menu = gtk.Menu()

        self.menu_quit = gtk.MenuItem("Quit")
        self.menu_quit.connect_object("activate", quit_app, None)
        self.menu.append(self.menu_quit)
        self.menu_quit.show()

        self.status_icon.connect('popup-menu', self.menu_popup)
        self.status_icon.connect('activate', self.toggle_disable)

    def menu_popup(self, data, button, time):
        self.menu.popup(None, None, None, button, time)

    def toggle_disable(self, data):
        if (self.enabled == True):
            self.disable()
            self.enabled = False
        else:
            self.enable()
            self.enabled = True

    def enable(self):
        self.set_icon_old_mail()
        i_filesystem_watcher = filesystem_watcher(get_mailboxes(), notifier)

    def disable(self):
        self.set_icon_disabled()
        i_filesystem_watcher.stop()

    def set_icon_disabled(self):
        print("Disabled!")
        return
#        self.status_icon.

    def set_icon_old_mail(self):
        self.status_icon.set_from_pixbuf(read_icon_pixbuf)

    def set_icon_new_mail(self):
        self.status_icon.set_from_pixbuf(unread_icon_pixbuf)

def get_mailboxes():
    # Getting the path of all the mailboxes
    fd =  open(expanduser(mailbox_file), 'r')
    boxes = filter(lambda v: (re.search(ignore, v) == None),
            (b.rstrip().replace('+','').replace('"','')
                for b in re.sub("^\s?mailboxes\s", "", fd.readline()).split(' ')))
    fd.close()
    return boxes

class filesystem_watcher:
    def __init__(self, boxes, notifier):
        self.wm = pyinotify.WatchManager()
        self.inotifier = pyinotify.ThreadedNotifier(self.wm, notifier)
        self.inotifier.start()

        for box in boxes:
            self.wm.add_watch(maildir_folder+box+"/new", pyinotify.IN_CREATE | pyinotify.IN_MOVED_TO | pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM)

    def stop(self):
        self.inotifier.stop()

if __name__ == '__main__':
    i_tray_icon = tray_icon()
    notifier = desktop_notification(r'maildir-notify.py')
    i_filesystem_watcher = filesystem_watcher(get_mailboxes(), notifier)

    gtk.main()
