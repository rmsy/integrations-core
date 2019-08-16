# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
from requests import HTTPError, Timeout

from datadog_checks.base import AgentCheck, ConfigurationError

SERVICE_CHECK_PROCESS_CAN_CONNECT = 'druid.process.can_connect'
SERVICE_CHECK_PROCESS_STATUS = 'druid.process.health'


class DruidCheck(AgentCheck):
    def check(self, instance):
        custom_tags = instance.get('tags', [])

        base_url = instance.get('url')
        if not base_url:
            raise ConfigurationError('Missing configuration: url')

        process_properties = self._get_process_properties(base_url, custom_tags)

        druid_service = process_properties['druid.service']
        tags = custom_tags + ['service:{}'.format(druid_service)]

        self._submit_status_service_check(base_url, tags)

    def _submit_status_service_check(self, base_url, tags):
        url = base_url + "/status/health"
        service_check_tags = ['url:{}'.format(url)] + tags

        resp = self._make_request(url)

        if resp is True:
            status = AgentCheck.OK
        else:
            status = AgentCheck.CRITICAL

        self.service_check(SERVICE_CHECK_PROCESS_STATUS, status, tags=service_check_tags)

    def _get_process_properties(self, base_url, tags):
        url = base_url + "/status/properties"
        service_check_tags = ['url:{}'.format(url)] + tags

        resp = self._make_request(url)

        if resp is None:
            status = AgentCheck.CRITICAL
        else:
            status = AgentCheck.OK

        self.service_check(SERVICE_CHECK_PROCESS_CAN_CONNECT, status, tags=service_check_tags)
        return resp

    def _make_request(self, url):
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: {} with exception: {}. Please verify the address is reachable".format(url, e)
            )
        except requests.exceptions.Timeout as e:
            self.warning("Connection timeout when connecting to {}: {}".format(url, e))
