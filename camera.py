import requests
from requests.auth import HTTPDigestAuth

class camera:
    def __init__(self, ID="", url="", manufacturer="", calendar="", pos=-1, status=0):
        self.ID = ID
        self.url = url
        self.manufacturer = manufacturer
        self.calendar = calendar
        self.pos = pos
        self.status = status

        print("Initialized: ", self)
    
    def __str__(self):
        return f"\'{self.ID}\' @ \'{self.url}\' (Type: \'{self.manufacturer}\') (Current Position: {self.pos})"
    
    def updateCalendar(self, calendar):
        self.calendar = calendar
        
    
    # TODO: If code 200 --> update self.pos 
    def setPreset(self, preset, verbose=False):
        code = -1
        camera = self.url.rstrip('/')
        #print(camera)
        if self.manufacturer == "panasonic":
            if 0 <= preset <= 100:
                params = {'cmd': f'#R{preset - 1:02}', 'res': 1}
                url = f'{camera}/cgi-bin/aw_ptz'
                auth = ('admin', 'PASS')
                if verbose:
                    print("URL:" + url)
                code = requests.get(url, auth=auth, params=params)

            else:
                print("Could not use the specified preset number, because it is out of range.\nThe Range is from 0 to 100 (including borders)")
        elif self.manufacturer == "sony":
            if 1 <= preset <= 10:
                # Presets start at 1 for Sony cameras
                url = f'{camera}/command/presetposition.cgi'
                params = {'PresetCall': preset}
                auth = HTTPDigestAuth('admin', '<password>')
                headers = {'referer': f'{camera}/'}
                if verbose:
                    print("URL:" + url)
                code = requests.get(url, auth=auth, headers=headers, params=params)
            else:
                print("Could not use the specified preset number, because it is out of range.\nThe Range is from 1 to 10 (including borders)")

        else:
            print("Unknown Camera Type \'%s\'.\nKnown Types are \'panasonis\' and \'sony\'." % self.manufacturer)
        return code
