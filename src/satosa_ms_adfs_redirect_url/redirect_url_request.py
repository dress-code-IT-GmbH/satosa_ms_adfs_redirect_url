import logging
from satosa.micro_services.base import RequestMicroService
from satosa_cls_redis_store import LocalStore
from .definitions import STATE_KEY
import json

logger = logging.getLogger(__name__)


class RedirectUrlRequest(RequestMicroService):
    """ Store AuthnRequest in SATOSA STATE in case it is required later for the RedirectUrl flow """
    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_store = LocalStore(config['db_encryption_key'], redishost=config.get('redis_host', 'localhost'))
        logging.info('RedirectUrlRequest microservice active')

    def process(self, context, internal_request):
        # get context already, because further process will delete request data which we need for replay later
        serializable_context = context.get_serializeable()

        # process (gives us saml2 relay state)
        result_response = super().process(context, internal_request)
        try:
            serializable_context.state = context.state.data
        except AttributeError:
            pass

        # serialize context for later
        context_json = json.dumps(serializable_context)
        key = self.local_store.set(context_json)
        try:
            logger.info(f"Stored context {key} has saml2 relay state: "
                        f" {serializable_context['state']['saml2']['relay_state']}")
        except KeyError:
            logger.error(f"Stored context {key} has no saml2 relay state")

        context.state[STATE_KEY] = str(key)
        logger.debug(f"RedirectUrlRequest: stored context {serializable_context} in {key}")
        return result_response
