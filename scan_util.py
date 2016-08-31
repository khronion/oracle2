# utility for scanning regions

import urllib.request
import xml.etree.ElementTree as ET
import time


class ScanUtil:




    # queries founder/delegate/officers
    regionQuery = "https://www.nationstates.net/cgi-bin/api.cgi?region={}&q=" \
                  "delegateauth+nations+officers+founderauth+delegate+delegateauth+delegatevotes+founder"

    # censusid-65 is SPDR, 66 is endorsements
    nationQuery = "https://www.nationstates.net/cgi-bin/api.cgi?nation={}&q=wa+census;scale=65+66;mode=score"

    def __init__(self, target, user=""):

        self.officers = {}
        self.nations = {}
        self.nations_loaded = False

        if user == "":
            self.user = input("Nation name or email: ")
        else:
            self.user = user

        # grab region XML
        self.target = target.replace(" ", "_")

        api_call = self.regionQuery.format(self.target)
        api_handler = urllib.request.Request(url=api_call, headers={'User-Agent': self.user})
        region_xml = ET.fromstring((urllib.request.urlopen(api_handler).read().decode()))
        # Get founder information
        self.founder = region_xml.find("FOUNDER").text
        fauth = region_xml.find("FOUNDERAUTH").text
        if "B" in fauth:
            self.founder_bc = "Yes"
        else:
            self.founder_bc = "No"

        # Get delegate information
        self.delegate = region_xml.find("DELEGATE").text
        delauth = region_xml.find("DELEGATEAUTH").text
        if 'B' in delauth:
            self.delegate_bc = "Yes"
        else:
            self.delegate_bc = "No"
        self.delegate_votes = region_xml.find("DELEGATEVOTES").text

        # Get officer information
        for officer in region_xml.find("OFFICERS"):
            o_name = officer.find("NATION").text
            if 'B' in officer.find("AUTHORITY").text:
                o_bc = "Yes"
            else:
                o_bc = "No"
            self.officers[o_name] = o_bc

        # Get nations
        nations = region_xml.find("NATIONS").text.split(":")

        for nation in nations:
            self.nations[nation] = {"WA": False, "Endos": 0, "SPDR": 0}

    # loads nation data
    def load_nations(self):
        if not self.nations_loaded:
            i = 1
            ref = self.nations.keys()
            for nation in ref:
                print("Loading {} out of {} ({})...".format(i, len(self.nations), nation))
                api_call = self.nationQuery.format(nation)
                api_handler = urllib.request.Request(url=api_call, headers={'User-Agent': self.user})
                region_xml = ET.fromstring((urllib.request.urlopen(api_handler).read().decode()))

                self.nations[nation]["WA"] = region_xml.find("UNSTATUS").text
                self.nations[nation]["Endos"] = int(float(region_xml.find("./CENSUS/SCALE[@id='66']").find("SCORE").text))
                self.nations[nation]["SPDR"] = int(float(region_xml.find("./CENSUS/SCALE[@id='65']").find("SCORE").text))

                i += 1
                time.sleep(32/50)

            self.nations_loaded = True
        else:
            pass

    # reports on border control authority entities
    def auth(self):
        print("{0:^80}\n{1:^80}".format("Border Control Report", self.target))
        print("{0:<50}{1:<15}{2:>15}".format(self.founder, "founder", self.founder_bc))
        print("{0:<50}{1:<15}{2:>15}".format(self.delegate, "delegate", self.delegate_bc))
        for officer in self.officers.keys():
            print("{0:<50}{1:<15}{2:>15}".format(officer, "officer", self.officers[officer]))

    # reports on endorsement counts + SPDR for WA nations
    def endo(self):
        if not self.nations_loaded:
            self.load_nations()
        print("{0:^80}\n{1:^80}".format("Endorsement Report", self.target))
        print("{0:<50}{1:<15}{2:>15}".format("Nation", "Endorsements", "SPDR"))
        for nation in self.nations.keys():
            if "WA" in self.nations[nation]["WA"]:
                print("{0:<50}{1:<15}{2:>15}".format(nation, self.nations[nation]["Endos"], self.nations[nation]["SPDR"]))

    # reports on SPDR for all nations
    def spdr(self):
        if not self.nations_loaded:
            self.load_nations()

        print("{0:^80}\n{1:^80}".format("SPDR Report", self.target))
        print("{0:<65}{1:>15}".format("Nation", "SPDR"))

        for nation in self.nations.keys():
            print("{0:<65}{1:>15}".format(nation, self.nations[nation]["SPDR"]))

user = "Khronion Denral"
scanner = None
while True:
    command = input("> ")
    action = command.split(" ")[0]
    args = " ".join(command.split(" ")[1:])

    if action == 't':
        del scanner
        scanner = ScanUtil(args, user)
        print("Target set to {} (population: {}).".format(args, len(scanner.nations)))
    elif action == 'e':
        if scanner is None:
            print("ERROR: Set target.")
        else:
            scanner.endo()
    elif action == 's':
        if scanner is None:
            print("ERROR: Set target.")
        else:
            scanner.spdr()
    elif action == 'b':
        scanner.auth()
    else:
        print("""Command not recognized. Valid commands are:
t <target> -- Set target region
e          -- Generate endorsement report
s          -- Generate SPDR report
b          -- Generate border control authority report
""")