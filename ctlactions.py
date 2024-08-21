from ctl import *
import csv
import io

def teamsFromChannelID(db, channelID):
  teams = db.namedQueryParams("SELECT name FROM teams WHERE channelID = ?", ["name"], (str(channelID),))
  return teams

def addNewTeam(message, db, params):
  name = params[0]
  logs = ["Attempting to add team: {}".format(name)]
  teamData = (name, "[]", "[\"None\",\"None\",\"None\",\"None\",\"None\"]",  0)
  try:
    db.execParams("INSERT INTO teams(name," +
                                "roster," +
                                "lineup," +
                                "subsUsed)" +
                                " VALUES(?, ?, ?, ?);", teamData)
    logs.append("Successfully added team: {}".format(name))
  except:
    logs.append("Failed to add team {}".format(name))
  return {"returnValue":[], "logs":logs, "files":[]}

def deleteTeam(message, db, params):
  name = params[0]
  logs = ["Attempting to deleted team: {}".format(name)]
  try:
    db.execParams("DELETE FROM teams WHERE name = ?", (name,))
    logs.append("Successfully deleted team: {}".format(name))
  except:
    logs.append("Failed to delete team: {}".format(name))
  return {"returnValue":[], "logs":logs, "files":[]}

def addNewPlayer(message, db, params):
  name = params[0]

  logs = ["Attempting to add player: {}".format(name)]

  ### Figure out what team is adding a player
  teams = teamsFromChannelID(db, message.channel.id)
  if len(teams) > 1:
    logs.append("There are multiple teams with the channelID {}".format(message.channel.id))
    return {"returnValue":[], "logs":logs, "files":[]}
  elif len(teams) == 0:
    logs.append("There are no teams with the channelID {}".format(message.channel.id))
    return {"returnValue":[], "logs":logs, "files":[]}
  teamName = teams[0]["name"]

  ### Try to insert the player
  try:
    db.execParams("INSERT INTO players(discordUsername, teamName) VALUES (?, ?)", (name, teamName))
    logs.append("{} added to {}".format(name, teamName))
  except:
    logs.append("Failed to add {} to {}".format(name, teamName))

  ### Insert the player into the roster
  try:
    ### get the old roster
    teams = db.queryParams("SELECT roster FROM teams WHERE name = ?", (teamName,))
    roster = list(json.loads(teams[0][0]))
    if name not in roster:
      roster.append(name)
    newRoster = json.dumps(roster)
    db.execParams("UPDATE teams SET roster = ? WHERE name = ?", (newRoster, teamName))
  except:
    logs.append("Failed to insert {} into the {} roster".format(name, teamName))

  return {"returnValue":[], "logs":logs, "files":[]}

def deletePlayer(message, db, params):
  name = params[0]

  logs = ["Attempting to delete player: {}".format(name)]

  ### Figure out what team is adding a player
  teams = teamsFromChannelID(db, message.channel.id)
  if len(teams) > 1:
    logs.append("There are multiple teams with the channelID {}".format(message.channel.id))
    return {"returnValue":[], "logs":logs, "files":[]}
  elif len(teams) == 0:
    logs.append("There are no teams with the channelID {}".format(message.channel.id))
    return {"returnValue":[], "logs":logs, "files":[]}
  teamName = teams[0]["name"]

  ### check if the player is tagged to be deleted
  tag = db.namedQueryParams("SELECT taggedToDelete FROM players WHERE discordUsername = ? AND teamName = ?", ["taggedToDelete"], (name, teamName))[0]["taggedToDelete"]
  if(not tag == "Yes"):
    db.execParams("UPDATE players SET taggedToDelete = \"Yes\" WHERE discordUsername = ? AND teamName = ?", (name, teamName))
    logs.append("```diff\n-{} has been tagged to be deleted. Please run deletePlayer again to confirm.```".format(name))
    return {"returnValue":[], "logs":logs, "files":[]}

  ### Try to delete the player
  try:
    db.execParams("DELETE FROM players WHERE discordUsername = ? AND teamName = ?", (name, teamName))
    logs.append("{} deleted from {}".format(name, teamName))
  except:
    logs.append("Failed to delete {} from {}".format(name, teamName))

  ### Remove the player from the roster
  try:
    ### get the old roster
    teams = db.queryParams("SELECT roster FROM teams WHERE name = ?", (teamName,))
    roster = list(json.loads(teams[0][0]))
    if name in roster:
      roster.remove(name)
    newRoster = json.dumps(roster)
    db.execParams("UPDATE teams SET roster = ? WHERE name = ?", (newRoster, teamName))
  except:
    logs.append("Failed to delete {} from the {} roster".format(name, teamName))

  return {"returnValue":[], "logs":logs, "files":[]}

def editPlayer(message, db, params):
  discordUsername = params[0]
  displayName = params[1]
  battletag = params[2]
  sc2inGameName = params[3]
  sc2race = params[4]
  primaryRegion = params[5]
  teamLeader = params[6]
  nephestLink = params[7]

  logs = ["Trying to edit {}".format(discordUsername)]

  validTeamLeaderNames = ["Captain", "Assistant Captain", "None"]
  validRaces = ["Protoss", "Terran", "Zerg", "Random"]

  ### Figure out what team is adding a player
  teams = teamsFromChannelID(db, message.channel.id)
  if len(teams) > 1:
    logs.append("There are multiple teams with the channelID {}".format(message.channel.id))
    return {"returnValue":[], "logs":logs, "files":[]}
  elif len(teams) == 0:
    logs.append("There are no teams with the channelID {}".format(message.channel.id))
    return {"returnValue":[], "logs":logs, "files":[]}
  teamName = teams[0]["name"]

  originalPlayer = db.queryParams("SELECT * FROM players WHERE discordUsername = ? AND teamName = ?",
      (discordUsername, teamName))[0]
  # TODO: FIX THIS SHIT
  originalDisplayName = originalPlayer[2]
  originalBattleTag = originalPlayer[3]
  originalsc2InGameName = originalPlayer[4]
  originalsc2Race = originalPlayer[5]
  originalPrimaryRegion = originalPlayer[6]
  originalNephestLink = originalPlayer[7]
  originalTeamLeader = originalPlayer[9]

  if len(displayName.strip(" ")) == 0:
    displayName = originalDisplayName
  if len(battletag.strip(" ")) == 0:
    battletag = originalBattleTag
  if len(sc2inGameName.strip(" ")) == 0:
    sc2inGameName = originalsc2InGameName
  if len(sc2race.strip(" ")) == 0:
    sc2race = originalsc2Race
  if len(primaryRegion.strip(" ")) == 0:
    primaryRegion = originalPrimaryRegion
  if len(nephestLink.strip(" ")) == 0:
    nephestLink = originalNephestLink
  if len(teamLeader.strip(" ")) == 0:
    teamLeader = originalTeamLeader

  if teamLeader not in validTeamLeaderNames:
    logs.append("WARN: teamLeader value not recognized, reverting to {}.".format(originalTeamLeader))
    teamLeader = originalTeamLeader

  if sc2race not in validRaces:
    sc2race = originalsc2Race
    logs.append("WARN: sc2race value not recognized, reverting to {}.".format(originalsc2Race))

  try:
    values = {"displayName": displayName,
              "battletag": battletag,
              "sc2InGameName": sc2inGameName,
              "sc2race": sc2race,
              "primaryRegion": primaryRegion,
              "teamLeader": teamLeader,
              "nephestLink": nephestLink,
              "discordUsername": discordUsername,
              "teamName": teamName}
    db.execParams("UPDATE players SET "+
                  "displayName = :displayName,"+
                  "battletag = :battletag,"+
                  "sc2inGameName = :sc2InGameName,"+
                  "sc2race = :sc2race,"+
                  "primaryRegion = :primaryRegion,"+
                  "teamLeader = :teamLeader,"+
                  "nephestLink = :nephestLink WHERE discordUsername = :discordUsername and teamName = :teamName",
                  values)
    logs.append("{} updated Successfully".format(discordUsername))
  except:
    logs.append("Failed to update {}".format(discordUsername))

  return {"returnValue":[], "logs":logs, "files":[]}

def setTeamChannel(message, db, params):
  name = params[0]
  channelID = params[1]

  logs = ["Attempting to set the channel for team {} to {}".format(name, channelID)]

  try:
    db.execParams("UPDATE teams SET channelID = ? WHERE name = ?", (channelID, name))
    logs.append("Succeeded setting team {} channel to {}".format(name, channelID))
  except:
    logs.append("Failed to set team channel")
  return {"returnValue":[], "logs":logs, "files":[]}

def showTeams(message, db, params):
  logs = ["Trying to grab teams"]
  try:
    r = "```"
    teams = db.namedQuery("SELECT name, subsUsed FROM teams", ["name", "subsUsed"])
    r += "name\tsubsUsed\n".expandtabs(20)
    for team in teams:
      r += "{}\t{}\n".format(team["name"], team["subsUsed"]).expandtabs(20)
    r += "```"
    logs.append(r)
  except:
    logs.append("Could not grab teams")
  return {"returnValue":[], "logs":logs, "files":[]}

def showPlayers(message, db, params):
  logs = ["Trying to grab players"]
  try:
    players = db.query("SELECT * FROM players")
    header = ["discName", "team", "dispName", "battleTag", "inGame", "race", "region", "nephest", "teamLeader"]
    rows = []
    for player in players:
      row = []
      discordUsername = player[0]
      teamName = player[1]
      displayName = player[2]
      battleTag = player[3]
      sc2InGameName = player[4]
      sc2Race = player[5]
      primaryRegion = player[6]
      nephestLink = player[8]
      teamLeader = player[10]
      row.append(discordUsername)
      row.append(teamName)
      row.append(displayName)
      row.append(battleTag)
      row.append(sc2InGameName)
      row.append(sc2Race)
      row.append(primaryRegion)
      row.append(nephestLink)
      row.append(teamLeader)
      rows.append(row)

    buff = io.StringIO()
    writer = csv.writer(buff)
    writer.writerow(header)
    writer.writerows(rows)
    buff.seek(0)
    f = discord.File(buff, "ctl_players.csv")
    files = [f]
  except Exception as e:
    logs.append(str(e))
    logs.append("Could not grab players")
    files = []
  return {"returnValue":[], "logs":logs, "files":files}

def showPenalties(message, db, params):
  result = {"returnValue":[], "logs":[], "files":[]}
  result["logs"].append("Grabbing penalties")
  teams = db.namedQuery("SELECT name, week1LineupPenalty, matchReportPenalty, replayPenalty FROM teams",
                              ["name", "week1LineupPenalty", "matchReportPenalty", "replayPenalty"])


  for team in teams:
    name = team["name"]
    week1 = team["week1LineupPenalty"]
    matchReport = team["matchReportPenalty"]
    replay = team["replayPenalty"]

    r = "```{} has {} penalties from missing the week one lineup, ".format(name, week1) + \
      "{} penalties from match reports, and {} penalties from missing replays```".format(matchReport, replay)

    result["logs"].append(r)

  return result

def changePenalties(message, db, params):
  teamName = params[0]
  penaltyType = params[1]
  amount = int(params[2])
  result = {"returnValue":[], "logs":[], "files":[]}

  penaltyTypes = ["week1LineupPenalty", "matchReportPenalty", "replayPenalty"]

  if penaltyType not in penaltyTypes:
    result["logs"].append("Invalid penalty type!")
    return result

  oldPenalties = db.namedQueryParams("SELECT week1LineupPenalty, matchReportPenalty, replayPenalty FROM teams WHERE name = ?",
                                    penaltyTypes, (teamName,))

  newPenalties = {}
  for p in penaltyTypes:
    if p == penaltyType:
      newPenalties[p] = oldPenalties[0][p] + amount
    else:
      newPenalties[p] = oldPenalties[0][p]

  try:
    for p in penaltyTypes:
      db.execParams("UPDATE teams SET {} = ? WHERE name = ?".format(p), (newPenalties[p], teamName))
    result["logs"].append("Successfully updated penalties")
  except:
    result["logs"].append("Could not update penalties!")

  return result

def setLineup(message, db, params):
  newlineup = [params[0], params[1], params[2], params[3], params[4]]

  logs = ["Attempting to set lineup: {}".format(newlineup)]

  ### Figure out what team is setting the lineup
  teams = teamsFromChannelID(db, message.channel.id)
  if len(teams) > 1:
    logs.append("There are multiple teams with the channelID {}".format(message.channel.id))
    return {"returnValue":[], "logs":logs, "files":[]}
  elif len(teams) == 0:
    logs.append("There are no teams with the channelID {}".format(message.channel.id))
    return {"returnValue":[], "logs":logs, "files":[]}
  teamName = teams[0]["name"]

  ### Insert the player into the lineup
  try:
    teams = db.queryParams("SELECT lineup FROM teams WHERE name = ?", (teamName,))
    lineup = list(json.loads(teams[0][0]))
    teams = db.queryParams("SELECT roster FROM teams WHERE name = ?", (teamName,))
    roster = list(json.loads(teams[0][0]))

    def checkPlayer(x):
      p = newlineup[x]
      if p not in roster:
        return 1
      if p in newlineup[0:x]:
        return 2
      return 0

    for i in range(5):
      tmp = checkPlayer(i)
      if tmp == 1:
        logs.append("{} is not in this teams roster! Try again.".format(newlineup[i]))
        return {"returnValue":[], "logs":logs, "files":[]}
      elif tmp == 2:
        logs.append("{} is in the lineup more than once! Try again.".format(newlineup[i]))
        return {"returnValue":[], "logs":logs, "files":[]}
      elif tmp == 0:
        lineup[i] = newlineup[i]
    lineupJSON = json.dumps(lineup)
    db.execParams("UPDATE teams SET lineup = ? WHERE name = ?", (lineupJSON, teamName))
    logs.append("lineup set Successfully to: {}".format(newlineup))
  except:
    logs.append("Failed to set lineup to {} for team {}".format(newlineup, teamName))

  return {"returnValue":[], "logs":logs, "files":[]}

def newMap(message, db, params):
  name = params[0]

  logs = ["Attempting to add map: {}".format(name)]

  ### Try to insert the map
  try:
    db.execParams("INSERT INTO maps VALUES (?)", (name,))
    logs.append("{} added to the mappool".format(name))
  except:
    logs.append("Failed to add {} to the mappool".format(name))
  return {"returnValue":[], "logs":logs, "files":[]}

def deleteMap(message, db, params):
  name = params[0]

  logs = ["Attempting to delete map: {}".format(name)]
  ### Try to delete the player
  try:
    db.execParams("DELETE FROM maps WHERE name = ?", (name,))
    logs.append("{} deleted from mappool".format(name))
  except:
    logs.append("Failed to delete {} from mappool".format(name))
  return {"returnValue":[], "logs":logs, "files":[]}

def showMaps(message, db, params):
  result = {"returnValue":[], "logs":[], "files":[]}
  result["logs"].append("Grabbing mappool...")
  maps = db.namedQuery("SELECT name FROM maps",
                              ["name"])

  for m in maps:
    name = m["name"]
    r = "```{}```".format(name)
    result["logs"].append(r)

  return result

def startSession(message, db, params):
  result = {"returnValue":[], "logs":[], "files":[]}
  result["logs"].append("Starting Session...")

  ### build a new session
  content = "Emoji Session with {}".format(message.author.global_name)
  result["newSessions"] = [{"user":message.author, "message":None, "sessionType":"testSession", "content":content}]
  return result

def runTests(message, db, params):
  result = {"returnValue":[], "logs":[], "files":[]}

  result["logs"].append("Running tests...")

  result["logs"].append("Testing newTeam...")
  newParams = ["Test Team"]
  newResult = addNewTeam(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing setTeamChannel...")
  newParams = ["Test Team", str(message.channel.id)]
  newResult = setTeamChannel(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing newPlayer...")
  newParams = ["TestPlayer"]
  newResult = addNewPlayer(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing editPlayer...")
  newParams = ["TestPlayer", "TestPlayerDN", "TestBattleTag", "sc2name", "Zerg", "NA", "None", "www.google.com"]
  newResult = editPlayer(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing setLineup...")
  newParams = ["TestPlayer", "TestPlayer", "TestPlayer", "TestPlayer", "TestPlayer"]
  newResult = setLineup(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing setLineup with invalid player...")
  newParams = ["TestPlayer", "FakePlayer", "TestPlayer", "TestPlayer", "TestPlayer"]
  newResult = setLineup(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing showPlayers...")
  newParams = []
  newResult = showPlayers(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing showTeams...")
  newParams = []
  newResult = showTeams(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing changePenalties...")
  newParams = ["Test Team", "replayPenalty", 10]
  newResult = changePenalties(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing showPenalties...")
  newParams = []
  newResult = showPenalties(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing deletePlayer...")
  newParams = ["TestPlayer"]
  newResult = deletePlayer(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing deletePlayer...")
  newParams = ["TestPlayer"]
  newResult = deletePlayer(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing deleteTeam...")
  newParams = ["Test Team"]
  newResult = deleteTeam(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing newMap...")
  newParams = ["Test Map LE"]
  newResult = newMap(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing showMaps...")
  newParams = []
  newResult = showMaps(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])

  result["logs"].append("Testing deleteMap...")
  newParams = ["Test Map LE"]
  newResult = deleteMap(message, db, newParams)
  result["returnValue"].extend(newResult["returnValue"])
  result["logs"].extend(newResult["logs"])
  result["files"].extend(newResult["files"])


  return result