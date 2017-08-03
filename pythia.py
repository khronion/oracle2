import threading
import urllib.request
import datetime
import time
import UpdTime
import xml.etree.ElementTree as et


class Pythia:
    def __init__(self, ua):
        self.ua = ua
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

    def query(self):
        """
        Queries the NationStates API for events which may reveal the current progress of the update.

        :return: Array [region_name, observed_update_time] or None if no event was observed.
        """
        headers = {u'User-Agent': self.ua}
        feed_url = u"https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=change;"
        query = urllib.request.Request(feed_url, headers=headers)
        xml = et.fromstring(urllib.request.urlopen(query).read())

        for event in xml.iter(u'EVENT'):
            time = int(event.find(u"TIMESTAMP").text)
            event_text = event.find(u"TEXT").text
            if u"influence" in event_text or u"ranked" in event_text:
                nation = event_text.split("@@")[1]
                region_url = u"https://www.nationstates.net/cgi-bin/api.cgi?nation={}&q=region".format(nation)
                region_query = urllib.request.Request(region_url, headers=headers)
                region_xml = et.fromstring(urllib.request.urlopen(region_query).read())
                region = region_xml.find(u"REGION").text

                # calculate how long after the update start the event was observed
                if self.mode is "minor":
                    time -= UpdTime.UpdTime.timestamp(self.time_base + datetime.timedelta(hours=16))
                else:
                    time -= UpdTime.UpdTime.timestamp(self.time_base + datetime.timedelta(hours=4))

                return [region, time]
        return None

if __name__ == '__main__':
    p = Pythia("Khronion")

    while True:
        time.sleep(5)
        print(p.query())