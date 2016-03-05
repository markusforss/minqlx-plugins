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

import minqlx

class fun(minqlx.Plugin):
    def __init__(self):
        super().__init__()
        self.add_command("darude", self.cmd_darude, 2, usage="Darude.. do I need to say more?")
        self.set_cvar_once("qlx_darudeSoundDelay", "3")

    def cmd_darude(self, player, msg, channel):
        channel.reply("Darude fuck yeah!")
        self.play_sound()

    def play_sound(self):
        if not self.last_sound:
            pass
        elif time.time() - self.last_sound < self.get_cvar("qlx_darudeSoundDelay", int):
            return

        self.last_sound = time.time()
        for p in self.players():
            if self.db.get_flag(p, "essentials:sounds_enabled", default=True):
                super().play_sound("sound/darude.ogg", p)
