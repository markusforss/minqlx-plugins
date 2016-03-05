import minqlx
import requests
import threading

class temperature(minqlx.Plugin):
    def __init__(self):
        super().__init__()
        self.add_command("temp", self.cmd_temperature, 5, usage="Just temperature")

    @minqlx.thread
    def cmd_temperature(self, player, msg, channel):
        r = requests.get('http://orly.fi/~markusforss/current.txt')
        channel.reply(r.text)
