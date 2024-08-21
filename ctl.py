import sqlite3
import os
import json
import discord
import io
from datetime import datetime
from pytz import timezone
import pytz
import pandas as pd

def log(msg: str):
  print("#CTLBOT: {}".format(msg))

class ActionRequest:
  '''
  Encapsulates a request from the user
  '''
  def __init__(self):
    self.name = ""
    self.params = []
    self.log = []
    self.files = []
    self.author = None

class MessageParser:
  '''
  Constructs an ActionRequest from a discord message
  '''
  def __init__(self, prefix):
    self.prefix = prefix

  def parse(self, message):
    ar = ActionRequest()
    if message.content.startswith(self.prefix):
      s = message.content.split(" ")
      ### commands at least need !prefix action, also accept !prefix action paramscsv
      if(len(s) < 2):
        ar.log.append("Bad command: {}".format(message.content))
        return ar

      ar.name = s[1]

      ### get params if they exist
      if(len(s) >= 3):
        paramsMerged = " ".join(s[2:])
        ar.params = paramsMerged.split(",")

    ar.author = message.author

    return ar

class dbAction:
  '''
  Wrapper of functions that implement bot commands.
  Meant to be injected into the DiscordManager's dbActions list
  '''
  def __init__(self, name, call, paramNames, roles, channels=[]):
    self.name = name
    self.call = call
    self.paramNames = paramNames
    self.roles = roles
    self.returnValue = None
    self.log = []
    self.files = []
    self.sessions = []
    self.channels = channels

  def checkRequest(self, ar):
    '''
    Check if a request matches this dbAction
    '''

    '''
    Check role permison
    '''

    allowed = False
    if len(self.roles) == 0:
      allowed = True
    else:
      for role in ar.author.roles:
        if role.name in self.roles:
          allowed = True
    if not allowed:
      return False

    '''
    check function signature
    '''
    if(ar.name == self.name and len(self.paramNames) == len(ar.params)):
      return True
    return False

  def execute(self, message, db, params):
    resultDict = self.call(message, db, params)
    self.returnValue = resultDict["returnValue"]
    self.log.extend(resultDict["logs"])
    self.files.extend(resultDict["files"])
    if "newSessions" in resultDict:
      self.sessions.extend(resultDict["newSessions"])

  def generateHelp(self):

    roleString = ""
    if len(self.roles) > 0:
      roleString = "- Allowed Roles["
      for role in self.roles:
        roleString += "{},".format(role)
      roleString = roleString[0:-1]
      roleString += "]\n"
    channelString = ""
    if len(self.channels) > 0:
      channelString = "+ Allowed Channels["
      for channel in self.channels:
        channelString += "{},".format(channel)
      channelString = channelString[0:-1]
      channelString += "]\n"
    result = "```diff\n\n{}{}syntax for {}\n".format(roleString, channelString, self.name) +\
              "{} ".format(self.name)
    for pname in self.paramNames:
      result += "<{}>,".format(pname)
    ### remove trailing comma
    if result[-1] == ",":
      result = result[0:-1]
    result += "\n```"
    return result

class DiscordManager(discord.Client):

  def __init__(self, intents, prefix, tables):
    super().__init__(intents=intents)
    ### setup the parser
    self.parser = MessageParser(prefix)
    
    ### list of injected actions
    self.dbActions = []

    ### database object
    self.db = CTLDB(tables)

    ### for duplicating messages
    self.dupesDict = {}

    ### tracking dialogue tree sessions
    self.sessions = {}

    ### load in schedule and setup the state of the league
    leagueStateFrame = pd.read_csv("./leagueState.csv")
    scheduleFrame = pd.read_csv("./schedule.csv")
    self.leagueState = {"week":0}

  def sessionStep(self, session, reaction):
    r = "{} reacted with {}".format(session["user"].global_name, str(reaction.emoji))
    return r

  def tryDuplicating(self, message):
    sourceTargetPairs = {}
    '''message duplication'''
    if message.channel.id in self.dupesDict:
      destination = self.dupesDict[message.channel.id]
      targetChannel = self.get_channel(destination)
      sourceTargetPairs[message.channel] = targetChannel
    return sourceTargetPairs

  def tryHelp(self, message):
    '''Print help for each available dbAction'''
    response = ""
    if message.content.startswith("!ctlbot help"):
      response += "The current CTL time (Pacific) is: {}\n".format(getCTLTime().strftime("%m/%d/%Y %H:%M:%S %Z"))
      for act in self.dbActions:
        response += act.generateHelp()
    return response

  async def on_ready(self):
    log("Logged in as {}".format(self.user))

  async def on_message(self, message):
    ### dont process messages from the bot
    if message.author.id == self.user.id:
      return

    ### message duplication
    sourceTargetPairs = self.tryDuplicating(message)
    for source, target in sourceTargetPairs.items():
      await target.send("{}: {}".format(message.author.name, message.content))
    if(len(sourceTargetPairs.keys()) > 0):
      return

    ### general help message
    helpResponse = self.tryHelp(message)
    if len(helpResponse) > 0:
      await message.channel.send(helpResponse)
      return

    ar = self.parser.parse(message)

    for act in self.dbActions:
      if act.checkRequest(ar):

        ### Check if this is in an allowed channel
        allowedChannel = False
        if "Team Channel" in act.channels:
          ### check if this is a team channel
          teams = self.db.namedQuery("SELECT channelID FROM teams", ["channelID"])
          for team in teams:
            if str(team["channelID"]) == str(message.channel.id):
              allowedChannel = True
        if len(act.channels) == 0:
          allowedChannel = True

        if allowedChannel:
          act.execute(message, self.db, ar.params)
          ar.log.extend(act.log)
          ar.files.extend(act.files)
          ### clear logs and files for the future
          act.log = []
          act.files = []

          ### plug in new sessions
          if len(act.sessions) > 0:
            for session in act.sessions:
              msg = await message.channel.send(session["content"])
              self.sessions[(session["user"].id, msg.id)] = ({"user":session["user"], "sessionType":session["sessionType"], "message":msg, "content":session["content"]})
            ### clean up for later
            act.sessions = []

    ### log locally and on discord
    for a in ar.log:
      log(a)
    if len(ar.log) > 0:
      await message.channel.send(msgCleaner(str("\n".join(ar.log))))

    ### are there files to send?
    if len(ar.files) > 0:
      for f in ar.files:
        await message.channel.send(file = f)

  ### handling question tree sessions
  async def on_reaction_add(self, reaction, user):
    if (user.id, reaction.message.id) in self.sessions:
      newContent = self.sessionStep(self.sessions[(user.id, reaction.message.id)], reaction)
      await reaction.message.edit(content = newContent)
      await reaction.message.clear_reactions()

  def shutdown(self):
    self.db.conn.close()


class DBTable:
  '''
  Wrapper for a db table
  '''
  def __init__(self, tableName, columnNames, columnParams, primaryKeys):
    self.tableName = tableName
    self.columnNames = columnNames
    self.columnParams = columnParams
    self.primaryKeys = primaryKeys

class CTLDB:
  '''
  Wrapper for a SQLite3 db
  '''
  def __init__(self, tables):

    self.tables = tables

    dbExists = os.path.exists("./ctl.db")
    self.conn = sqlite3.connect("ctl.db")
    if not dbExists:
      log("DB not found, creating it")
      self.initializeDB()
    log("Database initialized")

  def exec(self, cmd: str):
    self.conn.execute(cmd)
    self.conn.commit()

  def execParams(self, cmd: str, params):
    self.conn.execute(cmd, params)
    self.conn.commit()

  def query(self, cmd: str):
    res = self.conn.execute(cmd).fetchall()
    self.conn.commit()
    return res

  def queryParams(self, cmd: str, params):
    res = self.conn.execute(cmd, params).fetchall()
    self.conn.commit()
    return res

  def namedQuery(self, cmd, names):
    res = self.conn.execute(cmd).fetchall()
    self.conn.commit()

    namedRes = []
    for r in res:
      nr = {}
      for i in range(len(r)):
        nr[names[i]] = r[i]
      namedRes.append(nr)

    return namedRes

  def namedQueryParams(self, cmd, names, params):
    res = self.conn.execute(cmd, params).fetchall()
    self.conn.commit()

    namedRes = []
    for r in res:
      nr = {}
      for i in range(len(r)):
        nr[names[i]] = r[i]
      namedRes.append(nr)

    return namedRes

  def createTable(self, table):
    log("Creating table {}".format(table.tableName))
    commandString = "CREATE TABLE {} (".format(table.tableName)
    for cname in table.columnNames:
      params = ""
      if cname in table.columnParams:
        params = table.columnParams[cname]
      if len(params) > 0:
        commandString += "{} {}, ".format(cname, params)
      else:
        commandString += "{}, ".format(cname)
    ### remove traling comma and whitespace
    if commandString[-1] == " ":
      commandString = commandString[0:-1]
    if commandString[-1] == ",":
      commandString = commandString[0:-1]

    ### setup primary keys
    if len(table.primaryKeys) > 0:
      commandString += ", PRIMARY KEY ("
      for pk in table.primaryKeys:
        commandString += "{}, ".format(pk)
      ### remove traling comma and whitespace
      if commandString[-1] == " ":
        commandString = commandString[0:-1]
      if commandString[-1] == ",":
        commandString = commandString[0:-1]
      commandString += "));"
    else:
      commandString += ");"
    log("Table creation string: {}".format(commandString))
    self.exec(commandString)

  def initializeDB(self):
    for table in self.tables:
      self.createTable(table)

def msgCleaner(msg: str):

  badFormatters = []
  if len(msg) > 5000:
    msg = msg[0:5000]

  newMSG = ""
  for c in msg:
    if c in badFormatters:
      newMSG += "Z"
    else:
      newMSG += c
  return newMSG

def getCTLTime():
  date = datetime.now(tz=pytz.utc)
  date = date.astimezone(timezone("US/Pacific"))
  return date