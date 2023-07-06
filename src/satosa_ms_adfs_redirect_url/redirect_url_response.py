import logging
import satosa
from satosa.micro_services.base import ResponseMicroService
from satosa_cls_redis_store import LocalStore
import copy
from satosa.context import Context
from .definitions import STATE_KEY, RelayStateMissingException

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
        self.local_store = LocalStore(config['db_encryption_key'], redishost=config.get('redis_host', 'localhost'))
        logging.info('RedirectUrlResponse microservice active')

    def _load_stored_authnrequest_context(self, context, need_relay_state=True):
        key = int(context.state[STATE_KEY])
        stored_context_json = self.local_store.get(key)
        stored_request_context = Context.from_json(context.wsgi_app, stored_context_json)
        logging.debug(f"Loading context from {key}: {stored_request_context}")
        if need_relay_state:
            try:
                logger.info(f"Loaded context {key} has saml2 relay state: {stored_request_context.state['saml2']['relay_state']}")
            except KeyError:
                raise RelayStateMissingException(f"Loaded context {key} has no saml2 relay state")
        return stored_request_context

    @staticmethod
    def _copy_relay_state_from(context_src, context_dst):
        logging.info(f"updating saml2 relay state "
                     f"{context_dst.state['saml2']['relay_state']} with "
                     f"{context_src.state['saml2']['relay_state']}")
        context_dst.state['saml2'] = copy.deepcopy(context_src.state['saml2'])

    def _handle_redirecturl_response(self, context):
        authn_request_context = self._load_stored_authnrequest_context(context)

        logging.debug("Starting replay with authn request context")
        wsgi_result = context.wsgi_app.run(authn_request_context)

        self._copy_relay_state_from(authn_request_context, context)

        return wsgi_result

    def process(self, context, internal_response):
        if self.redir_attr not in internal_response.attributes:
            logging.debug(f"RedirectUrl microservice: Attribute {self.redir_attr} not found: Skipping redirect.")
            return super().process(context, internal_response)

        logging.debug(f"RedirectUrl microservice: Attribute {self.redir_attr} found: Redirecting.")
        redirecturl = internal_response.attributes[self.redir_attr][0] + '?wtrealm=' + self.self_entityid

        try:
            authn_request_context = self._load_stored_authnrequest_context(context)
            self._copy_relay_state_from(authn_request_context, context)
        except RelayStateMissingException:
            logging.error(f"Redirect Attribute {self.redir_attr} found, but no relay state: Skipping redirect.")
            return super().process(context, internal_response)

        return satosa.response.Redirect(redirecturl)

    def register_endpoints(self):
        return [("^{}$".format(self.endpoint), self._handle_redirecturl_response), ]
