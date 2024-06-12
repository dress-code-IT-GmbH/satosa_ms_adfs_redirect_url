import logging
import satosa
from satosa.micro_services.base import ResponseMicroService
from satosa_cls_redis_store import LocalStore
import copy
from satosa.context import Context
from .definitions import STATE_KEY

logger = logging.getLogger(__name__)


class RedirectUrlResponse(ResponseMicroService):
    """
    Handle following events:
    * Processing a SAML Response:
        if the redirectUrl attribute is set in the response/attribute statement:
            Redirect to responder
    * Processing a RedirectUrlResponse:
        Retrieve previously saved AuthnRequest
        Replay AuthnRequest
    """
    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint = 'redirecturl_response'
        self.self_entityid = config['self_entityid']
        self.redir_attr = config['redirect_attr_name']
        self.redir_entityid = config['redir_entityid']
        self.backends = config['backends']
        self.local_store = LocalStore(config['db_encryption_key'], redishost=config.get('redis_host', 'localhost'))
        logger.info('RedirectUrlResponse microservice active')

    def _load_stored_authnrequest_context(self, context):
        key = int(context.state[STATE_KEY])
        logger.info(f"Loading authnrequest context from key: {key}")
        stored_context_json = self.local_store.get(key)
        stored_request_context = Context.from_json(context.wsgi_app, stored_context_json)
        logger.debug(f"Authnrequest content from key {key}: {stored_request_context.state}")
        return stored_request_context

    def _copy_relay_state_from(self, context_src, context_dst):
        backends_updated = []
        for backend in self.backends:
            try:
                context_dst.state[backend] = copy.deepcopy(context_src.state[backend])
                backends_updated.append(backend)
            except KeyError:
                pass
        return backends_updated

    def _handle_redirecturl_response(self, context):
        authn_request_context = self._load_stored_authnrequest_context(context)

        logger.debug("Starting replay with authn request context")
        wsgi_result = context.wsgi_app.run(authn_request_context)

        backends_updated = self._copy_relay_state_from(authn_request_context, context)
        logger.info(f"updated redirect response relay state for backends: {backends_updated}")

        return wsgi_result

    def process(self, context, internal_response):
        if self.redir_attr not in internal_response.attributes:
            logger.info(f"Testing for Attribute {self.redir_attr}: Attribute not found: Skipping redirect.")
            return super().process(context, internal_response)
        logger.info(f"Testing for Attribute {self.redir_attr}: Attribute found: Redirecting")

        redirecturl = internal_response.attributes[self.redir_attr][0] + '?wtrealm=' + self.self_entityid
        logger.info(f"redirect to {redirecturl}")
        return satosa.response.Redirect(redirecturl)

    def register_endpoints(self):
        return [("^{}$".format(self.endpoint), self._handle_redirecturl_response), ]
