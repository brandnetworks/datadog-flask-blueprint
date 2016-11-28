"""Datadog blueprint."""
import datetime
import functools
import time
import simplejson as json
import sys

from copy import copy
from flask import Blueprint, request, session, current_app
from dateutil import parser as dateparser
from datadog import DogStatsd


class Config():
    """Config."""

    def __init__(self):
        """__init__."""
        config = current_app.config['DOGSTATSD']
        self.HOST = config['HOST']
        self.PREFIX = config['PREFIX']
        self.ENABLED = config.get('ENABLED', True)
        self.TAG_ALL_QUERY_PARAMS = config.get('TAG_ALL_QUERY_PARAMS', False)
        self.ENVIRONMENT = config.get('ENVIRONMENT', 'None')


def get_statsd():
    """Return statsd client."""
    return DogStatsd(host=Config().HOST)


class DatadogBlueprint(Blueprint):
    """
    Datadog blueprint.

    Sends tags to datadog, as well as uses the req_tag_func and
    res_tag_func on the request and response objects to generate request
    and response tags.
    """

    def __init__(self,
                 name,
                 import_name,
                 metric=None,
                 req_tag_func=None,
                 res_tag_func=None,
                 tags=None,
                 query_parameters=None,
                 *args, **kwargs):
        """Override __init__ func."""
        super(DatadogBlueprint, self).__init__(name, import_name, *args, **kwargs)
        tags = tags or []
        query_parameters = query_parameters or []
        before_func = functools.partial(DatadogBlueprint.datadog_before_request,
                                        tags,
                                        query_parameters,
                                        req_tag_func)
        self.before_request(before_func)

        after_func = functools.partial(DatadogBlueprint.datadog_after_request,
                                       metric,
                                       res_tag_func)
        self.after_request(after_func)

    @classmethod
    def datadog_before_request(cls, tags, valid_query_params, req_tag_func):
        """Datadog before request."""
        request_tags = copy(tags)
        try:
            start = time.time()
            if req_tag_func:
                request_tags += req_tag_func(request)
            default_request_tags = cls.get_tags_from_request(request, valid_query_params)
            request_tags += default_request_tags
        except:
            pass
        finally:
            session['datadog'] = {
                'tags': request_tags,
                'start': start
            }

    @classmethod
    def datadog_after_request(cls, metric, req_tag_func, response):
        """Datadog after request."""
        prefix = Config().PREFIX
        if metric:
            metric = prefix + metric
        else:
            metric = prefix
        try:
            result_tags = []
            response_dict = None
            try:
                response_dict = json.loads(response.get_data(as_text=True))
            except:
                pass
            if req_tag_func:
                result_tags = req_tag_func(response_dict)
            tags = session.get('datadog', {}).get('tags', []) + result_tags
            tags += cls.get_tags_from_response(response, response_dict)

            start = session.get('datadog', {}).get('start')
            dt = int((time.time() - start) * 1000)
            # Need to get statsd
            if Config().ENABLED:
                environment = str(Config().ENVIRONMENT).lower()
                tags += 'app:content_service'
                tags += 'environment:' + environment
                statsd = get_statsd()
                statsd.timing(metric, dt, tags=tags)
                statsd.increment(metric + '.response_code.' + str(response.status_code), 1, tags)
                statsd.increment(metric + '.response_code.all', 1, tags)
        except:
            pass
        finally:
            return response

    @classmethod
    def get_tags_from_request(cls, request, valid_query_params):
        """
        Get datadog tags from the request.

        These are items like method, route that happen on every request.
        """
        tags = []
        tags.append('method:' + request.method)
        tags.append('protocol:' + request.scheme)
        tags.append('path:' + request.path)
        tags.append('endpoint:' + request.endpoint)
        tags += cls.get_tags_from_query_params(request, valid_query_params)
        return tags

    @classmethod
    def get_tags_from_response(cls, response, response_dict):
        """
        Get datadog tags from the response.

        These are items like response code that happen on every request.
        """
        tags = []
        tags.append('response_code:' + str(response.status_code))
        if response_dict and 'data' in response_dict:
            response_size = len(response_dict['data'])
            tags.append('response_data.length:' + str(response_size))
            tags.append('response_data.length.bucket:' + cls.bucket(response_size))
        return tags

    @classmethod
    def get_tags_from_query_params(cls, request, valid_query_params):
        """Request tags."""
        tags = []
        keys = [key for key, _ in request.args.items()]
        filtered_keys = keys
        if not Config().TAG_ALL_QUERY_PARAMS:
            filtered_keys = list(set(valid_query_params).intersection(set(keys)))
        for key in filtered_keys:
            value_list = request.args.getlist(key)
            value = (',' + key + ':').join(value_list)
            tags.append(key + ':' + value)
            tags.append(key + '.count:' + str(len(value_list)))
            tags.append(key + '.count.bucket:' + cls.bucket(len(value_list)))

        if 'since' in keys and 'until' in keys:
            try:
                # Try Except here because we're not confident since and until are dates.
                since = dateparser.parse(request.args['since']).astimezone(tz=datetime.timezone.utc)
                until = dateparser.parse(request.args['until']).astimezone(tz=datetime.timezone.utc)
                duration = until - since
                hours = duration.total_seconds() / 60 / 60
                weeks = round(hours / (24 * 7))
                months = round(duration.days / 30.0)
                # Add duration to tags
                tags.append('duration_days:' + duration.days)
                tags.append('duration_hours.bucket:' + cls.bucket(hours))
                tags.append('duration_days.bucket:' + cls.bucket(duration.days))
                tags.append('duration_weeks:' + cls.bucket(weeks))
                tags.append('duration_months:' + cls.bucket(months))
            except:
                pass
        return tags

    @classmethod
    def bucket(cls, value):
        """Bucket value."""
        bucket_value = 'unknown'
        buckets = [
            (0, 1, '0'),
            (1, 11, '1-10'),
            (11, 26, '11-25'),
            (26, 51, '26-50'),
            (51, 101, '51-100'),
            (101, 251, '101-250'),
            (251, 501, '251-500'),
            (501, 1001, '501-1000'),
            (1001, 2501, '1001-2500'),
            (2501, 5001, '2501-5000'),
            (5001, sys.maxsize, 'gt5000')
        ]
        for min, max, str_value in buckets:
            if value >= min and value < max:
                bucket_value = str_value
        return bucket_value
