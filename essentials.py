# minqlx - A Quake Live server administrator bot.
# Copyright (C) 2015 Mino <mino@minomino.org>

# This file is part of minqlx.

# minqlx is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# minqlx is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with minqlx. If not, see <http://www.gnu.org/licenses/>.

#Some essential functions.

import minqlx
import minqlx.database
import plugins
import datetime
import itertools
import time
import re

from collections import deque

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"

class essentials(minqlx.Plugin):
    database = minqlx.database.Redis

    def __init__(self):
        super().__init__()
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("vote_called", self.handle_vote_called)
        self.add_hook("command", self.handle_command, priority=minqlx.PRI_LOW)
        self.add_command("id", self.cmd_id, 1, usage="[part_of_name] ...")
        self.add_command(("commands", "cmds"), self.cmd_commands, 2)
        self.add_command("shuffle", self.cmd_shuffle, 1)
        self.add_command("slap", self.cmd_slap, 2, usage="<id> [damage]")
        self.add_command("slay", self.cmd_slay, 2, usage="<id>")
        self.add_command("sound", self.cmd_sound, 1, usage="<path>")
        self.add_command("music", self.cmd_music, 1, usage="<path>")
        self.add_command("kick", self.cmd_kick, 2, usage="<id>")
        self.add_command(("kickban", "tempban"), self.cmd_kickban, 2, usage="<id>")
        self.add_command("yes", self.cmd_yes, 2)
        self.add_command("no", self.cmd_no, 2)
        self.add_command("switch", self.cmd_switch, 1, usage="<id> <id>")
        self.add_command("red", self.cmd_red, 1, usage="<id>")
        self.add_command("blue", self.cmd_blue, 1, usage="<id>")
        self.add_command(("spectate", "spec", "spectator"), self.cmd_spectate, 1, usage="<id>")
        self.add_command("free", self.cmd_free, 1, usage="<id>")
        self.add_command("addmod", self.cmd_addmod, 5, usage="<id>")
        self.add_command("addadmin", self.cmd_addadmin, 5, usage="<id>")
        self.add_command("demote", self.cmd_demote, 5, usage="<id>")
        self.add_command("mute", self.cmd_mute, 1, usage="<id>")
        self.add_command("unmute", self.cmd_unmute, 1, usage="<id>")
        self.add_command("allready", self.cmd_allready, 2)
        self.add_command("abort", self.cmd_abort, 2)
        self.add_command(("map", "changemap"), self.cmd_map, 2, usage="<mapname> [factory]")
        self.add_command(("help", "about", "version"), self.cmd_help)
        self.add_command("db", self.cmd_db, 5, usage="<key> [value]")
        self.add_command("seen", self.cmd_seen, usage="<steam_id>")
        self.add_command("time", self.cmd_time, usage="[timezone_offset]")
        self.add_command(("teamsize", "ts"), self.cmd_teamsize, 2, usage="<size>")
        self.add_command("rcon", self.cmd_rcon, 5)

        # Vote counter. We use this to avoid automatically passing votes we shouldn't.
        self.vote_count = itertools.count()
        self.last_vote = 0

        # A short history of recently executed commands.
        self.recent_cmds = deque(maxlen=11)

    def handle_player_connect(self, player):
        self.update_player(player)

    def handle_player_disconnect(self, player):
        self.update_player(player)

    def handle_vote_called(self, caller, vote, args):
        config = self.config
        # Enforce teamsizes.
        if vote.lower() == "teamsize":
            try:
                args = int(args)
            except ValueError:
                return
            
            limits = self.teamsize_limits()
            if "max" in limits and args > limits["max"]:
                caller.tell("The team size is larger than what the server allows.")
                return minqlx.RET_STOP_ALL
            elif "min" in limits and args < limits["min"]:
                caller.tell("The team size is smaller than what the server allows.")
                return minqlx.RET_STOP_ALL

        if "Essentials" in config and "AutoPassMajorityVote" in config["Essentials"]:
            auto_pass = config["Essentials"].getboolean("AutoPassMajorityVote")
            if auto_pass:
                require = None
                if "AutoPassRequireParticipation" in config["Essentials"]:
                    require = float(config["Essentials"]["AutoPassRequireParticipation"])
                self.last_vote = next(self.vote_count)
                self.force(require, self.last_vote)

    def handle_command(self, caller, command, args):
        self.recent_cmds.appendleft((caller, command, args))

    def cmd_id(self, player, msg, channel):
        """What you'll usually call before a lot of the other commands.
        You give it parts of people's names and it replies with a list
        of players that matched it. It ignores colors.

        Ex.: ``!id min cool`` would list all players with those two
        tokens in their name. "Mino", "COOLLER" and "^5I A^2M MI^6NO"
        would all be possible candidates.

        You can always do /players in the console, but this can save you
        some time if you're only looking for a player or two, especially
        since it can be done from chat too.

        """
        def list_alternatives(players, indent=2):
            out = ""
            for p in players:
                out += " " * indent
                out += "{}^6:^7 {}\n".format(p.id, p.name)
            player.tell(out[:-1])
        
        player_list = self.players()
        if not player_list:
            player.tell("There are no players connected at the moment.")
        elif len(msg) == 1:
            player.tell("All connected players:")
            list_alternatives(player_list)
        else:
            players = []
            for name in msg[1:]:
                for p in self.find_player(name):
                    if p not in players:
                        players.append(p)
            if players:
                player.tell("A total of ^6{}^7 players matched:".format(len(players)))
                list_alternatives(players)
            else:
                player.tell("Sorry, but no players matched your tokens.")

        # We reply directly to the player, so no need to let the event pass.
        return minqlx.RET_STOP_EVENT

    def cmd_commands(self, player, msg, channel):
        if len(self.recent_cmds) == 1:
            player.tell("No commands have been recorded yet.")
        else:
            player.tell("The most recent ^6{}^7 commands executed:".format(len(self.recent_cmds) - 1))
            for cmd in list(self.recent_cmds)[1:]:
                player.tell("  {} executed: {}".format(cmd[0].name, cmd[2]))

        return minqlx.RET_STOP_EVENT

    def cmd_shuffle(self, player, msg, channel):
        """Forces a shuffle instantly."""
        self.shuffle()

    def cmd_slap(self, player, msg, channel):
        """Slaps a player with optional damage."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            player.tell("Invalid ID.")
            return minqlx.RET_STOP_EVENT

        if len(msg) > 2:
            try:
                dmg = int(msg[2])
            except ValueError:
                player.tell("Invalid damage value.")
                return minqlx.RET_STOP_EVENT
        else:
            dmg = 0
        
        self.slap(target_player, dmg)
        return minqlx.RET_STOP_EVENT

    def cmd_slay(self, player, msg, channel):
        """Kills a player instantly."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            player.tell("Invalid ID.")
            return minqlx.RET_STOP_EVENT
        
        self.slay(target_player)
        return minqlx.RET_STOP_EVENT

    def cmd_sound(self, player, msg, channel):
        """Plays a sound for the whole server."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        if not self.play_sound(msg[1]):
            player.tell("Invalid sound.")
            return minqlx.RET_STOP_EVENT

    def cmd_music(self, player, msg, channel):
        """Plays music for the whole server, but only for those with music volume on."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        if not self.play_sound(msg[1]):
            player.tell("Invalid music.")
            return minqlx.RET_STOP_EVENT

    def cmd_kick(self, player, msg, channel):
        """Kicks a player. A reason can also be provided."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return
        
        if len(msg) > 2:
            target_player.kick(" ".join(msg[2:]))
        else:
            target_player.kick()

    def cmd_kickban(self, player, msg, channel):
        """Kicks a player and prevent the player from joining for the remainder of the map."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

            target_player.tempban()

    def cmd_yes(self, player, msg, channel):
        """Passes the current vote."""
        if self.is_vote_active():
            self.force_vote(True)
        else:
            channel.reply("There is no active vote!")

    def cmd_no(self, player, msg, channel):
        """Vetoes the current vote."""
        if self.is_vote_active():
            self.force_vote(False)
        else:
            channel.reply("There is no active vote!")

    def cmd_switch(self, player, msg, channel):
        """Switches the teams of the two players."""
        if len(msg) < 3:
            return minqlx.RET_USAGE

        try:
            i1 = int(msg[1])
            player1 = self.player(i1)
            if not (i1 >= 0 and i1 < 64) or not player1:
                raise ValueError
        except ValueError:
            channel.reply("The first ID is invalid.")
            return

        try:
            i2 = int(msg[2])
            player2 = self.player(i2)
            if not (i2 >= 0 and i2 < 64) or not player2:
                raise ValueError
        except ValueError:
            channel.reply("The second ID is invalid.")
            return

        self.switch(player1, player2)
            
    def cmd_red(self, player, msg, channel):
        """Moves a player to the red team."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        target_player.put("red")

    def cmd_blue(self, player, msg, channel):
        """Moves a player to the blue team."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        target_player.put("blue")


    def cmd_spectate(self, player, msg, channel):
        """Moves a player to the spectator team."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        target_player.put("spectator")

    def cmd_free(self, player, msg, channel):
        """Moves a player to the free team."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        target_player.put("free")

    def cmd_addmod(self, player, msg, channel):
        """Give a player mod status."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        target_player.addmod()

    def cmd_addadmin(self, player, msg, channel):
        """Give a player admin status."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        target_player.addadmin()

    def cmd_demote(self, player, msg, channel):
        """Remove admin status from someone."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        target_player.demote()

    def cmd_mute(self, player, msg, channel):
        """Mute a player."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        if target_player == player:
            channel.reply("I refuse.")
        else:
            target_player.mute()

    def cmd_unmute(self, player, msg, channel):
        """Mute a player."""
        if len(msg) < 2:
            return minqlx.RET_USAGE

        try:
            i = int(msg[1])
            target_player = self.player(i)
            if not (i >= 0 and i < 64) or not target_player:
                raise ValueError
        except ValueError:
            channel.reply("Invalid ID.")
            return

        target_player.unmute()
    
    def cmd_allready(self, player, msg, channel):
        """Forces all players to ready up."""
        if self.game.state == "warmup":
            self.allready()
        else:
            channel.reply("But the game's already in progress, you silly goose!")
        
    def cmd_abort(self, player, msg, channel):
        """Forces a game in progress to go back to warmup."""
        if self.game.state != "warmup":
            self.abort()
        else:
            channel.reply("But the game isn't even on, you doofus!")
    
    def cmd_map(self, player, msg, channel):
        """Changes the map."""
        if len(msg) < 2:
            return minqlx.RET_USAGE
        
        # TODO: Give feedback on !map.
        self.change_map(msg[1], msg[2] if len(msg) > 2 else None)
        
    def cmd_help(self, player, msg, channel):
        # TODO: Perhaps print some essential commands in !help
        player.tell("minqlx: ^6{}^7 - Plugins: ^6v{}".format(minqlx.__version__, plugins.__version__))
        player.tell("See ^6github.com/MinoMino/minqlx^7 for more info about the mod and its commands.")
        return minqlx.RET_STOP_EVENT
    
    def cmd_db(self, player, msg, channel):
        """Prints the value of a key in the database."""
        if len(msg) < 2:
            return minqlx.RET_USAGE
        
        try:
            if msg[1] not in self.db:
                channel.reply("The key is not present in the database.")
            else:
                t = self.db.type(msg[1])
                if t == "string":
                    out = self.db[msg[1]]
                elif t == "list":
                    out = str(self.db.lrange(msg[1], 0, -1))
                elif t == "set":
                    out = str(self.db.smembers(msg[1]))
                elif t == "zset":
                    out = str(self.db.zrange(msg[1], 0, -1, withscores=True))
                else:
                    out = str(self.db.hgetall(msg[1]))
                
                channel.reply(out)
        except Exception as e:
            channel.reply("^1{}^7: {}".format(e.__class__.__name__, e))
            raise

    def cmd_seen(self, player, msg, channel):
        """Responds with the last time a player was seen on the server."""
        if len(msg) < 2:
            return minqlx.RET_USAGE
        # TODO: Save a couple of nicknames in DB and have !seen work with nicks too?

        try:
            steam_id = int(msg[1])
            if steam_id < 64:
                channel.reply("Invalid SteamID64.")
                return
        except ValueError:
            channel.reply("Unintelligible SteamID64.")
            return
        
        p = self.player(steam_id)
        if p:
            channel.reply("That would be {}^7, who is currently on this very server!".format(p))
            return
        
        key = "minqlx:players:{}:last_seen".format(steam_id)
        name = "that player" if steam_id != minqlx.owner() else "my ^6master^7"
        if key in self.db:
            then = datetime.datetime.strptime(self.db[key], DATETIME_FORMAT)
            td = datetime.datetime.now() - then
            r = re.match(r'((?P<d>.*) days*, )?(?P<h>..?):(?P<m>..?):.+', str(td))
            if r.group("d"):
                channel.reply("^7I saw {} ^6{}^7 day(s), ^6{}^7 hour(s) and ^6{}^7 minute(s) ago."
                    .format(name, r.group("d"), r.group("h"), r.group("m")))
            else:
                channel.reply("^7I saw {} ^6{}^7 hour(s) and ^6{}^7 minute(s) ago."
                    .format(name, r.group("h"), r.group("m")))
        else:
            channel.reply("^7I have never seen {} before.".format(name))

    def cmd_time(self, player, msg, channel):
        """Responds with the current time."""
        tz_offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
        tz_offset = tz_offset // 60 // 60 * -1
        if len(msg) > 1:
            try:
                tz_offset = int(msg[1])
            except ValueError:
                channel.reply("Unintelligible time zone offset.")
                return
        tz = datetime.timezone(offset=datetime.timedelta(hours=tz_offset))
        now = datetime.datetime.now(tz)
        if tz_offset > 0:
            channel.reply("The current time is: ^6{} UTC+{}"
                .format(now.strftime(TIME_FORMAT), tz_offset))
        elif tz_offset < 0:
            channel.reply("The current time is: ^6{} UTC{}"
                .format(now.strftime(TIME_FORMAT), tz_offset))
        else:
            channel.reply("The current time is: ^6{} UTC"
                .format(now.strftime(TIME_FORMAT)))

    def cmd_teamsize(self, player, msg, channel):
        """Calls a teamsize vote and passes it immediately."""
        if len(msg) < 2:
            return minqlx.RET_USAGE
        
        try:
            n = int(msg[1])
        except ValueError:
            channel.reply("^7Unintelligible size.")
            return
        
        self.game.teamsize = n
        self.msg("The teamsize has been set to ^6{}^7 by {}.".format(n, player))
        return minqlx.RET_STOP_EVENT

    def cmd_rcon(self, player, msg, channel):
        """Sends an rcon command to the server."""
        if len(msg) < 2:
            return minqlx.RET_USAGE
        # TODO: Maybe hack up something to redirect the output of !rcon?
        minqlx.console_command(" ".join(msg[1:]))

    # ====================================================================
    #                               HELPERS
    # ====================================================================

    def update_player(self, player):
        """Updates the 'last_seen' entry in the database.

        """
        base_key = "minqlx:players:" + str(player.steam_id)
        db = self.db.pipeline()
        # The simplicity here is the reason why Redis is perfect for this.
        if base_key not in self.db:
            db.lpush(base_key, player.name)
            db.sadd("minqlx:players", player.steam_id)
        else:
            names = [self.clean_text(n) for n in self.db.lrange(base_key, 0, -1)]
            if player.clean_name not in names:
                db.lpush(base_key, player.name)
                db.ltrim(base_key, 0, 19)
        
        now = datetime.datetime.now().strftime(DATETIME_FORMAT)
        db.set(base_key + ":last_seen", now)
        db.execute()
        
    @minqlx.delay(29)
    def force(self, require, vote_id):
        if self.last_vote != vote_id:
            # This is not the vote we should be resolving.
            return

        votes = self.current_vote_count()
        if self.is_vote_active() and votes and votes[0] > votes[1]:
            if require:
                teams = self.teams()
                players = teams["red"] + teams["blue"] + teams["free"]
                if sum(votes)/len(players) < require:
                    return
            minqlx.force_vote(True)

    def teamsize_limits(self):
        res = {}
        conf = self.config
        if "Essentials" in conf and "MaximumTeamsize" in conf["Essentials"]:
            res["max"] = int(conf["Essentials"]["MaximumTeamsize"])

        if "Essentials" in conf and "MinimumTeamsize" in conf["Essentials"]:
            res["min"] = int(conf["Essentials"]["MinimumTeamsize"])

        return res