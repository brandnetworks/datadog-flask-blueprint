# datadog-flask-blueprint
A blueprint class for sending metrics to Datadog.

v0.0.2

## Install 

To install a particular version:

```
pip install git+http://git@github.com/brandnetworks/datadog-flask-blueprint.git@0.0.1#egg=datadog_flask_blueprint
```

To install via branch (while making sure to grab latest changes to that branch):

```
pip install -e git+http://git@github.com/brandnetworks/datadog-flask-blueprint.git@master#egg=datadog_flask_blueprint
```

Note: `-e` causes pip to install fresh via git. Without the `-e` subsequent pip installs will not get new changes.

## Configuration

Make sure that you have the following configured on your flask applications config:

```
app.config['DOGSTATSD'] = {
    'HOST': 'the-host-for-dogstatsd',
    'PREFIX': 'prefix-to-be-used-as-your-metric',
    'ENABLED': True, # False if you do not want stats to be sent to datadog
    'TAG_ALL_QUERY_PARAMS': False, # True if you want all of your query parameters to appear in datadog as tags
    'ENVIRONMENT': 'production'
}
```

## Usage

Where you declare your route blueprints:

```
from bn.blueprints.datadog import DatadogBlueprint

blueprint = DatadogBlueprint('name',
                             __name__,
                             query_parameters=['query', 'params', 'to', 'tag'],
                             metric='name-of-metric', # Note; metric will get prefix + metric
                             tags=['tags', 'to', 'always', 'add:to', 'routes', 'for', 'this:blueprint'],
                             req_tag_func=function_defined_to_tag_request_object,
                             res_tag_func=function_defined_to_tag_response_object)
```

### Request Tag Function

If you'd like to tag particular items based on your request use the request tag function: `req_tag_func`

This library is already configured to use the following function in addition to what is defined in the `req_tag_func`:

```
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
        tags += cls.get_tags_from_query_params(request, valid_query_params) # Retrieves tags from the query parameters
        return tags
```

### Response Tag Function

If you'd like to tag particular items based on your response use the response tag function: `res_tag_func`

This library is already configured to use the following function in addition to what is defined in the `res_tag_func`:

```
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
```