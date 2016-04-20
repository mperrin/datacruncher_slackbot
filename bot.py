import configparser
import time
import threading
from threading import Thread
import re
import os

from slackclient import SlackClient
from slacker import Slacker

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


    

# Read in configuration from config.ini
# Note that config.ini should never be versioned on git!!!
config = configparser.ConfigParser()
config.read("config.ini")
username = config['DEFAULT']['username']
token = config['DEFAULT']['token']
uid = config['DEFAULT']['id']
dropboxdir = os.path.normpath(config['DEFAULT']['dropboxdir'])

class NewImagePoster(FileSystemEventHandler):
    """
    Thread that posts new PSF subtracted images to the Slack Chat
    """
    def __init__(self, dropboxdir, slacker_bot):
        """
        Runs on creation
        
        Args:
            dropboxdir: full path to dropboxdir to scan
            slacker_bot: a Slacker instance
        """
        self.dropboxdir = dropboxdir
        self.newfiles = []
        self.lock = threading.Lock()
        self.slacker = slacker_bot
    
    def process_file(self):
        with self.lock:
            if len(self.newfiles) == 0:
                return
            
            filepath = self.newfiles.pop(0)
            print(self.slacker.chat.post_message('@jwang', 'Beep. Boop. {0}'.format(filepath), username=username, as_user=True).raw)
        return
    
    
    def process_new_file_event(self, event):
        """
        Handles what events when a new file / file gets modified:
        
        Args:
            event: file system event
        """
        filepath = event.src_path
        print(filepath)
        
        # we are looking for the first PSF subtraction that happens
        if "_Pol" in filepath:
            matches = re.findall(r".*m1-(ADI-)?KLmodes-all\.fits", filepath)
        else:    
            matches = re.findall(r".*m1-KLmodes-all\.fits", filepath)
        # not a PSF subtraction
        if len(matches) <= 0:
            return
            
        # add item to queue
        with self.lock:
            if filepath not in self.newfiles:
                print("appending {0}".format(filepath))
                self.newfiles.append(filepath)

        # wait 3 seconds before processing
        threading.Timer(3., self.process_file).start() 
        
        
    def on_created(self, event):
        """
        watchdog function to run when a new file appears
        """
        self.process_new_file_event(event)

        
    def on_modifed(self, event):
        """
        watchdog function to run when an existing file is modified
        """
        self.process_new_file_event(event)
    

class ChatResponder(Thread):
    def __init__(self, slack_bot):
        """
        Init
        
        Args:
            slack_bot: a SlackClient instance
        """
        super(ChatResponder, self).__init__()
        self.slack_client = slack_bot

    def run(self):
        connected = self.slack_client.rtm_connect()
        if connected:
            while True:
                events = self.slack_client.rtm_read()
                for event in events:
                    self.parse_event(event)
                        
                time.sleep(1)
        else:
            print("Connection Failed, invalid token?")
    
    def get_klipped_img_info(self, request):
        """
        Get the info for a Klipped image that was requested
        
        Args:
            request: a string in the form of "Object Name[, Date[, Band[, Mode]]]"
            
        Returns:
            filename: the full path to the klipped image
            objname: object name (with spaces)
            date: with dashes
            mode: obsmode
        """
        raise NotImplementedError


    def craft_response(self, msg, sender, channel):
        """
        Given some input text from someone, craft this a response
        
        Args:
            msg: some text someone sent to the data cruncher
            sender: ID of sender
            channel: ID of channel
            
        Return:
            
        """
        if msg is None:
            return
            
        msg = msg.strip()
        if (msg.upper()[:4] == "SHOW") | (msg.upper()[:7] == "SHOW ME"):
            # Someone wants us to show them something!!
            reply = 'I received your text of "{0}"!'.format(msg)
            full_reply = '<@{user}>: '.format(user=sender) + reply
            print(sc.api_call("chat.postMessage", channel=channel, text=full_reply, username=username, as_user=True))
            
            
    def parse_txt(self, msg):
        """
        Parse text someone sent to the Data Cruncher

        Args:
            msg: a string that is the text body
            
        Return:
            parsed: parsed text of some sort
        """
        # clear white space
        msg = msg.strip()

        # see if it's addressed to you
        if not "<@{id}>".format(id=uid) == msg[:12]:
            return None
            
        # strip off @data_cruncher:
        body = msg[12:] # strip off @data_cruncher
        if body[0] == ":":
            body = body[1:] # strip off : too
        
        parsed = body
        
        return parsed
        
    def parse_event(self, event):
        """
        Parse an event received from Slack
        
        Args:
            event: a dictionary with key/value pairs. Standardized Slack input
        """
        # how do I do what event it is without a type
        if "type" not in event:
            return
        # look for chat messages
        if (event["type"] == "message") & ("text" in event):
            print(event)
            # grab message info
            try:
                msg = event["text"]
                sender = event["user"]
                channel = event["channel"]
            except KeyError as e:
                print("Got a malformed message packet", e)
                return
            
            print("From {0}@{1}: {2}".format(sender, channel, msg))
            msg_parsed = self.parse_txt(msg)
            self.craft_response(msg_parsed, sender, channel)



# client = SlackClient(token)
# print(client.api_call(
#     "chat.postMessage", channel="@jwang", text="Beep. Boop.",
#     username=username, as_user=True))
    
    
# using Slacker as it's file upload interface is much better
client = Slacker(token)
print(client.chat.post_message('@jwang', 'Beep. Boop', username=username, as_user=True).raw)
# print(client.files.upload('tmp.png', channels="@jwang",filename="HD_95086_160229_H_Spec.png", title="HD 95086 2016-02-29 H-Spec" ).raw)



# Run real time PSF subtraction updater
print(dropboxdir)
event_handler = NewImagePoster(dropboxdir, client)
observer = Observer()

observer.schedule(event_handler, dropboxdir, recursive=True)
observer.start()



    
# Run real time message slack client 
sc = SlackClient(token)

p = ChatResponder(sc)
p.daemon = True

p.start()
while True:
    time.sleep(100)
