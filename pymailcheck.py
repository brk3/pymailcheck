# Copyright (C) 2010 Paul Bourke <pauldbourke@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# $Id: pymailcheck.py 5 2010-07-30 09:35:28Z bourke $

# TODO:
# - better icon size code

try:
  import pygtk
  import pynotify
  import gtk
  import gobject
  import egg.trayicon
except ImportError as e:
  print e
  exit(1)

import subprocess
import re
import os
import ConfigParser

class TrayIcon:
    def __init__(self):
      self.icon = os.path.abspath(os.path.join(os.path.curdir, 
          'mail-notification_22x22.xpm'))
      self.icon_size = (25, 22)
      self.mail_count = 0
      self.drawing_area = gtk.DrawingArea()
      self.window = egg.trayicon.TrayIcon(Pymailcheck.progname)
      self.pangolayout = self.drawing_area.create_pango_layout('')

      self.drawing_area.connect('expose-event', self._expose_cb)
      self.drawing_area.set_size_request(self.icon_size[0], self.icon_size[1])
      self.window.add(self.drawing_area)
      self.drawing_area.show()
      self.window.show()

    def _expose_cb(self, event, area):
      self.style = self.drawing_area.get_style()
      self.gc = self.style.fg_gc[gtk.STATE_NORMAL]
      self._draw_pixmap(self.mail_count)
      return True

    def _draw_pixmap(self, num):
      pixmap, mask = gtk.gdk.pixmap_create_from_xpm(
          self.drawing_area.window, self.style.bg[gtk.STATE_NORMAL], self.icon)
      self.drawing_area.window.draw_drawable(self.gc, pixmap, 0, 0, 0, 0,
                                     -1, -1)
      self.pangolayout.set_text(str(num))
      self.drawing_area.window.draw_layout(self.gc, (self.icon_size[0]/2)-5, 
          (self.icon_size[1]/2)-5, self.pangolayout)

class Config:
  def __init__(self):
    """ Inits a Config object and sets rc location to $HOME/prognamerc. """
    self.filename = os.path.join(os.environ['HOME'], 
        '.'+Pymailcheck.progname+'rc')

  def load_config(self):
    cp = ConfigParser.SafeConfigParser()
    ret = cp.read(self.filename)   
    assert len(ret) > 0, \
        self.filename + ' is empty or non existent.\n \
        See README for examples on creating one.'
    return cp

class Pymailcheck:
  progname = 'pymailcheck'

  def __init__(self):
    try:
      self.config = Config().load_config() 
    except (ConfigParser.ParsingError, AssertionError), e:
      print e
      exit(1)
    try:
      self.maildir = self.config.get('preferences', 'maildir')
      self.interval = int(self.config.get('preferences', 'interval'))
    except ConfigParser.NoOptionError as e:
      print e
      exit(1)
    except ValueError as e:
      print 'Invalid option specified in config file:'
      print e
      exit(1)
    self.tc = TrayIcon()
    self.last_check = 0
    self._timer_cb()
    gobject.timeout_add(self.interval*1000, self._timer_cb)
    gtk.main()

  def _timer_cb(self):
    new_mail = self._check_mail()
    new_mail_count = len(new_mail)
    if (new_mail_count > 0):
      self.tc.window.show()
      self.tc.mail_count = new_mail_count
      brand_new = new_mail_count - self.last_check
      if ((brand_new > 0) and (new_mail_count > self.last_check)):
        for i in range(self.last_check, len(new_mail)):
          n = pynotify.Notification('New Mail',
              'From: ' + new_mail[i][0] + '\n' + 
              'Subject: ' + new_mail[i][1],
               os.path.abspath(os.path.join(os.curdir,
                   'mail-notification_32x32.xpm')))
          n.show()
      self.last_check = new_mail_count
    else:
      self.tc.window.hide()
      self.tc.mail_count = 0
      self.last_check = 0
      self.should_notify = True
    self.tc.window.queue_draw()
    return True

  def _check_mail(self):
    maildir = os.path.join(self.maildir, 'new')
    new_mail = list()

    for f in os.listdir(maildir):
      full_path = os.path.join(maildir, f)

      if os.path.isfile(full_path):
        with open(full_path, 'r') as current_mail: 
          pattern_from = re.compile('From: \\"(?P<from>.+)\\"')
          pattern_subject = re.compile('Subject: (?P<subject>.+)')
          from_field = ''
          subject_field = ''
          line = current_mail.readline()

          while line:
            m1 = re.search(pattern_from, line)
            m2 = re.search(pattern_subject, line) 
            if m1 is not None:
              from_field = m1.group('from') 
            if m2 is not None:
              subject_field = m2.group('subject')
            if from_field != '' and subject_field != '':
              new_mail.append((from_field,subject_field))
              break
            line = current_mail.readline()
          assert from_field != '' and subject_field != '', \
              'something went wrong parsing details from ' \
              + full_path

    return new_mail

def main():
    Pymailcheck()

if __name__ == '__main__':
    main()
