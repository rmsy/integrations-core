# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests

from datadog_checks.base import AgentCheck, ConfigurationError


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

    def _submit_status_service_check(self, base_url, base_tags):
        url = base_url + "/status/health"
        tags = ['url:{}'.format(url)] + base_tags

        resp = self._make_request(url)

        if resp is True:
            status = AgentCheck.OK
        else:
            status = AgentCheck.CRITICAL

        self.service_check('druid.process.health', status, tags=tags)
        self.gauge('druid.process.health', 1 if resp is True else 0, tags=tags)

    def _get_process_properties(self, base_url, tags):
        url = base_url + "/status/properties"
        service_check_tags = ['url:{}'.format(url)] + tags

        resp = self._make_request(url)

        if resp is None:
            status = AgentCheck.CRITICAL
        else:
            status = AgentCheck.OK

        self.service_check('druid.process.can_connect', status, tags=service_check_tags)
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
