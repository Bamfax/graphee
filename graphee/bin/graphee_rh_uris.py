
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'neo4j_uri',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=500, 
            min_len=1, 
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'graphee_uris',
    model,
    config_name='uris'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
