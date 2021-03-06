# Copyright 2017, Optimizely
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

import sys

from . import bucketer
from .helpers import audience as audience_helper
from .helpers import enums
from .helpers import experiment as experiment_helper
from .helpers import validator
from .user_profile import UserProfile


class DecisionService(object):
  """ Class encapsulating all decision related capabilities. """

  def __init__(self, config, user_profile_service):
    self.bucketer = bucketer.Bucketer(config)
    self.user_profile_service = user_profile_service
    self.config = config
    self.logger = config.logger

  def get_forced_variation(self, experiment, user_id):
    """ Determine if a user is forced into a variation for the given experiment and return that variation.

    Args:
      experiment: Object representing the experiment for which user is to be bucketed.
      user_id: ID for the user.

    Returns:
      Variation in which the user with ID user_id is forced into. None if no variation.
    """

    forced_variations = experiment.forcedVariations
    if forced_variations and user_id in forced_variations:
      variation_key = forced_variations.get(user_id)
      variation = self.config.get_variation_from_key(experiment.key, variation_key)
      if variation:
        self.config.logger.log(enums.LogLevels.INFO,
                               'User "%s" is forced in variation "%s".' % (user_id, variation_key))
      return variation

    return None

  def get_stored_variation(self, experiment, user_profile):
    """ Determine if the user has a stored variation available for the given experiment and return that.

    Args:
      experiment: Object representing the experiment for which user is to be bucketed.
      user_profile: UserProfile object representing the user's profile.

    Returns:
      Variation if available. None otherwise.
    """

    user_id = user_profile.user_id
    variation_id = user_profile.get_variation_for_experiment(experiment.id)

    if variation_id:
      variation = self.config.get_variation_from_id(experiment.key, variation_id)
      if variation:
        self.config.logger.log(enums.LogLevels.INFO,
                               'Found a stored decision. User "%s" is in variation "%s" of experiment "%s".' %
                               (user_id, variation.key, experiment.key))
        return variation

    return None

  def get_variation(self, experiment, user_id, attributes, ignore_user_profile=False):
    """ Top-level function to help determine variation user should be put in.

    First, check if experiment is running.
    Second, check if user is forced in a variation.
    Third, check if there is a stored decision for the user and return the corresponding variation.
    Fourth, figure out if user is in the experiment by evaluating audience conditions if any.
    Fifth, bucket the user and return the variation.

    Args:
      experiment_key: Experiment for which user variation needs to be determined.
      user_id: ID for user.
      attributes: Dict representing user attributes.
      ignore_user_profile: True to ignore the user profile lookup. Defaults to False.

    Returns:
      Variation user should see. None if user is not in experiment or experiment is not running.
    """

    # Check if experiment is running
    if not experiment_helper.is_experiment_running(experiment):
      self.logger.log(enums.LogLevels.INFO, 'Experiment "%s" is not running.' % experiment.key)
      return None

    # Check to see if user is white-listed for a certain variation
    variation = self.get_forced_variation(experiment, user_id)
    if variation:
      return variation

    # Check to see if user has a decision available for the given experiment
    user_profile = UserProfile(user_id)
    if not ignore_user_profile and self.user_profile_service:
      try:
        retrieved_profile = self.user_profile_service.lookup(user_id)
      except:
        error = sys.exc_info()[1]
        self.logger.log(
          enums.LogLevels.ERROR,
          'Unable to retrieve user profile for user "%s" as lookup failed. Error: %s' % (user_id, str(error))
        )
        retrieved_profile = None

      if validator.is_user_profile_valid(retrieved_profile):
        user_profile = UserProfile(**retrieved_profile)
        variation = self.get_stored_variation(experiment, user_profile)
        if variation:
          return variation
      else:
        self.logger.log(enums.LogLevels.WARNING, 'User profile has invalid format.')

    # Bucket user and store the new decision
    if not audience_helper.is_user_in_experiment(self.config, experiment, attributes):
      self.logger.log(
        enums.LogLevels.INFO,
        'User "%s" does not meet conditions to be in experiment "%s".' % (user_id, experiment.key)
      )
      return None

    variation = self.bucketer.bucket(experiment, user_id)

    if variation:
      # Store this new decision and return the variation for the user
      if not ignore_user_profile and self.user_profile_service:
        try:
          user_profile.save_variation_for_experiment(experiment.id, variation.id)
          self.user_profile_service.save(user_profile.__dict__)
        except:
          error = sys.exc_info()[1]
          self.logger.log(enums.LogLevels.ERROR,
                          'Unable to save user profile for user "%s". Error: %s' % (user_id, str(error)))
      return variation

    return None

  def get_variation_for_layer(self, layer, user_id, attributes=None, ignore_user_profile=False):
    """ Determine which variation the user is in for a given layer.
    Returns the variation of the first experiment the user qualifies for.

    Args:
      layer: Layer for which we are getting the variation.
      user_id: ID for user.
      attributes: Dict representing user attributes.
      ignore_user_profile: True to ignore the user profile lookup. Defaults to False.


    Returns:
      Variation the user should see. None if the user is not in any of the layer's experiments.
    """
    # Go through each experiment in order and try to get the variation for the user
    if layer:
      for experiment_dict in layer.experiments:
        experiment = self.config.get_experiment_from_key(experiment_dict['key'])
        variation = self.get_variation(experiment, user_id, attributes, ignore_user_profile)
        if variation:
          self.logger.log(enums.LogLevels.DEBUG,
                          'User "%s" is in variation %s of experiment %s.' % (user_id, variation.key, experiment.key))
          # Return as soon as we get a variation
          return variation

    return None

  def get_variation_for_feature(self, feature, user_id, attributes=None):
    """ Returns the variation the user is bucketed in for the given feature.

    Args:
      feature: Feature for which we are determining if it is enabled or not for the given user.
      user_id: ID for user.
      attributes: Dict representing user attributes.

    Returns:
      Variation that the user is bucketed in. None if the user is not in any variation.
    """
    variation = None

    # First check if the feature is in a mutex group
    if feature.groupId:
      group = self.config.get_group(feature.groupId)
      if group:
        experiment = self.get_experiment_in_group(group, user_id)
        if experiment and experiment.id in feature.experimentIds:
          variation = self.get_variation(experiment, user_id, attributes)

          if variation:
            self.logger.log(enums.LogLevels.DEBUG,
                            'User "%s" is in variation %s of experiment %s.' % (user_id, variation.key, experiment.key))
      else:
        self.logger.log(enums.LogLevels.ERROR, enums.Errors.INVALID_GROUP_ID_ERROR.format('_get_variation_for_feature'))

    # Next check if the feature is being experimented on
    elif feature.experimentIds:
      # If an experiment is not in a group, then the feature can only be associated with one experiment
      experiment = self.config.get_experiment_from_id(feature.experimentIds[0])
      if experiment:
        variation = self.get_variation(experiment, user_id, attributes)

        if variation:
          self.logger.log(enums.LogLevels.DEBUG,
                          'User "%s" is in variation %s of experiment %s.' % (user_id, variation.key, experiment.key))

    # Next check if user is part of a rollout
    if not variation and feature.layerId:
      layer = self.config.get_layer_from_id(feature.layerId)
      variation = self.get_variation_for_layer(layer, user_id, attributes, ignore_user_profile=True)

    return variation

  def get_experiment_in_group(self, group, user_id):
    """ Determine which experiment in the group the user is bucketed into.

    Args:
      group: The group to bucket the user into.
      user_id: ID of the user.

    Returns:
      Experiment if the user is bucketed into an experiment in the specified group. None otherwise.
    """

    experiment_id = self.bucketer.find_bucket(user_id, group.id, group.trafficAllocation)
    if experiment_id:
      experiment = self.config.get_experiment_from_id(experiment_id)
      if experiment:
        self.logger.log(enums.LogLevels.INFO,
                        'User "%s" is in experiment %s of group %s.' %
                        (user_id, experiment.key, group.id))
        return experiment

    self.logger.log(enums.LogLevels.INFO,
                    'User "%s" is not in any experiments of group %s.' %
                    (user_id, group.id))

    return None
