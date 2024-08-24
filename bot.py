import sys
from ctl import *
from ctlactions import *
from constants import *
import csv
import io

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

'''
Setup DB table structure
'''
maps = DBTable("maps",
                    ["name"],
                    {"name":"NOT NULL"},
                    ["name"])

players = DBTable("players",
                  PLAYERS_FIELDS,
                  {"discordUsername":"NOT NULL", "teamName":"NOT NULL"},
                  ["discordUsername", "teamName"])
teams = DBTable("teams",
                ["name", "roster", "lineup", "subsLeft", "week1LineupPenalty", "matchReportPenalty", "replayPenalty", "channelID"],
                {"name":"NOT NULL",
                "subsLeft":"INTEGER DEFAULT 0 NOT NULL",
                "week1LineupPenalty":"INTEGER DEFAULT 0 NOT NULL",
                "matchReportPenalty":"INTEGER DEFAULT 0 NOT NULL",
                "replayPenalty":"INTEGER DEFAULT 0 NOT NULL",},
                ["name"])

matches = DBTable("teamMatches",
                      ["week", "teamA", "teamB", "status",
                       "setScoreA", "setScoreB",
                       "mapScoreA", "mapScoreB",
                       "lineupAStatus", "lineupBStatus",
                       "map1", "map2", "map3", "map4", "map5",
                       "lineupA", "lineupB", "scoreAReportA","scoreAReportB", "scoreBReportA", "scoreBReportB", "mapReportA", "mapReportB"],
                       {"teamA":"NOT NULL", "teamB":"NOT NULL", "week":"INTEGER DEFAULT 0 NOT NULL",
                       "setScoreA":"INTEGER DEFAULT 0 NOT NULL", "setScoreB":"INTEGER DEFAULT 0 NOT NULL",
                       "mapScoreA":"INTEGER DEFAULT 0 NOT NULL", "setScoreB":"INTEGER DEFAULT 0 NOT NULL"},
                       ["week", "teamA", "teamB"])

tables = [maps, players, teams, matches]


dm = DiscordManager(intents = intents, prefix = "!ctlbot", tables = tables)

### setup channels for duping:
dm.dupesDict[1243885793978618018] = 1243885805962002463

### Players
dm.dbActions.append(dbAction(name = "newTeam", call = addNewTeam, paramNames = {"teamName"}, roles = ["Admins"]))
dm.dbActions.append(dbAction(name = "deleteTeam", call = deleteTeam, paramNames = {"teamName"}, roles = ["Admins"]))
dm.dbActions.append(dbAction(name = "newPlayer", call = addNewPlayer, paramNames=["playerDiscordUsername"], roles = [], channels = ["Team Channel"]))
dm.dbActions.append(dbAction(name = "deletePlayer", call = deletePlayer, paramNames = ["playerName"], roles = [], channels = ["Team Channel"]))
dm.dbActions.append(dbAction(name = "editPlayer", call = editPlayer, paramNames = EDIT_PLAYER_FIELDS, roles = [], channels = ["Team Channel"]))

### Teams
dm.dbActions.append(dbAction(name = "setTeamChannel", call = setTeamChannel, paramNames = ["teamName", "channelID"], roles = ["Admins"]))
dm.dbActions.append(dbAction(name = "showTeams", call = showTeams, paramNames = [], roles = []))
dm.dbActions.append(dbAction(name = "showPenalties", call = showPenalties, paramNames = [], roles = []))
dm.dbActions.append(dbAction(name = "changePenalties", call = changePenalties, paramNames = ["teamName", "penaltyType", "amount"], roles = ["Admins"]))
dm.dbActions.append(dbAction(name = "showPlayers", call = showPlayers, paramNames = [], roles = []))
dm.dbActions.append(dbAction(name = "setLineup", call = setLineup, paramNames = ["set1", "set2", "set3", "set4", "set5"], roles = [], channels = ["Team Channel"]))

### Maps
dm.dbActions.append(dbAction(name = "newMap", call = newMap, paramNames = ["mapName"], roles = ["Admins"]))
dm.dbActions.append(dbAction(name = "deleteMap", call = deleteMap, paramNames = ["mapName"], roles = ["Admins"]))
dm.dbActions.append(dbAction(name = "showMaps", call = showMaps, paramNames = [], roles = []))

### Matches
# dm.dbActions.append(dbAction(name = "updateScheduleFile", call = updateSchedule, paramNames = [], roles = ["Admins"]))
# dm.dbActions.append(dbAction(name = "getScheduleFile", call = updateSchedule, paramNames = [], roles = ["Admins"]))
# dm.dbActions.append(dbAction(name = "showSchedule", call = showSchedule, paramNames = [], roles = []))
# dm.dbActions.append(dbAction(name = "reportMatch", call = showSchedule, paramNames = [], roles = [], channels = ["Team Channel"]))

### Match Reporting

### Testing
dm.dbActions.append(dbAction(name = "runTests", call = runTests, paramNames = [], roles = ["Admins"]))
dm.dbActions.append(dbAction(name = "startSession", call = startSession, paramNames = [], roles = ["Admins"]))

### launch the bot
token = os.environ["ctltoken"]
dm.run(token)
dm.shutdown()