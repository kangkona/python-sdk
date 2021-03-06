# Copyright 2016-2017, Optimizely
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
import unittest

from optimizely import event_builder
from optimizely import exceptions
from optimizely import version
from optimizely.helpers import enums
from . import base


class EventTest(unittest.TestCase):

  def test_init(self):
    url = 'event.optimizely.com'
    params = {
      'a': '111001',
      'n': 'test_event',
      'g': '111028',
      'u': 'oeutest_user'
    }
    http_verb = 'POST'
    headers = {'Content-Type': 'application/json'}
    event_obj = event_builder.Event(url, params, http_verb=http_verb, headers=headers)
    self.assertEqual(url, event_obj.url)
    self.assertEqual(params, event_obj.params)
    self.assertEqual(http_verb, event_obj.http_verb)
    self.assertEqual(headers, event_obj.headers)


class EventBuilderTest(base.BaseTest):

  def setUp(self):
    base.BaseTest.setUp(self)
    self.event_builder = self.optimizely.event_builder

  def _validate_event_object(self, event_obj, expected_url, expected_params, expected_verb, expected_headers):
    """ Helper method to validate properties of the event object. """

    self.assertEqual(expected_url, event_obj.url)
    self.assertEqual(expected_params, event_obj.params)
    self.assertEqual(expected_verb, event_obj.http_verb)
    self.assertEqual(expected_headers, event_obj.headers)

  def test_create_impression_event(self):
    """ Test that create_impression_event creates Event object with right params. """

    expected_params = {
      'accountId': '12001',
      'projectId': '111001',
      'layerId': '111182',
      'visitorId': 'test_user',
      'decision': {
        'experimentId': '111127',
        'variationId': '111129',
        'isLayerHoldback': False
      },
      'revision': '42',
      'timestamp': 42123,
      'isGlobalHoldback': False,
      'userFeatures': [],
      'clientEngine': 'python-sdk',
      'clientVersion': version.__version__
    }
    with mock.patch('time.time', return_value=42.123):
      event_obj = self.event_builder.create_impression_event(
        self.project_config.get_experiment_from_key('test_experiment'), '111129', 'test_user', None
      )
    self._validate_event_object(event_obj,
                                event_builder.EventBuilder.IMPRESSION_ENDPOINT,
                                expected_params,
                                event_builder.EventBuilder.HTTP_VERB,
                                event_builder.EventBuilder.HTTP_HEADERS)

  def test_create_impression_event__with_attributes(self):
    """ Test that create_impression_event creates Event object
    with right params when attributes are provided. """

    expected_params = {
      'accountId': '12001',
      'projectId': '111001',
      'layerId': '111182',
      'visitorId': 'test_user',
      'revision': '42',
      'decision': {
        'experimentId': '111127',
        'variationId': '111129',
        'isLayerHoldback': False
      },
      'timestamp': 42123,
      'isGlobalHoldback': False,
      'userFeatures': [{
        'id': '111094',
        'name': 'test_attribute',
        'type': 'custom',
        'value': 'test_value',
        'shouldIndex': True
      }],
      'clientEngine': 'python-sdk',
      'clientVersion': version.__version__
    }
    with mock.patch('time.time', return_value=42.123):
      event_obj = self.event_builder.create_impression_event(
        self.project_config.get_experiment_from_key('test_experiment'),
        '111129', 'test_user', {'test_attribute': 'test_value'}
      )
    self._validate_event_object(event_obj,
                                event_builder.EventBuilder.IMPRESSION_ENDPOINT,
                                expected_params,
                                event_builder.EventBuilder.HTTP_VERB,
                                event_builder.EventBuilder.HTTP_HEADERS)

  def test_create_conversion_event__with_attributes(self):
    """ Test that create_conversion_event creates Event object
    with right params when attributes are provided. """

    expected_params = {
      'accountId': '12001',
      'projectId': '111001',
      'visitorId': 'test_user',
      'eventName': 'test_event',
      'eventEntityId': '111095',
      'eventMetrics': [],
      'eventFeatures': [],
      'revision': '42',
      'layerStates': [{
          'layerId': '111182',
          'revision': '42',
          'decision': {
            'experimentId': '111127',
            'variationId': '111129',
            'isLayerHoldback': False
          },
          'actionTriggered': True,
        }
      ],
      'timestamp': 42123,
      'isGlobalHoldback': False,
      'userFeatures': [{
        'id': '111094',
        'name': 'test_attribute',
        'type': 'custom',
        'value': 'test_value',
        'shouldIndex': True
      }],
      'clientEngine': 'python-sdk',
      'clientVersion': version.__version__
    }
    with mock.patch('time.time', return_value=42.123), \
      mock.patch('optimizely.bucketer.Bucketer._generate_bucket_value', return_value=5042):
      event_obj = self.event_builder.create_conversion_event(
        'test_event', 'test_user', {'test_attribute': 'test_value'}, None,
        [('111127', '111129')]
      )
    self._validate_event_object(event_obj,
                                event_builder.EventBuilder.CONVERSION_ENDPOINT,
                                expected_params,
                                event_builder.EventBuilder.HTTP_VERB,
                                event_builder.EventBuilder.HTTP_HEADERS)

  def test_create_conversion_event__with_attributes_no_match(self):
    """ Test that create_conversion_event creates Event object with right params if attributes do not match. """

    expected_params = {
      'accountId': '12001',
      'projectId': '111001',
      'visitorId': 'test_user',
      'revision': '42',
      'eventName': 'test_event',
      'eventEntityId': '111095',
      'eventMetrics': [],
      'eventFeatures': [],
      'layerStates': [],
      'timestamp': 42123,
      'isGlobalHoldback': False,
      'userFeatures': [],
      'clientEngine': 'python-sdk',
      'clientVersion': version.__version__
    }
    with mock.patch('time.time', return_value=42.123):
      event_obj = self.event_builder.create_conversion_event('test_event', 'test_user', None, None, [])
    self._validate_event_object(event_obj,
                                event_builder.EventBuilder.CONVERSION_ENDPOINT,
                                expected_params,
                                event_builder.EventBuilder.HTTP_VERB,
                                event_builder.EventBuilder.HTTP_HEADERS)

  def test_create_conversion_event__with_event_value(self):
    """ Test that create_conversion_event creates Event object
    with right params when event value is provided. """

    expected_params = {
      'accountId': '12001',
      'projectId': '111001',
      'visitorId': 'test_user',
      'eventName': 'test_event',
      'eventEntityId': '111095',
      'eventMetrics': [{
        'name': 'revenue',
        'value': 4200
      }],
      'eventFeatures': [{
          'name': 'non-revenue',
          'type': 'custom',
          'value': 'abc',
          'shouldIndex': False,
        }, {
          'name': 'revenue',
          'type': 'custom',
          'value': 4200,
          'shouldIndex': False,
      }],
      'layerStates': [{
          'layerId': '111182',
          'revision': '42',
          'decision': {
            'experimentId': '111127',
            'variationId': '111129',
            'isLayerHoldback': False
          },
          'actionTriggered': True,
        }
      ],
      'timestamp': 42123,
      'revision': '42',
      'isGlobalHoldback': False,
      'userFeatures': [{
        'id': '111094',
        'name': 'test_attribute',
        'type': 'custom',
        'value': 'test_value',
        'shouldIndex': True
      }],
      'clientEngine': 'python-sdk',
      'clientVersion': version.__version__
    }
    with mock.patch('time.time', return_value=42.123), \
         mock.patch('optimizely.bucketer.Bucketer._generate_bucket_value', return_value=5042):
      event_obj = self.event_builder.create_conversion_event(
        'test_event', 'test_user', {'test_attribute': 'test_value'}, {'revenue': 4200, 'non-revenue': 'abc'},
        [('111127', '111129')]
      )

    # Sort event features based on ID
    event_obj.params['eventFeatures'] = sorted(event_obj.params['eventFeatures'], key=lambda x: x.get('name'))
    self._validate_event_object(event_obj,
                                event_builder.EventBuilder.CONVERSION_ENDPOINT,
                                expected_params,
                                event_builder.EventBuilder.HTTP_VERB,
                                event_builder.EventBuilder.HTTP_HEADERS)

  def test_create_conversion_event__with_invalid_event_value(self):
    """ Test that create_conversion_event creates Event object
    with right params when event value is provided. """

    expected_params = {
      'accountId': '12001',
      'projectId': '111001',
      'visitorId': 'test_user',
      'eventName': 'test_event',
      'eventEntityId': '111095',
      'revision': '42',
      'eventMetrics': [],
      'eventFeatures': [{
          'name': 'non-revenue',
          'type': 'custom',
          'value': 'abc',
          'shouldIndex': False,
        }, {
          'name': 'revenue',
          'type': 'custom',
          'value': '4200',
          'shouldIndex': False,
      }],
      'layerStates': [{
          'layerId': '111182',
          'revision': '42',
          'decision': {
            'experimentId': '111127',
            'variationId': '111129',
            'isLayerHoldback': False
          },
          'actionTriggered': True,
        }
      ],
      'timestamp': 42123,
      'isGlobalHoldback': False,
      'userFeatures': [{
        'id': '111094',
        'name': 'test_attribute',
        'type': 'custom',
        'value': 'test_value',
        'shouldIndex': True
      }],
      'clientEngine': 'python-sdk',
      'clientVersion': version.__version__
    }
    with mock.patch('time.time', return_value=42.123), \
      mock.patch('optimizely.bucketer.Bucketer._generate_bucket_value', return_value=5042):
      event_obj = self.event_builder.create_conversion_event(
        'test_event', 'test_user', {'test_attribute': 'test_value'}, {'revenue': '4200', 'non-revenue': 'abc'},
        [('111127', '111129')]
      )
    # Sort event features based on ID
    event_obj.params['eventFeatures'] = sorted(event_obj.params['eventFeatures'], key=lambda x: x.get('name'))
    self._validate_event_object(event_obj,
                                event_builder.EventBuilder.CONVERSION_ENDPOINT,
                                expected_params,
                                event_builder.EventBuilder.HTTP_VERB,
                                event_builder.EventBuilder.HTTP_HEADERS)


class EventBuilderV3Test(base.BaseTestV3):

  def setUp(self):
    base.BaseTestV3.setUp(self)
    self.event_builder = self.optimizely.event_builder

  def _validate_event_object(self, event_obj, expected_url, expected_params, expected_verb, expected_headers):
    """ Helper method to validate properties of the event object. """

    self.assertEqual(expected_url, event_obj.url)
    self.assertEqual(expected_params, event_obj.params)
    self.assertEqual(expected_verb, event_obj.http_verb)
    self.assertEqual(expected_headers, event_obj.headers)

  def test_create_impression_event(self):
    """ Test that create_impression_event creates Event object with right params. """

    expected_params = {
      'account_id': '12001',
      'project_id': '111001',
      'visitors': [{
        'visitor_id': 'test_user',
        'attributes': [],
        'snapshots': [{
          'decisions': [{
            'variation_id': '111129',
            'experiment_id': '111127',
            'campaign_id': '111182'
          }],
          'events': [{
            'timestamp': 42123,
            'entity_id': '111182',
            'uuid': 'a68cf1ad-0393-4e18-af87-efe8f01a7c9c',
            'key': 'campaign_activated'
          }]
        }]
      }],
      'client_name': 'python-sdk',
      'client_version': version.__version__
    }

    with mock.patch('time.time', return_value=42.123), \
      mock.patch('uuid.uuid4', return_value='a68cf1ad-0393-4e18-af87-efe8f01a7c9c'):
      event_obj = self.event_builder.create_impression_event(
        self.project_config.get_experiment_from_key('test_experiment'), '111129', 'test_user', None
      )
    self._validate_event_object(event_obj,
                                event_builder.EventBuilderV3.EVENTS_URL,
                                expected_params,
                                event_builder.EventBuilderV3.HTTP_VERB,
                                event_builder.EventBuilderV3.HTTP_HEADERS)

  def test_create_impression_event__with_attributes(self):
    """ Test that create_impression_event creates Event object
    with right params when attributes are provided. """

    expected_params = {
      'account_id': '12001',
      'project_id': '111001',
      'visitors': [{
        'visitor_id': 'test_user',
        'attributes': [{
          'type': 'custom',
          'value': 'test_value',
          'entity_id': '111094',
          'key': 'test_attribute'
        }],
        'snapshots': [{
          'decisions': [{
            'variation_id': '111129',
            'experiment_id': '111127',
            'campaign_id': '111182'
          }],
          'events': [{
            'timestamp': 42123,
            'entity_id': '111182',
            'uuid': 'a68cf1ad-0393-4e18-af87-efe8f01a7c9c',
            'key': 'campaign_activated'
          }]
        }]
      }],
      'client_name': 'python-sdk',
      'client_version': version.__version__
    }

    with mock.patch('time.time', return_value=42.123), \
      mock.patch('uuid.uuid4', return_value='a68cf1ad-0393-4e18-af87-efe8f01a7c9c'):
      event_obj = self.event_builder.create_impression_event(
        self.project_config.get_experiment_from_key('test_experiment'),
        '111129', 'test_user', {'test_attribute': 'test_value'}
      )
    self._validate_event_object(event_obj,
                                event_builder.EventBuilderV3.EVENTS_URL,
                                expected_params,
                                event_builder.EventBuilderV3.HTTP_VERB,
                                event_builder.EventBuilderV3.HTTP_HEADERS)

  def test_create_conversion_event__with_attributes(self):
    """ Test that create_conversion_event creates Event object
    with right params when attributes are provided. """

    expected_params = {
      'account_id': '12001',
      'project_id': '111001',
      'visitors': [{
        'visitor_id': 'test_user',
        'attributes': [{
          'type': 'custom',
          'value': 'test_value',
          'entity_id': '111094',
          'key': 'test_attribute'
        }],
        'snapshots': [{
          'decisions': [{
            'variation_id': '111129',
            'experiment_id': '111127',
            'campaign_id': '111182'
          }],
          'events': [{
            'timestamp': 42123,
            'entity_id': '111095',
            'uuid': 'a68cf1ad-0393-4e18-af87-efe8f01a7c9c',
            'key': 'test_event'
          }]
        }]
      }],
      'client_name': 'python-sdk',
      'client_version': version.__version__
    }

    with mock.patch('time.time', return_value=42.123), \
      mock.patch('uuid.uuid4', return_value='a68cf1ad-0393-4e18-af87-efe8f01a7c9c'), \
      mock.patch('optimizely.bucketer.Bucketer._generate_bucket_value', return_value=5042):
      event_obj = self.event_builder.create_conversion_event(
        'test_event', 'test_user', {'test_attribute': 'test_value'}, None, [('111127', '111129')]
      )
    self._validate_event_object(event_obj,
                                event_builder.EventBuilderV3.EVENTS_URL,
                                expected_params,
                                event_builder.EventBuilderV3.HTTP_VERB,
                                event_builder.EventBuilderV3.HTTP_HEADERS)

  def test_create_conversion_event__with_event_value(self):
    """ Test that create_conversion_event creates Event object
    with right params when event value and tags are provided. """

    expected_params = {
      'client_version': version.__version__,
      'project_id': '111001',
      'visitors': [{
        'attributes': [{
          'entity_id': '111094',
          'type': 'custom',
          'value': 'test_value',
          'key': 'test_attribute'
        }],
        'visitor_id': 'test_user',
        'snapshots': [{
          'decisions': [{
            'variation_id': '111129',
            'experiment_id': '111127',
            'campaign_id': '111182'
          }],
          'events': [{
            'uuid': 'a68cf1ad-0393-4e18-af87-efe8f01a7c9c',
            'tags': {
              'non-revenue': 'abc',
              'revenue': 4200
            },
            'timestamp': 42123,
            'revenue': 4200,
            'key': 'test_event',
            'entity_id': '111095'
          }]
        }]
      }],
      'account_id': '12001',
      'client_name': 'python-sdk',
    }

    with mock.patch('time.time', return_value=42.123), \
         mock.patch('optimizely.bucketer.Bucketer._generate_bucket_value', return_value=5042), \
         mock.patch('uuid.uuid4', return_value='a68cf1ad-0393-4e18-af87-efe8f01a7c9c'):
      event_obj = self.event_builder.create_conversion_event(
        'test_event', 'test_user', {'test_attribute': 'test_value'}, {'revenue': 4200, 'non-revenue': 'abc'},
        [('111127', '111129')]
      )
    self._validate_event_object(event_obj,
                                event_builder.EventBuilderV3.EVENTS_URL,
                                expected_params,
                                event_builder.EventBuilderV3.HTTP_VERB,
                                event_builder.EventBuilderV3.HTTP_HEADERS)

  def test_create_conversion_event__with_invalid_event_value(self):
    """ Test that create_conversion_event creates Event object
    with right params when event value is provided. """

    expected_params = {
      'client_version': version.__version__,
      'project_id': '111001',
      'visitors': [{
        'attributes': [{
          'entity_id': '111094',
          'type': 'custom',
          'value': 'test_value',
          'key': 'test_attribute'
        }],
        'visitor_id': 'test_user',
        'snapshots': [{
          'decisions': [{
            'variation_id': '111129',
            'experiment_id': '111127',
            'campaign_id': '111182'
          }],
          'events': [{
            'timestamp': 42123,
            'entity_id': '111095',
            'uuid': 'a68cf1ad-0393-4e18-af87-efe8f01a7c9c',
            'key': 'test_event',
            'tags': {
              'non-revenue': 'abc',
              'revenue': '4200'
            }
          }]
        }]
      }],
      'account_id': '12001',
      'client_name': 'python-sdk',
    }

    with mock.patch('time.time', return_value=42.123), \
      mock.patch('optimizely.bucketer.Bucketer._generate_bucket_value', return_value=5042), \
      mock.patch('uuid.uuid4', return_value='a68cf1ad-0393-4e18-af87-efe8f01a7c9c'):
      event_obj = self.event_builder.create_conversion_event(
        'test_event', 'test_user', {'test_attribute': 'test_value'}, {'revenue': '4200', 'non-revenue': 'abc'},
        [('111127', '111129')]
      )
    self._validate_event_object(event_obj,
                                event_builder.EventBuilderV3.EVENTS_URL,
                                expected_params,
                                event_builder.EventBuilderV3.HTTP_VERB,
                                event_builder.EventBuilderV3.HTTP_HEADERS)
