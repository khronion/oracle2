import oracle
import time
import threading
import datetime
import urllib.request
import xml.etree.ElementTree as ET


# This file is part of Oracle.
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

    def __init__(self, regions, ua):
        """
        Provides interactive Oracle functionality. This can be used to create bots and user interfaces.

        :param regions: Path to NationStates regional data dump. Can be a string or file object.
        :param ua: User agent string that identifies the operator, as required by NS TOS
        :return:
        """

        self.regions = regions

        self.ua = ua
        self.oracle = oracle.Oracle(regions, ua)

        # persistent state attributes
        self.mode = "major"
        self.target = None

        # initiate tracking
        self.start()

    # main command processor

    def reload(self, regions=""):
        """
        Hotloads a new regions.xml.gz without restarting the Delphi wrapper. This will reset any offsets or
        calibrations.

        :param regions: Path to NationStates regional data dump. Can be a string or file object.
        :return:
        """
        if regions == "":
            self.oracle = oracle.Oracle(regions=self.regions, ua=self.oracle.ua)
        else:
            self.oracle = oracle.Oracle(regions=regions, ua=self.oracle.ua)

    def parse(self, command):
        """
        Parses a command string and returns a text string with a human readable response. Handles any exceptions and
        informs the user gracefully. Command strings can be set by modifying the Delphi class.

        :param command: user input string, formatted as "command arguments"
        :return: user-readable response string
        """
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
                    return "Time predicted for {}: {:02d}:{:02d}:{:02d}.".format(self.target, time[0], time[1], time[2])
                except KeyError:
                    return "ERROR: No such region {}".format(self.target)

            # recall last prediction
            elif action == self.cmd_review:
                if self.target != "":
                    time = self.oracle.get_time_hms(self.target, self.mode)
                    return "Time predicted for {}: {:02d}:{:02d}:{:02d}.".format(self.target, time[0], time[1], time[2])
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

            # calibrate (region name) (time)
            elif action == self.cmd_calibrate:
                # time will be last text blob
                t = args[-1].split(':')
                time = []
                try:
                    for i in t:
                        time.append(int(i))
                except ValueError:
                    return "ERROR: Invalid time provided."

                tSec = time[0] * 3600 + time[1] * 60 + time[2]

                # all other text blobs are part of region name
                region = ' '.join(args[:-1])
                try:
                    self.oracle.calibrate(region, tSec, self.mode)
                    self.oracle.offset = 0
                    return "New update speed is {} seconds/nation.".format(self.oracle.speed[self.mode])
                except KeyError:
                    return "ERROR: No such region {}.".format(region)

            elif action == self.cmd_reload:
                self.reload()
                return "regions.xml.gz has been reloaded. Offsets and speed corrections reset."

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
                return self.start()
            elif action == self.cmd_stop:
                return self.stop()

            else:

                return """Command not recognized. Please use one of the following:

                {} <region> - get region time
                {} <major|minor> - set update mode to major or minor
                {} - recall last targeted  region
                {} <hh:mm:ss> - indicate true update time in hh:mm:ss of last targeted region
                {} <region> <hh:mm:ss> - calibrate update speed based on time of late updating region
                {} <filename> - export CSV of oracle data using current update mode
                {} <filename> - export CSV of oracle data for founderless regions using current update mode
                {} <filename> - export HTML of oracle data using current update mode
                {} - reload regions.xml.gz and reset Oracle settings to default
                {} - start automatic region tracking via API (engaged by default)
                {} - stop automatic region tracking via API
                """.format(self.cmd_time, self.cmd_mode, self.cmd_review, self.cmd_offset, self.cmd_calibrate,
                           self.cmd_export, self.cmd_targets, self.cmd_html, self.cmd_reload, self.cmd_start,
                           self.cmd_stop)

        except IndexError:
            return "ERROR: malformed command."

    thread = None
    tracking = False

    def start(self):
        """
        Starts API tracking.

        :return: user-readable response string
        """
        if not self.tracking:
            self.tracking = True
            self.thread = threading.Thread(target=self.api_runner)
            self.thread.start()
            return "Scanner activated."
        else:
            return "Scanner already active."

    def stop(self):
        """
        Stops API tracking.

        :return: user-readable response string
        """
        if self.tracking:
            self.tracking = False
            return "Scanner deactivated."
        else:
            return "Scanner not running."

    def api_runner(self):
        """
        Tracks the NationStates API, looking for influence changes to determine when a region has updated.
        """
        print("INFO: Tracker starting up.")
        while self.tracking is True:
            # get the latest happenings
            try:
                api_call = 'http://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=change;limit=5'
                ns_request_url = urllib.request.Request(url=api_call, headers={'User-Agent': self.ua})
                happenings = ET.fromstring((urllib.request.urlopen(ns_request_url).read().decode())).find("HAPPENINGS")
                time.sleep(1)
                for event in happenings:

                    # get HMS of event
                    event_time = datetime.datetime.fromtimestamp(float(event.find("TIMESTAMP").text), tz=None)
                    h = event_time.hour
                    m = event_time.minute
                    s = event_time.second

                    # are we major or minor update?
                    if h == 9 or h == 10:
                        mode = 'minor'
                        h -= 9
                    else:
                        mode = 'major'
                        h -= 21
                    event_text = event.find("TEXT").text
                    # if we find an influence change, process it.
                    if "influence in" in event_text:
                        region = self.find_between(event_text, "%%", "%%").replace("_", " ")
                        try:
                            self.oracle.set_offset(region, h * 3600 + m * 60 + s, mode)
                        except KeyError:
                            print("Warning: Couldn't update offset for region {}. "
                                  "Is the daily dump updated?".format(region))
                            pass
                        break
            except TimeoutError:
                print("Warning: Connection timed out. Sleeping 5 seconds.")
                time.sleep(5)

        print("INFO: Tracker shutting down.")

    @staticmethod
    def find_between(s, first, last):
        try:
            start = s.index(first) + len(first)
            end = s.index(last, start)
            return s[start:end]
        except ValueError:
            return ""


if __name__ == '__main__':
    print("Delphi: Proof-of-concept Oracle Shell\n")
    ua = input("Unique identifier (use an email or nation name): ")

    delphi = Delphi(regions="./regions.xml.gz", ua=ua)
    print("Update speed values generated on", delphi.oracle.speed_last_updated)

    while True:
        print("Ready.")
        cmd = input("> ".format(delphi.mode, delphi.target))
        if cmd == 'quit':
            break
        print(delphi.parse(cmd))
