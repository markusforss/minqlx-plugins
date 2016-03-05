import minqlx
import time

class darude(minqlx.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("map", self.reference_soundpack)
        self.add_command("darude", self.cmd_darude, 5, usage="Darude.. do I need to say more?")
        self.set_cvar("qlx_darudeSoundDelay", "30")

        self.soundpack_id = "638403084"
        self.last_sound = None
        self.sound_path = "sound/darude/darude.ogg"

    def reference_soundpack(self, mapname, factory):
        # Download your sound pack from the workshop onto your player's computers when they first join.
        self.game.steamworks_items += [self.soundpack_id]

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
            #if self.db.get_flag(p, "essentials:sounds_enabled", default=True):
            super().play_sound(self.sound_path, p)
