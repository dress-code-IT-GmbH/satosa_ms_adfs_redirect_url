import logging
from satosa.micro_services.base import RequestMicroService
from satosa_cls_redis_store import LocalStore
from .definitions import STATE_KEY
from .serializable_context import SerializableContext

logger = logging.getLogger(__name__)


class RedirectUrlRequest(RequestMicroService):
    """ Store AuthnRequest in SATOSA STATE in case it is required later for the RedirectUrl flow """
    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_store = LocalStore(config['db_encryption_key'], redishost=config.get('redis_host', 'localhost'))
        logger.info('RedirectUrlRequest microservice active')

    def process(self, context, internal_request):
        # get context for later replay
        # process will delete some context information we'll need later
        serializable_context = SerializableContext(context)

        # process request, store new data in the context
        result_response = super().process(context, internal_request)
        serializable_context.add_state_data_from(context)

        # serialize context for later
        key = self.local_store.set(serializable_context.json_dumps())
        context.state[STATE_KEY] = str(key)

        logger.info(f"stored context in {key}")
        logger.debug(f"{key} context state {serializable_context.state()}")
        return result_response
