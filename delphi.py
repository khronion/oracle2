import oracle
import time
import threading
import datetime
import urllib.request
import urllib
import shutil
import xml.etree.ElementTree as ElementTree

# Oracle 2 NationStates Update Prediction Framework
# Copyright (c) 2017 Khronion <khronion@gmail.com>
#
# Oracle2 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Oracle2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Oracle2.  If not, see <http://www.gnu.org/licenses/>.

class UTC(datetime.tzinfo):
    # code derived from example code in Python2 documentation:
    # https://docs.python.org/2/library/datetime.html#tzinfo-objects
    u"""UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return u"UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


class Delphi:
    # define command keyword for each respective command
    cmd_time = 't'  # get time (region)
    cmd_mode = 'm'  # set mode ('major' or 'minor')
    cmd_review = 'r'  # review last time
    cmd_offset = 'o'  # set offset (region h:m:s)
    cmd_calibrate = 'c'  # calibrate (region h:m:s)
    cmd_nudge = 'n'  # nudge

    cmd_export = 'export'
    cmd_targets = 'targets'
    cmd_html = 'html'
    cmd_reload = 'reload'

    cmd_pull = 'pull'

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

        self.time_now = datetime.datetime.utcnow().replace(tzinfo=UTC())
        self.time_base = datetime.datetime.utcnow().replace(tzinfo=UTC(), hour=0, minute=0, second=0,
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
        self.target = ""

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

        if self.log:
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
                target = ' '.join(args)
                try:
                    predicted_time = self.oracle.get_time_hms(target, self.mode)
                    self.target = target
                    return "Time predicted for {}: {:02d}:{:02d}:{:02d}.\n" \
                           "URL: http://nationstates.net/region={}".format(self.target, predicted_time[0],
                                                                           predicted_time[1], predicted_time[2],
                                                                           self.target.replace(" ", "_"))
                except KeyError:
                    return "ERROR: No such region {}".format(self.target)

            # recall last prediction
            elif action == self.cmd_review:
                if self.target != "":

                    predicted_time = self.oracle.get_time_hms(self.target, self.mode)
                    return "Time predicted for {}: {:02d}:{:02d}:{:02d}.\n" \
                           "URL: http://nationstates.net/region={}".format(self.target, predicted_time[0],
                                                                           predicted_time[1], predicted_time[2],
                                                                           self.target.replace(" ", "_"))
                else:
                    return "ERROR: No previous region to recall."

            # offset (time)
            elif action == self.cmd_offset:
                # time will be last text blob
                t = args[0:2]
                input_time = []
                try:
                    for i in t:
                        input_time.append(int(i))
                    observed_time = input_time[0] * 60 + input_time[1]

                except ValueError:
                    return "ERROR: Invalid time provided."
                # all other text blobs are part of region name
                region = ' '.join(args[:-1])

                try:
                    self.oracle.set_offset(self.target, observed_time, self.mode)
                    return "Offset adjusted to {} seconds.".format(-self.oracle.offset)
                except KeyError:
                    return "ERROR: No such region {}.".format(region)

            # nudge
            elif action == self.cmd_nudge:
                if len(args) > 0:
                    self.oracle.nudge += int(args[0])
                return "Nudge is {}".format(self.oracle.nudge)
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
            elif action == self.cmd_pull:
                return self.pull_time()
            elif action == "dbg":  # this is for troubleshooting use only
                self.debug = not self.debug
                return "!!!! Debug flag toggled."

            else:

                return """
Oracle2 Update Prediction Tool Command Reference

t <region>      Get region time
r               Recall last targeted region
m <major|minor> Set update mode to major or minor
o <MM SS>       Indicate true update time in minutes and seconds of last targeted region
n <seconds>     Add/subtract from nudge value to offset all future predictions.
                If blank, resets nudge.
start           Start automatic tracking
stop            Stop automatic tracking
pull            Manually trigger an API query (only works if automatic tracking is not running)
                WARNING: calling this command repeatedly could trigger an API rate limit violation!
dbg             Toggle debug messages
                """
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

    @staticmethod
    def timestamp(dt):
        return (dt - datetime.datetime(1970, 1, 1).replace(tzinfo=UTC())).total_seconds()

    def find_event(self):
        """
        Queries the NationStates API for events which may reveal the current progress of the update.

        :return: Array [region_name, observed_update_time] or None if no event was observed.
        """
        headers = {u'User-Agent': self.ua}
        feed_url = u"https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=admin;"
        query = urllib.request.Request(feed_url, headers=headers)
        xml = ElementTree.fromstring(urllib.request.urlopen(query).read())

        for event in xml.iter(u'EVENT'):
            event_time = int(event.find(u"TIMESTAMP").text)
            event_text = event.find(u"TEXT").text
            if u"influence" in event_text:
                nation = event_text.split("@@")[1]
                region_url = u"https://www.nationstates.net/cgi-bin/api.cgi?nation={}&q=region".format(nation)
                region_query = urllib.request.Request(region_url, headers=headers)
                region_xml = ElementTree.fromstring(urllib.request.urlopen(region_query).read())
                region = region_xml.find(u"REGION").text

                # calculate how long after the update start the event was observed
                if self.mode is "minor":
                    event_time -= self.timestamp(self.time_base + datetime.timedelta(hours=16))
                else:
                    event_time -= self.timestamp(self.time_base + datetime.timedelta(hours=4))

                if self.debug is True:
                    self.log.append("HIT: {} updated {} sec in".format(region, event_time))
                    self.log.append("API Query: {}".format(region_url.replace(" ", "_")))

                return [region, event_time]
        return None

    def pull_time(self):
        if self.tracking is False:
            event_time = self.find_event()
            if event_time is not None:
                self.oracle.set_offset(event_time[0], event_time[1], self.mode)
                return "Recalibrated."
            else:
                return "No event found."
        else:
            return "Manual queries disabled while automatic tracking enabled."

    def _runner(self):
        while True:
            time.sleep(5)
            if self.tracking is True:
                if self.debug:
                    self.log.append("Making query...")
                event_time = self.find_event()

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
        time_now = datetime.datetime.utcnow()
        print("\nLast target: {} (Type 'r' to recall time prediction.)".format(delphi.target))
        cmd = input('[{:02d}:{:02d}:{:02d} UTC] DELPHI> '.format(time_now.hour, time_now.minute, time_now.second))
        if cmd == 'quit':
            break
        print(delphi.parse(cmd))
