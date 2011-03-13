'''Reads config.conf and parses common values
for easy access by other modules'''
import ConfigParser
import sys
import re
import os

try:
    if '--local-config' in sys.argv:
        raise Exception('Use local config!')
    file = open(os.getenv('HOME') + '/.BBot/config.cfg', 'r')
    sys.path.insert(1, os.getenv('HOME') + '/.BBot')
    PATH = os.getenv('HOME') + '/.BBot/'
    print(' * Loaded config.cfg from your home directory')
except:
    if '--user-config' in sys.argv:
        raise Exception('Local config could not be read.')
    file = open('config.cfg', 'r')
    PATH = ''
    print(' * Loaded config.cfg out of local directory')

c = ConfigParser.ConfigParser()
c.readfp(file)

nick = c.get('main', 'nick')
username = c.get('main', 'username')
password = c.get('main', 'password')
network = c.get('main', 'network')
port = c.getint('main', 'port')
ssl = c.getboolean('main', 'ssl')
autojoin = c.get('main', 'channels').split()
modules = c.get('main', 'modules').split()
superusers = c.get('main', 'super-users').split()
sleep_after_id = c.getfloat('main', 'wait-after-identify')
wait_recv = c.getint('main', 'read-wait')
cmd_char = c.get('main', 'command-char')
ignore = re.compile(c.get('main', 'ignore-re'))

backend = c.get('main', 'backend')
