import time

from random import randint
from math import sqrt

from occameracontrol.camera import Camera

# Just a very rudimentary testing script for some methods of the camera class


# Initialization
c1 = Camera("15-217-3", "http://camera-sony-15-217.virtuos.uni-osnabrueck.de", "sony", "", 3, 0)
c2 = Camera("15-217-1", "http://camera-panasonic-15-217.virtuos.uni-osnabrueck.de", "panasonic", "", 10, 2)
c3 = Camera("Test 3", "", "NOT A SUPPORTED CAMERA TYPE", "", 5, 8)


def getTestList(min, max):
    testlist = []

    for i in range(int(max/sqrt(max))):
        n = randint(min, max)
        while n in testlist:
            n = randint(min, max)
        testlist.append(n)
    return testlist


def test_setPreset():
    '''test setPreset
    '''
    # Test Sony Cameras

    # Might be difficult to test like that, because Sony can have any number of presets
    assert c1.setPreset(0) == -1
    assert c1.setPreset(20) == -1
    testlist = getTestList(1, 10)
    print(testlist)
    for i in testlist:
        print("Test ", i)
        code = c1.setPreset(i)
        assert code == 200, str(code) + " " + str(i)
        time.sleep(3)

    # Test Panasonic Cameras
    assert c2.setPreset(-1) == -1
    assert c2.setPreset(223) == -1
    testlist = getTestList(1, 100)
    print(testlist)
    for i in testlist:
        print("Test ", i)
        code = c2.setPreset(i)
        assert code == 200, str(code) + " " + str(i)
        time.sleep(3)

    # Test unsupported cameras
    assert c3.setPreset(0) == -1


test_setPreset()
