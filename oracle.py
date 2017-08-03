import xml.etree.ElementTree as ET
import urllib.request
import urllib
import gzip
import datetime
import UpdTime

# Oracle: Nationstates Region Update Predictor
# Project page: <https://gitlab.com/khronion/oracle>
#
# Maintained by Khronion <khronion@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


class Oracle:
    def __init__(self, regions, ua):
        """
        Initializes an Oracle object to process a NationStates regions.xml.gz dump.

        :param regions: Path to NationStates regions.xml.gz dump
        :param ua: User Agent string that identifies the operator as required by NS TOS; Should be an email or nation
        :param major: Length of major update
        :param minor: Length of minor update
        """

        self.speed = UpdTime.UpdTime(ua).get()

        self.version = 1
        # set UA
        self.ua = "Oracle {} (developed by khronion@gmail.com, in use by <{}>)".format(self.version, ua)

        # set major/minor mode. Assume major unless user passes minor in because seriously, who's around for minor?

        # load founderless regions into a list
        apiCall = 'https://www.nationstates.net/cgi-bin/api.cgi?q=regionsbytag;tags=founderless,-password'
        ns_request_url = urllib.request.Request(url=apiCall, headers={'User-Agent': self.ua})
        founderlessXML = ET.fromstring((urllib.request.urlopen(ns_request_url).read().decode()))
        founderlessList = founderlessXML.find("REGIONS").text.lower().split(",")
        # load regions.xml.gz
        with gzip.open(regions) as f:
            regionsXML = ET.parse(f).getroot()

        # populate regionList with tuples that links region name to update time and other useful info
        # this is made accessible in the future in case the user decides to regenerate times with a new update speed
        # regionList format: name, population, cumulative population, endorsements, founderless status
        self.regionList = []
        for region in regionsXML:
            name = region.find("NAME").text.lower()
            population = int(region.find("NUMNATIONS").text)
            endos = int(region.find("DELEGATEVOTES").text)
            if name.lower() in founderlessList:
                founderless = True
            else:
                founderless = False
            self.regionList.append([name, population, 0, endos, founderless])

        # calculate cumulative population, or cPop.
        # Why? cPop * per nation update time = region update time
        for i in range(len(self.regionList)):
            # we are on the first updating region, cPop is zero
            if i == 0:
                self.regionList[i][2] = 0
            # cPop is previous region's cPop plus region's population
            else:
                self.regionList[i][2] = self.regionList[i - 1][2] + self.regionList[i][1]

        # create dictionary of all regions for easy lookup
        self.lookupTable = {}
        self.sortedTable = []
        for region in self.regionList:
            self.lookupTable[region[0]] = region[1:]

        # set default offset to zero.
        self.offset = 0

    # predicts a region's update time
    def get_time(self, region, mode):
        """
        Gets a region's update time in seconds after the beginning of the update.

        :param region: Name of region to get update time for.
        :param mode: Update to get region's update time for (must be major or minor)
        :return: Time of update in seconds
        """
        # update time is given by region's cumulative population * per nation update speed
        cPop = self.lookupTable[region.lower()][1]

        return cPop * self.speed[mode] / self.regionList[-1][2] - self.offset

    def get_time_hms(self, region, mode):
        """
        Gets a region's update time as a tuple containing update time in hours, minutes, and seconds

        :param region: Name of region to get update time for.
        :param mode: Update to get region's update time for (must be major or minor)
        :return: Time of update in a tuple (hours, minutes, seconds)
        """
        t = self.get_time(region, mode)  # DON'T REAPPLY OFFSET HERE -- IT'LL DOUBLE OFFSET
        h = int(t / 3600)
        m = int(t / 60) % 60
        s = int(t % 60)

        return h, m, s

    def get_info(self, region):
        """
        Get information about a region.

        :param region: Region to get information about
        :return: Dictionary with the following keys: major, minor, population, cumulative, endos, founder
        """
        data = self.lookupTable[region.lower()]
        return {'major': self.get_time(region.lower(), 'major'),
                'minor': self.get_time(region.lower(), 'minor'),
                'population': data[0],
                'cumulative': data[1],
                'endos': data[2],
                'founder': data[3]}

    # adjusts prediction offset needed based off a region and its true update time and returns it
    def set_offset(self, region, time, mode):
        """
        Calculates a time offset to apply to all future predictions based off of difference between true and estimated
        time.

        :param region: Region with known update time
        :param time: True update time of region in seconds
        :param mode: Update during which time was observed (must be "major or "minor")
        """
        estimate = self.get_time(region, mode)
        self.offset += estimate - time

    # calibrates update speed based on a given region and its observed update time.
    def calibrate(self, time, mode):
        """
        Calculates the per nation update speed to apply to all future predictions based off the true update time of a
        late updating region. Incorrect values (or any value for an early updating region) will negatively impact
        prediction accuracy. For best results, use an average value observed over several days.

        :param time: True length of update
        :param mode: Update during which time was observed (must be "major" or "minor")
        """
        # per nation update speed is given by cumulative population / region update time in seconds
        # store this update speed. It will be lost if Oracle is restarted.
        if mode in self.speed.keys():
            self.speed[mode] = time

    # creates a sorted CSV.
    def csv_export(self, mode, path):
        """
        Exports a sorted CSV of update information.

        :param mode: Update to export information for (must be major or minor)
        :param path: Path to export CSV to.
        """
        file = open(path, 'w')
        with file as out:
            out.write("region,population,endorsements,founderless,h,m,s,,{},{}\n".
                      format(mode, datetime.date.today().strftime("%B %d-%Y")))
            for i in self.regionList:
                out.write("=HYPERLINK(\"{url}\"),{pop},{endo},{founderless},{h},{m},{s}\n".format(
                    url="http://www.nationstates.net/region=" + i[0].replace(" ", "_"),
                    pop=i[1],
                    endo=i[3],
                    founderless=i[4],
                    h=self.get_time_hms(i[0], mode)[0],
                    m=self.get_time_hms(i[0], mode)[1],
                    s=self.get_time_hms(i[0], mode)[2]))

    # creates a sorted HTML page.
    def html_export(self, mode, path):
        """
        Exports a sorted HTML file of update information.

        :param mode: Update to export information for (must be major or minor)
        :param path: Path to export HTML file to.
        """
        file = open(path, 'w')
        with file as out:
            out.write("""
            <html><head><title>{} update, {}</title></head><body>
            <table><tr><td>URL</td><td>Population</td><td>Endorsements</td>
            <td>Founderless?</td><td>H</td><td>M</td><td>S</td></tr>
            """.format(mode, datetime.date.today().strftime("%B %d-%Y")))

            for i in self.regionList:
                out.write(
                    "<tr><td>{url}</td><td>{pop}</td><td>{endo}</td>"
                    "<td>{founderless}</td><td>{h}</td><td>{m}</td><td>{s}</td></tr>\n".format(
                        url="http://www.nationstates.net/region=" + i[0].replace(" ", "_"),
                        pop=i[1],
                        endo=i[3],
                        founderless=i[4],
                        h=self.get_time_hms(i[0], mode)[0],
                        m=self.get_time_hms(i[0], mode)[1],
                        s=self.get_time_hms(i[0], mode)[2]))

            out.write("""
            </table>
            </body>
            </html>
            """)

    def founderless_export(self, mode, path):
        """
        Exports a sorted CSV of founderless region information.

        :param mode: Update to export information for (must be major or minor)
        :param path: Path to export CSV to.
        """
        file = open(path, 'w')
        with file as out:
            out.write("region,population,endorsements,founderless,h,m,s,,{},{}\n".
                      format(mode, datetime.date.today().strftime("%B %d-%Y")))
            for i in self.regionList:
                if i[4] is True:
                    out.write("=HYPERLINK(\"{url}\"),{pop},{endo},{founderless},{h},{m},{s}\n".format(
                        url="http://www.nationstates.net/region=" + i[0].replace(" ", "_"),
                        pop=i[1],
                        endo=i[3],
                        founderless=i[4],
                        h=self.get_time_hms(i[0], mode)[0],
                        m=self.get_time_hms(i[0], mode)[1],
                        s=self.get_time_hms(i[0], mode)[2]))