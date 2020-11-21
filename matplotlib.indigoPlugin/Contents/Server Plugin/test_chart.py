#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import pickle

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')
import matplotlib.pyplot as plt

# import DLFramework as Dave

# Collection of logging messages.
# TODO: consider looking at Matt's logging handler and see if that's better.
log = []


def __init__():
    pass


# Unpickle the payload data. The first element of the payload is the name
# of this script and we don't need that. As long as size isn't a limitation
# we will always send the entire payload as element 1.
payload = pickle.loads(sys.argv[1])
log.append(u'payload unpickled successfully.')

# Do the plotting stuff.
plt.figure(figsize=(10, 5))
plt.bar(payload['data']['x_obs'], payload['data']['y_obs'])
plt.savefig(payload['prefs']['chartPath'] + "chart_test.png", **payload['kwargs'])
plt.clf()
log.append(u'Chart processed successfully.')

# Process any standard output. For now, we can only do this once, so we should
# combine any messages we want to send.
pickle.dump(log, sys.stdout)

# Any exceptions should be automatically written to sys.stderr
raise StandardError(u'This is a test error.')
