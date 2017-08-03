import oracle
import time
import threading
import UpdTime
import datetime
import urllib.request
import urllib
import shutil
import gzip
import xml.etree.ElementTree as ET


# Delphi Command Interpreter for Oracle2
#
# Oracle is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Oracle is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Oracle.  If not, see <http://www.gnu.org/licenses/>.


class Delphi:

    # define command keyword for each respective command
    cmd_time = 't'  # get time (region)
    cmd_mode = 'm'  # set mode ('major' or 'minor')
    cmd_review = 'r'  # review last time
    cmd_offset = 'o'  # set offset (region h:m:s)
    cmd_calibrate = 'c'  # calibrate (region h:m:s)

    cmd_export = 'export'
    cmd_targets = 'targets'
    cmd_html = 'html'
    cmd_reload = 'reload'

    cmd_start = 'start'
    cmd_stop = 'stop'

    def __init__(self, regions, ua, debug=False):
        """
        Provides interactive Oracle functionality. This can be used to create bots and user interfaces.

        :param regions: Path to NationStates regional data dump. Can be a string or file object.
        :param ua: User agent string that identifies the operator, as required by NS TOS
        :return:
        """

        self.debug = debug
        self.regions = regions

        self.ua = ua
        self.oracle = oracle.Oracle(regions, ua)

        self.time_now = datetime.datetime.utcnow().replace(tzinfo=UpdTime.UTC())
        self.time_base = datetime.datetime.utcnow().replace(tzinfo=UpdTime.UTC(), hour=0, minute=0, second=0,
                                                            microsecond=0)

        # determine start time of closest update
        # 16h = minor
        # 4h = major
        # easy: anything less than 16h is major (we don't really care about weird exception cases anyhow)

        if self.time_now < self.time_base + datetime.timedelta(hours=16):
            self.mode = "major"
        else:
            self.mode = "minor"

        self.tracking = False
        self.target = None

        self.runner = threading.Thread(target=self._runner, daemon=True)
        self.runner.start()

        self.log = []

    def parse(self, command):
        """
        Parses a command string and returns a text string with a human readable response. Handles any exceptions and
        informs the user gracefully. Command strings can be set by modifying the Delphi class.

        :param command: user input string, formatted as "command arguments"
        :return: user-readable response string
        """

        if self.log != []:
            print("Queued debug messages:")
            for _ in self.log:
                print(_)
            self.log = []
            print("\n")

        action = command.split(" ")[0]
        args = command.split(" ")[1:]
        try:
            # mode (major, minor)
            if action == self.cmd_mode:
                if args[0] == 'major' or args[0] == 'minor':
                    self.mode = args[0]
                    return "Mode set to {}.".format(self.mode)
                else:
                    return "ERROR: No such update '{}'.".format(args[0])

            # time (region name)
            elif action == self.cmd_time:
                self.target = ' '.join(args)
                try:
                    time = self.oracle.get_time_hms(self.target, self.mode)
                    return "Time predicted for {}: {:02d}:{:02d}:{:02d}.\n" \
                           "URL: http://nationstates.net/region={}".format(self.target, time[0], time[1], time[2],
                                                                           self.target.replace(" ", "_"))
                except KeyError:
                    return "ERROR: No such region {}".format(self.target)

            # recall last prediction
            elif action == self.cmd_review:
                if self.target != "":

                    time = self.oracle.get_time_hms(self.target, self.mode)
                    return "Time predicted for {}: {:02d}:{:02d}:{:02d}.\n" \
                           "URL: http://nationstates.net/region={}".format(self.target, time[0], time[1], time[2],
                                                                           self.target.replace(" ", "_"))
                else:
                    return "ERROR: No previous region to recall."

            # offset (time)
            elif action == self.cmd_offset:
                # time will be last text blob
                t = args[0].split(':')
                time = []
                try:
                    for i in t:
                        time.append(int(i))
                    tSec = time[0] * 3600 + time[1] * 60 + time[2]
                except ValueError:
                    return "ERROR: Invalid time provided."
                # all other text blobs are part of region name
                region = ' '.join(args[:-1])

                try:
                    self.oracle.set_offset(self.target, tSec, self.mode)
                    return "Offset adjusted to {} seconds.".format(-self.oracle.offset)
                except KeyError:
                    return "ERROR: No such region {}.".format(region)

            elif action == self.cmd_export:
                self.oracle.csv_export(self.mode, args[0])
                return "Exported CSV to {}".format(args[0])
            elif action == self.cmd_targets:
                self.oracle.founderless_export(self.mode, args[0])
                return "Exported founderless regions to {}".format(args[0])
            elif action == self.cmd_html:
                self.oracle.html_export(self.mode, args[0])
                return "Exported HTML to {}".format(args[0])
            elif action == self.cmd_start:
                self.tracking = True
                return "Tracking set to True"
            elif action == self.cmd_stop:
                self.tracking = False
                return "Tracking set to False."
            elif action == "dbg": # this is for troubleshooting use only
                self.debug = not self.debug
                return "!!!! Debug flag toggled."

            else:

                return """                {} <region> - get region time
                {} <major|minor> - set update mode to major or minor
                {} - recall last targeted  region
                {} <hh:mm:ss> - indicate true update time in hh:mm:ss of last targeted region
                {} <filename> - export CSV of oracle data using current update mode
                {} <filename> - export CSV of oracle data for founderless regions using current update mode
                {} <filename> - export HTML of oracle data using current update mode
                """.format(self.cmd_time, self.cmd_mode, self.cmd_review, self.cmd_offset,
                           self.cmd_export, self.cmd_targets, self.cmd_html, self.cmd_start,
                           self.cmd_stop)

        except IndexError:
            return "ERROR: malformed command."

    @staticmethod
    def find_between(s, first, last):
        try:
            start = s.index(first) + len(first)
            end = s.index(last, start)
            return s[start:end]
        except ValueError:
            return ""

    def query(self):
        """
        Queries the NationStates API for events which may reveal the current progress of the update.

        :return: Array [region_name, observed_update_time] or None if no event was observed.
        """
        headers = {u'User-Agent': self.ua}
        feed_url = u"https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=change;"
        query = urllib.request.Request(feed_url, headers=headers)
        xml = ET.fromstring(urllib.request.urlopen(query).read())

        for event in xml.iter(u'EVENT'):
            time = int(event.find(u"TIMESTAMP").text)
            event_text = event.find(u"TEXT").text
            if u"influence" in event_text or u"ranked" in event_text:
                nation = event_text.split("@@")[1]
                region_url = u"https://www.nationstates.net/cgi-bin/api.cgi?nation={}&q=region".format(nation)
                region_query = urllib.request.Request(region_url, headers=headers)
                region_xml = ET.fromstring(urllib.request.urlopen(region_query).read())
                region = region_xml.find(u"REGION").text

                # calculate how long after the update start the event was observed
                if self.mode is "minor":
                    time -= UpdTime.UpdTime.timestamp(self.time_base + datetime.timedelta(hours=16))
                else:
                    time -= UpdTime.UpdTime.timestamp(self.time_base + datetime.timedelta(hours=4))

                if self.debug is True:
                    self.log.append("HIT: {} updated {} sec in".format(region, time))
                    self.log.append("API Query: {}").format(region_url.replace(" ", "_"))

                return [region, time]
        return None

    def _runner(self):
        while True:
            time.sleep(5)
            if self.tracking is True:
                if self.debug:
                    self.log.append("Making query...")
                event_time = self.query()

                if event_time is not None:
                    self.oracle.set_offset(event_time[0], event_time[1], self.mode)
                    if self.debug:
                       self.log.append("INFO: Event observed {}".format(event_time))
            elif self.debug is True:
                self.log.append("Tracking is disabled...")

if __name__ == '__main__':
    print("Delphi: Interactive Oracle Shell\n")
    user = input("Primary Nation Name: ")

    refresh = input("Do you want to download the latest daily dump? (Y/N) ")
    if refresh.lower() == 'y':
        print("Downloading regions.xml.gz...")
        url = 'https://www.nationstates.net/pages/regions.xml.gz'
        request = urllib.request.Request(url=url, headers={'User-Agent': "oracle2/{}".format(user)})
        with urllib.request.urlopen(request) as r, open("regions.xml.gz", 'wb') as out:
            shutil.copyfileobj(r, out)
            out.close()

        print("Download complete.")

    delphi = Delphi(regions="./regions.xml.gz", ua=user)

    while True:
        print("Ready.")
        cmd = input("DELPHI({})> ".format(delphi.mode, delphi.target))
        if cmd == 'quit':
            break
        print(delphi.parse(cmd))
