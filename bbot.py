#! /usr/bin/python
#this bot is licensed under the GNU GPL v3.0
#http://www.gnu.org/licenses/gpl.html
version='1.7'
proxyscan=1#Scan for open proxies on join? 1=yes,0=no. Requires nmap and python-namp: http://nmap.org  http://xael.org/norman/python/python-nmap/
globals=[]

config=open('config','r')
cline=config.readline()
mynick=cline.split('nick: ')[-1][0:-1]
cline=config.readline()
username=cline.split('username: ')[-1][0:-1]
cline=config.readline()
password=cline.split('password: ')[-1][0:-1]
cline=config.readline()
network=cline.split('network: ')[-1][0:-1]
cline=config.readline()
port=int(cline.split('port: ')[-1].strip())
print('Connecting to: %s' % network)

cline=config.readline()
autojoin=cline.split('channels: ')[-1].split(' ')
cline=config.readline()
superusers=cline.split('super-user: ')[-1].split(' ')

cline=config.readline()
sleep_after_join=float(cline.split('wait-after-identify: ')[-1].strip())
cline=config.readline()
wait_recv=int(cline[cline.find(' '):].strip('\r\n'))
cline=config.readline()
cmd_char=cline[cline.find(' '):].strip('\r\n')
config.close()
del config
del cline

import socket
import sys
import re
import time
#import sqlite3
from random import randint
import thread

import blockbotlib #some functions required for BlockBot(). Delete this like if you remove BlockBot()
import api #BBot API Functions
sys.path.append('%s/modules'%sys.path[0])
#from folderbot import *

class queue_class():
	def __init__(self):
		self.queue=[]
	def get_length(self):
		return len(self.queue)
	def append(self,data):
		self.queue.append('PRIVMSG '+data[0]+' :'+data[1])
	def pop(self):
		return self.queue.pop(0)
	def join(self, channel):
		self.queue.append('JOIN '+channel)
	def part(self, channel, message=''):
		self.queue.append('PART %s :%s'%(channel,message))
	def kick(self,nick,channel,message=''):
		self.queue.append('KICK %s %s :%s!'%(channel,nick,message))
	def nick(self,nick):
		self.queue.append('NICK %s'%nick)
		mynick=nick[:]
	def notice(self,data):
		self.queue.append('NOTICE '+data[0]+' :'+data[1])
	def mode(self,nick,channel,mode):
		self.queue.append('MODE '+channel+' '+mode+' '+nick)
	def kill(self,nick,reason=''):#Must be IRCOP
		self.queue.append('KILL %s :%s' % (nick,reason))
	def kline(self,host,time='3600',reason='K-Lined'):#Must be IRCOP
		self.queue.append('KLINE %s %s :%s'%(host,str(time),reason))
	def raw(self,data):
		self.queue.append(data)
queue=queue_class()	
class BBot():
	def __init__(self):
		self.read_dict()
		self.q=''
	#database=sqlite3.connect('newdatabase.sql')
	def go(self,nick,data,channel):
		if channel.find('#')==-1:#Detect if the message is a PM to the Bot
			channel=nick.lower()
		ldata=data.lower()
		if api.checkIfSuperUser(data,superusers):
			if ldata.find('raw ')!=-1:
				queue.raw(data.split('raw ')[-1])
			elif ldata.find('leave')!=-1:
				words=ldata.split('leave ')
				irc.send('PART %s' % words)
			elif ldata.find('?add ')!=-1:
				self.q=ldata[ldata.find('?add ')+5:].strip('\r\n')
				self.q=self.q.split(':::')
				self.add_factoid(self.q)
			elif ldata.find('?writedict')!=-1:
				self.write_dict()
		if ldata.find(':'+mynick.lower()+': ')!=-1:
			self.q=ldata[ldata.find(':'+mynick.lower()+': ')+3+len(mynick):].strip('\r\n')
			print self.q
			if self.q in self.static:
				queue.append((channel,self.static[self.q]))
		if data.find(':?')!=-1:
			print 'q: %s'%self.q
			self.q=data[data.find(':?')+2:].strip('\r\n')
			if self.q in self.static:
				queue.append((channel,nick+': '+self.static[self.q]))
			elif data.find(':?hit ')!=-1:
				words=data.split(':?hit ')[-1].strip('\r\n')
				if words.lower().find(mynick.lower())!=-1 or words.lower()=='aj00200':
					words=nick
				queue.append((channel,u'\x01ACTION kicks %s\x01'%words))
	def add_factoid(self,query):
		self.static[query[0]]=query[1]
	def del_factoid(self,query):
		if quey in self.static:
			del elf.static[query]
	def write_dict(self):
		self.dict=open('bbot/dict','w')
		for each in self.static:
			self.dict.write('%s:::%s\n'%(each,self.static[each]))
		self.dict.close()
	def read_dict(self):
		self.static={}
		self.dict=open('bbot/dict','r')
		for line in self.dict.readlines():
			self.q=line.split(':::')
			self.static[self.q[0]]=self.q[1]
		self.dict.close()
class BlockBot():
	def __init__(self):
		self.ignore_users_on_su_list=1#Don't kick users if they are on the superusers list
		self.jlist={}
		self.config=open('blockbot-config','r')
		self.findlist=self.config.readline().split('spam-strings: ')[1].split('#')[0].split('^^^@@@^^^')
		self.proxyscan=0
		if self.config.readline().lower().split('#')[0].find('yes')!=-1:
			self.proxyscan=1
			proxyscan=1
		if self.proxyscan==1:
			import nmap #Can be found at: http://xael.org/norman/python/python-nmap/
		self.line=self.config.readline()
		self.wait=float(self.line.split('-speed: ')[-1].split(' #')[0])
		self.config.close()
		self.repeatlimit=3
		self.repeat_time=2
		self.repeat_1word=4
		self.msglist=[]
		self.lastnot=('BBot',time.time(),'sdkljfls')
	def join(self,nick,channel,ip,user):
		#webchat=(str(blockbotlib.hex2dec('0x'+str(user[1:3])))+'.'+str(blockbotlib.hex2dec('0x'+str(user[3:5])))+'.'+str(blockbotlib.hex2dec('0x'+str(user[5:7])))+'.'+str(blockbotlib.hex2dec('0x'+str(user[7:9]))))
		if channel[1:] not in self.jlist:
			self.jlist[channel[1:]]=[]
		self.jlist[channel[1:]].append(nick)
		if proxyscan:
			thread.start_new_thread(self.scan, (ip,channel,nick))
	def scan(self,ip,channel,nick):
		self.scansafe=1
		try:
			print('Scanning '+ip)
			self.nm=nmap.PortScanner()
			#80, 8080, 1080, 3246
			self.nm.scan(ip,'808,23,1080,110,29505,8080,3246','-T5')
			for each in nm.all_hosts():
				print each+':::'
				lport = nm[each]['tcp'].keys()
				print lport
				if 808 in lport or 23 in lport or 110 in lport or 1080 in lport or 29505 in lport or 80 in lport or 8080 in lports or 3246 in lports:
					self.scansafe=0
					print 'DRONE'
			del self.nm
			if self.scansafe:
				queue.mode(nick,channel,'+v')
		except:
			print 'PYTHON NMAP CRASH'
	def go(self,nick,data,channel):
		self.ldata=data.lower()
		if self.ignore_users_on_su_list:
			self.superuser=api.checkIfSuperUser(data,superusers)
		if self.superuser:
			if self.ldata.find(':?;')!=-1:
				self.findlist.append(data.split(':?; ')[-1][0:-2])
			elif self.ldata.find(':?faster')!=-1:
				print 'FASTER'
				self.wait=self.wait/2
			elif self.ldata.find(':?slower')!=-1:
				print('SLOWER')
				self.wait=self.wait*2
			elif self.ldata.find(':?setspeed ')!=-1:
				self.wait=float(data.split('?setspeed ')[-1][0:-2])
			elif self.ldata.find(':?rehash')!=-1:
				self.__init__()
			elif self.ldata.find(':?ekill')!=-1:
				irc.send('QUIT')
				continuepgm=0
			elif self.ldata.find(':?protect')!=-1:
				queue.mode('',channel,'+mz')
			elif self.ldata.find(':?kl')!=-1:
				if self.ldata.find('?kl ')!=-1:
					self.t=self.ldata.split('?kl ')[-1][0:-2]
					self.t=int(self.t)
					try:
						for each in range(t):
							queue.kick(self.jlist[channel[1:]].pop(),channel)
					except:
						queue.append((nick,'Kicking that many people has caused an error!'))
		elif not self.superuser:
			self.checkforspam(nick,data,channel)
	def checkforspam(self,nick,data,channel):
		self.msglist.insert(0,(nick,time.time(),data))
		if len(self.msglist)>5:
			self.msglist.pop()
		ident=data.split(' PRIVMSG ')[0].split('@')[0][1:]
		ldata=data.lower()
		msg=ldata[ldata.find(' :')+2:]
		for each in self.findlist:
			if re.search(each,ldata):
				queue.kick(nick,channel)
		try:
			if self.msglist[0][0]==self.msglist[1][0]==self.msglist[2][0]:
				if (self.msglist[0][1]-self.msglist[2][1])<self.wait:
					queue.kick(nick,channel,'No Flooding!')
				if msg.split()>1:
					if (self.msglist[0][2]==self.msglist[1][2]==self.msglist[2][2]) and (self.msglist[0][1]-self.msglist[1][1]<self.repeat_time):
						queue.kick(nick,channel,'Please do not repeat!')
		except IndexError:
			pass
	def notice(self,nick,channel,data):
		ldata=data.lower()
		self.olastnot=(self.lastnot[0:])
		self.lastnot=(nick,time.time())
		if self.olastnot[0]==self.lastnot[0]:
			if (self.lastnot[1]-self.olastnot[1])<self.wait:
				queue.kick(nick,channel,'Please do not use the notice command so much')
		for each in self.findlist:
			if ldata.find(each)!=-1:
				queue.kick(nick,channel)
class trekbot():
	def __init__(self):
		self.blacklist=[]
		self.blconfig=open('trekbot/blacklist','r').readlines()
		for each in self.blconfig:
			self.blacklist.append(each.strip('\r\n'))
		self.whitelist=[]
		self.wlconfig=open('trekbot/whitelist','r').readlines()
		for each in self.wlconfig:
			self.whitelist.append(each.strip('\r\n'))
		del self.blconfig,self.wlconfig
	def go(self,nick,data,channel):
		ldata=data.lower()
		self.superuser=api.checkIfSuperUser(data,superusers)
		if self.superuser:
			if ldata.find(':?op')!=-1:
				if ldata.find('?op ')!=-1:
					nick=ldata[ldata.find('?op')+4:].strip('\r\n')
				queue.mode(nick,channel,'+o')
			if ldata.find(':?deop')!=-1:
				if ldata.find('?deop ')!=-1:
					nick=ldata[ldata.find('?deop ')+6:].strip('\r\n')
				queue.mode(nick,channel,'-o')
			elif ldata.find(':?voice')!=-1:
				if ldata.find('?voice ')!=-1:
					nick=ldata[ldata.find('?voice ')+7:].strip('\r\n')
				queue.mode(nick,channel,'+v')
			elif ldata.find(':?devoice')!=-1:
				if ldata.find('?devoice ')!=-1:
					nick=ldata[ldata.find('?devoice ')+9:].strip('\r\n')
				queue.mode(nick,channel,'-v')
			elif ldata.find(':?kick ')!=-1:
				name=ldata[ldata.find('?kick ')+6:].strip('\r\n')
				queue.kick(name,channel,'Requested by %s'%nick)
			elif ldata.find('?rehash')!=-1:
				self.__init__()
			#Blacklist
			elif ldata.find(':?blacklist ')!=-1:
				name=data[data.find('?blacklist ')+11:].strip('\r\n')
				if not name in self.blacklist:
					self.blacklist.append(name)
					self.write_blacklist()
			elif ldata.find(':?unblacklist ')!=-1:
				name=data[data.find('?unblacklist ')+13:].strip('\r\n')
				if name in self.blacklist:
					self.blacklist.pop(self.blacklist.index(name))
					self.write_blacklist()
				else:
					queue.append((nick,'That host is not blacklisted'))
			elif ldata.find(':?listbl')!=-1:
				queue.append((nick,str(self.blacklist)))
			#Whitelist
			elif ldata.find(':?whitelist ')!=-1:
				name=data[data.find('?whitelist ')+11:].strip('\r\n')
				if not name in self.whitelist:
					self.whitelist.append(name)
					self.write_blacklist()
			elif ldata.find(':?unwhitelistlist ')!=-1:
				name=data[data.find('?unwhitelist ')+13:].strip('\r\n')
				if name in self.blacklist:
					self.whitelist.pop(self.blacklist.index(name))
					self.write_whitelist()
				else:
					queue.append((nick,'That host is not whitelisted'))
			elif ldata.find(':?listbl')!=-1:
				queue.append((nick,str(self.blacklist)))
			elif ldata.find(':?mode ')!=-1:
				queue.mode('',channel,ldata[ldata.find('?mode ')+6:])
			elif data.find(':?echo ')!=-1:
				queue.append((channel,data[ldata.find('?echo ')+6:]))
			elif ldata.find(':?ban ')!=-1:
				queue.mode(data[data.find('?ban ')+5:],channel,'+b')
			elif ldata.find(':?unban ')!=-1:
				queue.mode(data[data.find('?unban ')+7:],channel,'-b')
			elif data.find(':?topic ')!=-1:
				queue.raw('TOPIC %s :%s'%(channel,data[data.find('?topic ')+7:]))
			elif data.find(':?nick ')!=-1:
				queue.nick(data[data.find('?nick ')+6:])
	def write_blacklist(self):
		self.blconfig=open('trekbot/blacklist','w')
		for each in self.blacklist:
			self.blconfig.write(each+'\n')
	def write_whitelist(self):
		self.wlconfig=open('trekbot/whitelist','w')
		for each in self.whitelist:
			self.wlconfig.write(each+'\n')
	def join(self,nick,channel,ip,user):
		if not ip in self.blacklist:
			if not ip in self.whitelist:
				bb.scan(ip,channel,nick)
			else:
				queue.mode(nick,channel,'+v')
		else:
			queue.kick(nick,channel,'Your on the blacklist, please message a channel op about getting removed from the list')
class statusbot():
	def __init__(self):
		self.statuses={}
	def go(self,nick,data,channel):
		if data.find(':?status ')!=-1:
			words=data.split('?status')[-1].strip('\r\n')
			self.statuses[nick]=words[:]
		elif data.find(':?whereis ')!=-1:
			try:
				words=data.split(':?whereis ')[-1].strip('\r\n')
				queue.append((channel,nick+': %s is: '%words+self.statuses[words]))
			except:
				queue.append((channel,nick+': %s hasn\'t left a status.'%words))
		elif data.find('?notify ')!=-1:
			words=data.split(':?notify ')[-1].strip('\r\n').strip('#')
			if words.find(' '):
				queue.append((nick,'Please don\'t abuse me. This is logged!'))
			else:
				queue.append((words,'Just letting you know, %s is looking for you in %s' % (nick,channel)))
		elif data.find(':?reset')!=-1:
			words=data.split(':?reset')[-1].strip('\r\n')
			try:
				del self.statuses[words]
			except:
				pass
class searchbot():
	def __init__(self):
		self.goog='http://www.google.com/search?q=%s'
		self.wiki='http://www.en.wikipedia.org/wiki/%s'
		self.pb='http://www.pastebin.com/%s'
		self.upb='http://paste.ubuntu.com/%s'
	def go(self,nick,data,channel):
		if data.find(':?goog ')!=-1:
			w=data.split(':?goog ')[-1].replace(' ','+')
			queue.append((channel,self.goog%w))
		elif data.find(':?wiki ')!=-1:
			w=data.split(':?wiki ')[-1].replace(' ','+')
			queue.append((channel,self.wiki%w))
		elif data.find(':?pb ')!=-1:
			w=data.split(':?pb ')[-1]
			queue.append((channel,self.pb%w))
		elif data.find(':?upb ')!=-1:
			w=data.split(':?upb ')[-1]
			queue.append((channel,self.upb%w))
class WhoBot():
	def go(self,nick,data,channel):
		if nick.lower()=='evilbikcmp' or nick.lower()=='mithos' or nick.lower()=='aj00200':
			if data.find('?kline ')!=-1:
				nick=data[data.find('?kline ')+7:]
				print nick
				irc.send('WHOIS %s'%nick)
	def code(self,code,data):
		if code=='311':
			self.data=data.split(mynick)[-1].split()
			self.h=self.data[2]
			print 'HOST %s'%self.h
			if self.h.find('webchat/')!=-1:
				self.ident='!'.join(self.data[1:2])
				print 'IDENT: %s'%self.ident
				queue.append(('operserv','AKILL ADD !T 6400 %s@%s Spam is offtopic on FOSSnet. Email kline@fossnet.info for help'%(self.ident,self.h)))
			else:
				queue.append(('operserv','AKILL ADD !T 6400 *!*@'+self.h+' Spam is offtopic on FOSSnet. Email kline@fossnet.info for help.'))
class mathbot():
	def __init__(self):
		import math
		self.allow={
			')':'..0..',
			'sqrt(':'..1..',
			'pow(':'..2..',
			'ceil(':'..3..',
			'floor(':'..4..',
			'log(':'..5..',
			'asin(':'..6..',
			'acos(':'..7..',
			'atan(':'..8..',
			'atan2(':'..9..',
			'sin(':'..10..',
			'cos(':'..11..',
			'tan(':'..12..'
			}
		self.invert={
			'..0..':')',
			'..1..':'math.sqrt(',
			'..2..':'math.pow(',
			'..3..':'math.ceil(',
			'..4..':'math.floor(',
			'..5..':'math.log(',
			'..6..':'math.asin(',
			'..7..':'math.acos(',
			'..8..':'math.atan(',
			'..9..':'math.atan2(',
			'..10..':'math.sin(',
			'..11..':'math.cos(',
			'..12..':'math.tan('
			}
	def go(self,nick,data,channel):
		self.ldata=data.lower()
		if self.ldata.find('?math help')!=-1:
			queue.append((channel,nick+' : +, -, *, /, %, sqrt, pow, ceil, floor, log, asin, acos, atan, atan2, sin, cos, tan'))
		elif self.ldata.find('?math ')!=-1:
			self.e=self.ldata[self.ldata.find('?math ')+6:].strip('\r\n')
			self.e=self.e.replace('pi','3.1415926535897931')
			for each in self.allow:
				self.e=self.e.replace(each,self.allow[each])
			self.e=self.e.strip('abcdefghijklmnopqrstubwxyz#@$')
			for each in self.invert:
				self.e=self.e.replace(each,self.invert[each])
			self.e=self.e.replace('//','.0/')
			try:
				queue.append((channel,str(eval(self.e))))
			except Exception,e:
				self.e='Error: %s; with arguments %s'%(type(e),e.args)
				queue.append((channel,self.e))
#===============HANDLERS=====
bb=BlockBot()
tb=trekbot()
wb=WhoBot()
handlers=[bb,BBot(),statusbot(),searchbot(),tb,wb,mathbot()]#Run on msg
jhandlers=[tb,bb]#Run on Join
lhandlers=[]#Run every loop
nhandlers=[bb]
codes=[wb]
continuepgm=1
def PONG(data):
	if data.find ('PING')!=-1:
		irc.send('PONG '+data.split()[ 1 ]+'\r\n') #Return the PING to the server
		print('PONGING')
irc=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
irc.connect((network,port))
print 'NICK'
irc.send('NICK %s\r\n'%mynick)
irc.send ('USER '+mynick+' '+mynick+' '+mynick+' :'+mynick+'\r\n')
needping=1
while needping:
	data=irc.recv(1024)
	if data.find('PING')!=-1:
		PONG(data)
		print 'IDENTIFY'
		irc.send('PRIVMSG NickServ :IDENTIFY '+username+' '+password+'\r\n')
		needping=0
		print(data)
time.sleep(sleep_after_join)
print('JOIN')
for each in autojoin:
	irc.send('JOIN '+each+'\r\n')
while continuepgm:
	data = irc.recv (wait_recv)
	print(data)
	PONG(data)
	if data.find('INVITE '+mynick+' :#')!=-1:
		newchannel=data.split(mynick+' :')[-1]
		irc.send('JOIN '+newchannel+'\r\n')
		del newchannel
	elif re.search(':*!*NOTICE #*:',data):
		nick=data[1:data.find('!')]
		channel=data[data.find(' NOTICE ')+8:data.find(':')]
		words=data[data.find('NOTICE')+6:]
		words=words[words.find(':'):]
		for handler in nhandlers:
			handler.notice(nick,channel,words)
	elif data.find(' PRIVMSG ')!=-1:
		channel=data.split(' PRIVMSG ')[1]
		channel=channel.split(' :')[0]
		nick=data.split('!')[0][1:]
		for handler in handlers:
			handler.go(nick,data,channel)
	elif data.find(' JOIN :#')!=-1:
		nick=data.split('!')[0][1:]
		if nick.find('#')==-1:
			channel='#'+data.split(' :#')[-1][0:-2]
			ip=data.split('@')[1].split(' JOIN')[0]
			user=data.split('@')[0].split('!')[-1]
			for jhandler in jhandlers:
				jhandler.join(nick,channel,ip,user)
	elif re.search('[0-9]+ '+mynick,data):
		code=data.split()[1]
		for each in codes:
			each.code(code,data)
	if data.strip('\r\n')=='':
		continuepgm=0
	for handler in lhandlers:
		handler.loop()
	if queue.get_length():
		send=queue.pop()
		print(send)
		irc.send(send+'\r\n')
irc.send('QUIT :Quit: BBot Rulez\r\n')
